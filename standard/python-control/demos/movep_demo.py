#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MoveP 笛卡尔点到点运动演示：归零 -> MoveP 举到演示位姿 -> MoveP 收回。

通过 /left_arm/movep 或 /right_arm/movep 话题（std_msgs/String, JSON）下发
笛卡尔位姿目标（**臂模型根坐标系**，由 armcontrol 的 URDF 决定，不是躯干
base_link 系），并订阅 /arm_diagnostics 等待运动结果：
  {"pose": {"position": {"x","y","z"}, "orientation": {"x","y","z","w"}},
   "speed_scale": 1.0}

坐标系注意：IK 以对应机械臂的模型根坐标系为参考，而不是整机 base_link。
左臂模型根坐标系的 +X 轴向上、+Y 轴向前、+Z 轴向左；右臂模型根坐标系
的 +X 轴向上、+Y 轴向后、+Z 轴向右。目标位置和 TCP 姿态四元数均以对应
的臂模型根坐标系为参考。

各关节角均为 0 时，左臂 TCP 坐标系的 +X 轴向前、+Y 轴向右、+Z 轴向下；
末端位置为 (-0.7265, 0.0, 0.1582)，姿态四元数 (x,y,z,w) 为
(0.5, 0.5, -0.5, -0.5)。右臂 TCP 坐标系的 +X 轴向后、+Y 轴向左、+Z
轴向下。机械臂运动时，TCP 坐标系会随末端姿态一起旋转。目标位姿超出可达
空间时，节点会返回 ik_failed。

默认演示目标取自实机验证过的预置动作关节角（arm_actions.yaml），
经 URDF 正运动学换算成末端位姿，保证可达、幅度明显：
  左臂 = wave 动作 s2 关节角 -> 末端 (0.1930, 0.3101, 0.3612)
  右臂 = beckon 动作 raise 关节角 -> 末端 (0.0198, -0.3671, 0.6365)

默认流程（保证可达）：
  1) MoveJ 归零（关节空间，零位必可达）
  2) MoveP 举到演示位姿
  3) MoveJ 归零复原（MoveP 到同一末端位姿的 IK 有多解，选解不一定是
     零位构型，所以收回用关节空间归零，保证姿势与初始完全一致）
可用 --x --y --z --qx --qy --qz --qw 覆盖第 2 步目标。
运行中 Ctrl+C 会自动发布停止指令。

用法示例：
    python3 movep_demo.py                                  # 左臂 归零+前伸+收回
    python3 movep_demo.py --arm right                      # 右臂
    python3 movep_demo.py --speed-scale 0.5                # 降低速度
"""
import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Empty
from diagnostic_msgs.msg import DiagnosticStatus

# 演示目标位姿：来自实机验证过的预置动作关节角（arm_actions.yaml）经
# URDF 正运动学换算，保证可达且动作幅度明显
DEMO_POSE = {
    # wave 动作 s2：左臂抬起挥手姿态
    "left": {
        "position": {"x": 0.1930, "y": 0.3101, "z": 0.3612},
        "orientation": {"x": 0.0362, "y": 0.4940, "z": -0.0451, "w": 0.8675},
    },
    # beckon 动作 raise：右臂抬起招手姿态
    "right": {
        "position": {"x": 0.0198, "y": -0.3671, "z": 0.6365},
        "orientation": {"x": 0.3673, "y": -0.2599, "z": 0.8652, "w": 0.2214},
    },
}


class MovePDemo(Node):

    def __init__(self, arm: str, speed_scale: float, timeout: float):
        super().__init__("movep_demo")
        side = "left" if arm == "left" else "right"
        self._side = side
        self._diag_name = f"{arm}_arm"
        self.speed_scale = speed_scale
        self.timeout = timeout

        self._movej_pub = self.create_publisher(String, f"/{side}_arm/movej", 10)
        self._pub = self.create_publisher(String, f"/{side}_arm/movep", 10)
        self._stop_pub = self.create_publisher(Empty, f"/{side}_arm/stop", 10)
        self._diag_sub = self.create_subscription(
            DiagnosticStatus, "/arm_diagnostics", self._diag_callback, 10)

        self._done = False
        self._result_message = None

    def _diag_callback(self, msg: DiagnosticStatus):
        if msg.name != self._diag_name:
            return
        for kv in msg.values:
            if kv.key == "motion_type" and kv.value == self._expect_type:
                self._result_message = msg.message
                self._done = True
                return

    def _stop(self, tag: str = "停止"):
        self._stop_pub.publish(Empty())
        self.get_logger().info(f"[{tag}] 已发布 /{self._side}_arm/stop")

    def _wait_done(self) -> bool:
        deadline = time.time() + self.timeout
        while rclpy.ok() and not self._done and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        return self._done

    def _send_and_wait(self, topic_pub, payload: dict, tag: str, motion_type: str) -> int:
        msg = String(data=json.dumps(payload))
        self.get_logger().info(f"[{tag}] 发布 {motion_type}: {msg.data}")
        self._expect_type = motion_type
        self._done = False
        self._result_message = None
        topic_pub.publish(msg)

        if not self._wait_done():
            self.get_logger().error(f"[{tag}] 等待诊断超时（{self.timeout}s）")
            self._stop()
            return 1
        if self._result_message == "motion completed":
            self.get_logger().info(f"[{tag}] 完成")
            return 0
        self.get_logger().error(f"[{tag}] 失败: {self._result_message}")
        self._stop()
        return 1

    def run(self, pose_arg) -> int:
        time.sleep(1.0)  # DDS 发现

        # 1) MoveJ 归零，保证笛卡尔起点确定
        if self._send_and_wait(self._movej_pub,
                               {"joints": [0.0] * 7, "speed_scale": self.speed_scale},
                               "MoveJ 归零", "movej") != 0:
            return 1

        # 2) MoveP 举到演示位姿（来自实机验证动作的末端位姿）
        target = pose_arg if pose_arg is not None else DEMO_POSE[self._side]
        if self._send_and_wait(self._pub, {"pose": target, "speed_scale": self.speed_scale},
                               "MoveP 举起", "movep") != 0:
            return 1

        # 3) MoveJ 归零复原（保证关节姿态与初始完全一致；MoveP 到同一末端
        #    位姿的 IK 存在多解，选解不一定是零位构型，会导致收臂姿势不同）
        if self._send_and_wait(self._movej_pub,
                               {"joints": [0.0] * 7, "speed_scale": self.speed_scale},
                               "MoveJ 复原", "movej") != 0:
            return 1

        self.get_logger().info("MoveP 演示完成")
        return 0


def main():
    parser = argparse.ArgumentParser(description="MoveP 笛卡尔点到点运动演示")
    parser.add_argument("--arm", choices=["left", "right"], default="left",
                        help="选择手臂（默认 left）")
    parser.add_argument("--x", type=float, default=None,
                        help="自定义目标位置 x（米，臂模型根系）")
    parser.add_argument("--y", type=float, default=None,
                        help="自定义目标位置 y（米）")
    parser.add_argument("--z", type=float, default=None,
                        help="自定义目标位置 z（米）")
    parser.add_argument("--qx", type=float, default=None,
                        help="自定义目标姿态四元数 x")
    parser.add_argument("--qy", type=float, default=None,
                        help="自定义目标姿态四元数 y")
    parser.add_argument("--qz", type=float, default=None,
                        help="自定义目标姿态四元数 z")
    parser.add_argument("--qw", type=float, default=None,
                        help="自定义目标姿态四元数 w")
    parser.add_argument("--speed-scale", type=float, default=1.0,
                        help="速度倍率，范围 [0.01, 5.0]")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="每步等待诊断的超时时间（秒）")
    args = parser.parse_args()

    pose_arg = None
    has_xyz = any(v is not None for v in (args.x, args.y, args.z))
    has_quat = any(v is not None for v in (args.qx, args.qy, args.qz, args.qw))
    if has_xyz or has_quat:
        demo = DEMO_POSE["left" if args.arm == "left" else "right"]
        pose_arg = {
            "position": {
                "x": args.x if args.x is not None else demo["position"]["x"],
                "y": args.y if args.y is not None else demo["position"]["y"],
                "z": args.z if args.z is not None else demo["position"]["z"],
            },
            "orientation": {
                "x": args.qx if args.qx is not None else demo["orientation"]["x"],
                "y": args.qy if args.qy is not None else demo["orientation"]["y"],
                "z": args.qz if args.qz is not None else demo["orientation"]["z"],
                "w": args.qw if args.qw is not None else demo["orientation"]["w"],
            },
        }

    rclpy.init()
    node = MovePDemo(args.arm, args.speed_scale, args.timeout)
    code = 1
    try:
        code = node.run(pose_arg)
    except KeyboardInterrupt:
        node.get_logger().warn("检测到 Ctrl+C，停止手臂运动")
        node._stop()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()

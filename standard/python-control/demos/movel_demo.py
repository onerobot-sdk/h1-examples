#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MoveL 笛卡尔直线运动演示：归零 -> 收到胸口 -> MoveL 长直线举到高位 -> 复原。

通过 /left_arm/movel 或 /right_arm/movel 话题（std_msgs/String, JSON）下发
笛卡尔位姿目标（**臂模型根坐标系**，由 armcontrol 的 URDF 决定），并订阅
/arm_diagnostics 等待运动结果：
  {"pose": {"position": {"x","y","z"}, "orientation": {"x","y","z","w"}},
   "speed_scale": 1.0}

坐标系注意：目标位置和 TCP 姿态四元数均以对应机械臂的模型根坐标系为
参考，而不是整机 base_link。左臂模型根坐标系的 +X 轴向上、+Y 轴向前、
+Z 轴向左；右臂模型根坐标系的 +X 轴向上、+Y 轴向后、+Z 轴向右。

各关节角均为 0 时，左臂 TCP 坐标系的 +X 轴向前、+Y 轴向右、+Z 轴向下；
右臂 TCP 坐标系的 +X 轴向后、+Y 轴向左、+Z 轴向下。机械臂运动时，TCP
坐标系会随末端姿态一起旋转。

为什么需要 IK：/movel 话题下发的是末端位姿（位置+姿态），arm_control_node
内部必须做逆运动学把它换算成 7 个关节角才能驱动电机；且 MoveL 要求整条
直线路径逐点 IK（比 MoveP 只解两端苛刻）。臂完全伸直（零位）处于奇异
位形，从零位直接做长直线中途 IK 会失败（实测 ik_failed），所以先用
MoveJ 把手收到胸前，再从那里走长直线。

默认流程（举起 -> 放下，终点复位；左右镜像对称）：
  1) MoveJ 归零（关节空间，零位必可达）
  2) MoveJ 收到胸口收拢姿态（肘部大弯，手在身前靠中线、远离奇异位形）
       左臂 [-0.2, 0.5, -0.5, -1.7, 0, 1.0, 0] -> 末端 (0.169, 0.266, 0.280)
  3) MoveL 长直线（约 0.46m）举到高位
       左臂目标位姿 (0.0398, 0.2296, 0.7147)，与右臂实机验证过的
       beckon.in 构型 (0.0398, -0.2290, 0.7150) 镜像对称
  4) MoveJ 归零复原（IK 有多解，关节空间归零保证姿势与初始完全一致）
可用 --x --y --z --qx --qy --qz --qw 覆盖第 3 步目标。
运行中 Ctrl+C 会自动发布停止指令。

用法示例：
    python3 movel_demo.py                                  # 左臂 收胸 -> 长直线举起 -> 放下
    python3 movel_demo.py --arm right                      # 右臂
    python3 movel_demo.py --speed-scale 0.5                # 降低速度
"""
import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Empty
from diagnostic_msgs.msg import DiagnosticStatus

# 每臂的 MoveL 演示段：胸口收拢起始关节角 + 长直线目标末端位姿。
# 左右镜像对称；高位终点与实机验证过的 beckon.in 构型（右臂）镜像一致，
# 直线长约 0.46m，中途到臂根的最大距离不超过臂全长，逐点 IK 可行。
DEMO_SEG = {
    "left": {
        "start_joints": [-0.2, 0.5, -0.5, -1.7, 0.0, 1.0, 0.0],   # 胸口收拢
        "target_pose": {
            "position": {"x": 0.0398, "y": 0.2296, "z": 0.7147},
            "orientation": {"x": -0.2335, "y": 0.2527, "z": -0.2178, "w": 0.9133},
        },  # 高位（beckon.in 的左臂镜像）
    },
    "right": {
        "start_joints": [0.2, -0.5, 0.5, 1.7, 0.0, -1.0, 0.0],    # 胸口收拢（镜像）
        "target_pose": {
            "position": {"x": 0.0398, "y": -0.2290, "z": 0.7150},
            "orientation": {"x": 0.2527, "y": -0.2334, "z": 0.9133, "w": -0.2178},
        },  # 高位（beckon.in，实机验证）
    },
}
HOME_JOINTS = [0.0] * 7


class MoveLDemo(Node):

    def __init__(self, arm: str, speed_scale: float, timeout: float):
        super().__init__("movel_demo")
        side = "left" if arm == "left" else "right"
        self._side = side
        self._diag_name = f"{arm}_arm"
        self.speed_scale = speed_scale
        self.timeout = timeout

        self._movej_pub = self.create_publisher(String, f"/{side}_arm/movej", 10)
        self._pub = self.create_publisher(String, f"/{side}_arm/movel", 10)
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
        seg = DEMO_SEG[self._side]
        time.sleep(1.0)  # DDS 发现

        # 1) MoveJ 归零
        if self._send_and_wait(self._movej_pub,
                               {"joints": HOME_JOINTS, "speed_scale": self.speed_scale},
                               "MoveJ 归零", "movej") != 0:
            return 1

        # 2) MoveJ 收到胸口收拢姿态（远离奇异位形）
        if self._send_and_wait(self._movej_pub,
                               {"joints": seg["start_joints"],
                                "speed_scale": self.speed_scale},
                               "MoveJ 收到胸口", "movej") != 0:
            return 1

        # 3) MoveL 长直线（约 0.46m）举到高位
        target = pose_arg if pose_arg is not None else seg["target_pose"]
        if self._send_and_wait(self._pub, {"pose": target, "speed_scale": self.speed_scale},
                               "MoveL 长直线举起", "movel") != 0:
            return 1

        # 4) MoveJ 归零复原（保证关节姿态与初始完全一致）
        if self._send_and_wait(self._movej_pub,
                               {"joints": HOME_JOINTS, "speed_scale": self.speed_scale},
                               "MoveJ 放下", "movej") != 0:
            return 1

        self.get_logger().info("MoveL 演示完成")
        return 0


def main():
    parser = argparse.ArgumentParser(description="MoveL 笛卡尔直线运动演示")
    parser.add_argument("--arm", choices=["left", "right"], default="left",
                        help="选择手臂（默认 left）")
    parser.add_argument("--speed-scale", type=float, default=1.0,
                        help="速度倍率，范围 [0.01, 5.0]")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="每步等待诊断的超时时间（秒）")
    parser.add_argument("--x", type=float, default=None, help="目标位置 x（米）")
    parser.add_argument("--y", type=float, default=None, help="目标位置 y（米）")
    parser.add_argument("--z", type=float, default=None, help="目标位置 z（米）")
    parser.add_argument("--qx", type=float, default=None, help="目标姿态四元数 x")
    parser.add_argument("--qy", type=float, default=None, help="目标姿态四元数 y")
    parser.add_argument("--qz", type=float, default=None, help="目标姿态四元数 z")
    parser.add_argument("--qw", type=float, default=None, help="目标姿态四元数 w")
    args = parser.parse_args()

    pose_arg = None
    if any(v is not None for v in (args.x, args.y, args.z,
                                   args.qx, args.qy, args.qz, args.qw)):
        demo = DEMO_SEG["left" if args.arm == "left" else "right"]["target_pose"]
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
    node = MoveLDemo(args.arm, args.speed_scale, args.timeout)
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

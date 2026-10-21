#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MoveJ 关节空间运动演示：MoveJ 到演示姿态，再 MoveJ 回零位。

通过 /left_arm/movej 或 /right_arm/movej 话题（std_msgs/String, JSON）下发
关节空间目标，并订阅 /arm_diagnostics 等待运动结果：
  {"joints": [7个弧度], "speed_scale": 1.0}
MoveJ 是关节空间绝对位置控制，不保证末端走直线，速度快。

默认流程（左右臂对称演示，均「抬起 -> 回零位」）：
  左臂: [0, 0.8, 0, -1.2, 0, 0, 0] -> 回零位 [0,0,0,0,0,0,0]
  右臂: [0, -0.8, 0, 1.2, 0, 0, 0] -> 回零位 [0,0,0,0,0,0,0]
注意：左右臂镜像，抬起方向相反——左臂 joint2=+0.8 往上抬（末端
      z 约 0.45m），右臂 joint2=-0.8 往上抬（两臂外侧对称，y=∓0.46）。
可用 --joints 指定 7 个目标角。运行中 Ctrl+C 会自动发布停止指令。

用法示例：
    python3 movej_demo.py                                    # 左臂抬起 -> 回零位
    python3 movej_demo.py --arm right                        # 右臂抬起 -> 回零位
    python3 movej_demo.py --joints -0.5 0.2 0.4 -0.6 0 0.2 0 # 自定义 7 关节目标
"""
import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Empty
from diagnostic_msgs.msg import DiagnosticStatus

# 左右臂对称演示姿态（抬起 -> 回零位）：
#   joint2 为肩部俯仰，控制「往上抬」——左臂 +0.8 上抬、右臂 -0.8 上抬（镜像）
#   joint4 为肘部弯曲，让前臂上折，举起效果更明显
#   姿态经 URDF 正运动学验证：左右臂末端 (−0.288, ±0.459, 0.455)，外侧对称
#   关节均在限位内（joint2/joint4 限位约 ±1.946，此前的 joint4=-2.1 超限）
DEMO_JOINTS = {
    "left": [0.0, 0.8, 0.0, -1.2, 0.0, 0.0, 0.0],
    "right": [0.0, -0.8, 0.0, 1.2, 0.0, 0.0, 0.0],
}
HOME_JOINTS = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


class MoveJDemo(Node):

    def __init__(self, arm: str, speed_scale: float, timeout: float):
        super().__init__("movej_demo")
        side = "left" if arm == "left" else "right"
        self._side = side
        self._diag_name = f"{arm}_arm"
        self.speed_scale = speed_scale
        self.timeout = timeout

        self._pub = self.create_publisher(String, f"/{side}_arm/movej", 10)
        self._stop_pub = self.create_publisher(Empty, f"/{side}_arm/stop", 10)
        self._diag_sub = self.create_subscription(
            DiagnosticStatus, "/arm_diagnostics", self._diag_callback, 10)

        self._done = False
        self._result_message = None

    def _diag_callback(self, msg: DiagnosticStatus):
        if msg.name != self._diag_name:
            return
        for kv in msg.values:
            if kv.key == "motion_type" and kv.value == "movej":
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

    def _movej(self, joints: list, tag: str) -> int:
        payload = {"joints": [float(v) for v in joints],
                   "speed_scale": self.speed_scale}
        msg = String(data=json.dumps(payload))
        self.get_logger().info(f"[{tag}] 发布 movej: {msg.data}")
        self._done = False
        self._result_message = None
        self._pub.publish(msg)

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

    def run(self, joints_arg) -> int:
        time.sleep(1.0)  # DDS 发现

        target = list(joints_arg) if joints_arg else DEMO_JOINTS[
            "left" if self._diag_name == "left_arm" else "right"]
        if self._movej(target, "MoveJ 目标") != 0:
            return 1

        # 回零位复位（目标本身是零位时该步幂等）
        if target != HOME_JOINTS:
            if self._movej(HOME_JOINTS, "回零位") != 0:
                return 1

        self.get_logger().info("MoveJ 演示完成")
        return 0


def main():
    parser = argparse.ArgumentParser(description="MoveJ 关节空间运动演示")
    parser.add_argument("--arm", choices=["left", "right"], default="left",
                        help="选择手臂（默认 left）")
    parser.add_argument("--joints", type=float, nargs=7, default=None, metavar="J",
                        help="自定义 7 个关节目标角（弧度），不给则用演示姿态")
    parser.add_argument("--speed-scale", type=float, default=1.0,
                        help="速度倍率，范围 [0.01, 5.0]")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="每步等待诊断的超时时间（秒）")
    args = parser.parse_args()

    rclpy.init()
    node = MoveJDemo(args.arm, args.speed_scale, args.timeout)
    code = 1
    try:
        code = node.run(args.joints)
    except KeyboardInterrupt:
        node.get_logger().warn("检测到 Ctrl+C，停止手臂运动")
        node._stop()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()

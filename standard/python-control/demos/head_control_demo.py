#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""头部控制：默认播放「摇头来回 N 次 -> 点头来回 N 次」演示，
也可用 --shake / --nod 单独触发动作，或用 --pitch / --yaw 直接下发
原生角度控制（话题原始用法）。

原生接口：/head/joint_states/update 话题（sensor_msgs/JointState，关节名
head_pitch_joint / head_yaw_joint，position 单位弧度），demo 帮你把度数
换算成弧度并发布，节点收到后按位置控制运动到位：
  - --pitch 20 --yaw -15   直接设置俯仰 20°、偏航 -15°（可单独给）

动作演示（demo 编排好的动作）：
  - 摇头：head_yaw_joint 左右摆动（--shake N 或默认演示）
  - 点头：head_pitch_joint 上下摆动（--nod N 或默认演示）

用法示例：
    python3 head_control_demo.py                              # 默认演示
    python3 head_control_demo.py --shake 2                    # 摇头来回 2 次
    python3 head_control_demo.py --nod 1                      # 点头来回 1 次
    python3 head_control_demo.py --pitch 20 --yaw -15         # 原生角度控制
    python3 head_control_demo.py --times 3 --yaw-amp 30 --pitch-amp 20 --wait 1.5
"""
import argparse
import math
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class HeadControlDemo(Node):

    def __init__(self):
        super().__init__("head_control_demo")
        self._joint_pub = self.create_publisher(
            JointState, "/head/joint_states/update", 10)

    def _send_position(self, pitch_deg: float, yaw_deg: float,
                       wait: float, tag: str):
        msg = JointState()
        msg.name = ["head_pitch_joint", "head_yaw_joint"]
        msg.position = [math.radians(pitch_deg), math.radians(yaw_deg)]
        self.get_logger().info(f"[{tag}] pitch={pitch_deg:.1f}°, yaw={yaw_deg:.1f}°")
        self._joint_pub.publish(msg)
        time.sleep(wait)

    def shake_head(self, times: int, amp_deg: float, wait: float):
        """摇头：yaw 左右摆动 times 个来回。"""
        for i in range(times):
            self._send_position(0.0, amp_deg, wait, f"摇头 {i + 1}-右")
            self._send_position(0.0, -amp_deg, wait, f"摇头 {i + 1}-左")
        self._send_position(0.0, 0.0, wait, "摇头回正")

    def nod_head(self, times: int, amp_deg: float, wait: float):
        """点头：pitch 上下摆动 times 个来回。"""
        for i in range(times):
            self._send_position(amp_deg, 0.0, wait, f"点头 {i + 1}-下")
            self._send_position(-amp_deg, 0.0, wait, f"点头 {i + 1}-上")
        self._send_position(0.0, 0.0, wait, "点头回正")

    def run(self, times: int, yaw_amp: float, pitch_amp: float, wait: float,
            shake: int = None, nod: int = None,
            pitch_deg: float = None, yaw_deg: float = None) -> int:
        time.sleep(1.0)  # DDS 发现

        # 原生角度控制：--pitch/--yaw 直接下发目标角度（话题原始用法）
        if pitch_deg is not None or yaw_deg is not None:
            pitch = pitch_deg if pitch_deg is not None else 0.0
            yaw = yaw_deg if yaw_deg is not None else 0.0
            self._send_position(pitch, yaw, wait, "原生角度控制")
            self.get_logger().info("角度下发完成")
            return 0

        # 手动模式：--shake / --nod 指定动作与次数（先摇头后点头）
        if shake is not None or nod is not None:
            if shake:
                self.shake_head(shake, yaw_amp, wait)
            if nod:
                self.nod_head(nod, pitch_amp, wait)
            self.get_logger().info("手动头部动作完成")
            return 0

        # 默认演示：摇头来回 N 次 -> 点头来回 N 次
        self.shake_head(times, yaw_amp, wait)
        self.nod_head(times, pitch_amp, wait)

        self.get_logger().info("摇头/点头动作完成")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="头部控制：不带参数播放默认演示；--shake/--nod 触发动作；"
                    "--pitch/--yaw 原生角度控制")
    parser.add_argument("--pitch", type=float, default=None, metavar="DEG",
                        help="直接下发俯仰角（度，正=低头），如 --pitch 20")
    parser.add_argument("--yaw", type=float, default=None, metavar="DEG",
                        help="直接下发偏航角（度，正=左转），如 --yaw -15")
    parser.add_argument("--shake", type=int, default=None, metavar="N",
                        help="摇头来回 N 次，如 --shake 2")
    parser.add_argument("--nod", type=int, default=None, metavar="N",
                        help="点头来回 N 次，如 --nod 1")
    parser.add_argument("--times", type=int, default=3,
                        help="默认演示的摇头/点头来回次数")
    parser.add_argument("--yaw-amp", type=float, default=30.0,
                        help="摇头幅度（度）")
    parser.add_argument("--pitch-amp", type=float, default=20.0,
                        help="点头幅度（度）")
    parser.add_argument("--wait", type=float, default=1.5,
                        help="每步到位等待时间（秒），头部电机较慢，建议不小于 1.5s")
    args = parser.parse_args()

    rclpy.init()
    node = HeadControlDemo()
    try:
        code = node.run(args.times, args.yaw_amp, args.pitch_amp, args.wait,
                        args.shake, args.nod, args.pitch, args.yaw)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
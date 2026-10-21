#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升降控制：默认播放「抬臂 -> 下降 -> 上升复位 -> 恢复手臂」联动演示，
也可用 --up / --down 单独控制升降柱。

流程（默认演示）：
1. 通过 /action/execute 触发 ready（手臂抬起并保持），等待完成；
2. 通过 /lift/joint_states/update_relative 下降 delta 米；
3. 再上升 delta 米复位；
4. 通过 /action/execute 触发 home（手臂回零位）。

手动控制（仅控制升降柱，不联动手臂，注意避让）：
    python3 lift_control_demo.py --down 0.1      # 下降 0.1 m
    python3 lift_control_demo.py --up 0.1        # 上升 0.1 m
    python3 lift_control_demo.py --down 0.2 --up 0.2   # 下降后上升复位

用法示例（默认演示）：
    python3 lift_control_demo.py --delta 0.5 --wait 10.0
"""
import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String


class LiftControlDemo(Node):

    def __init__(self):
        super().__init__("lift_control_demo")
        self._rel_pub = self.create_publisher(
            JointState, "/lift/joint_states/update_relative", 1)
        self._action_pub = self.create_publisher(String, "/action/execute", 10)
        self._action_sub = self.create_subscription(
            String, "/action/status", self._status_callback, 10)

        self._current_action = None
        self._done = False

    def _status_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
        except (json.JSONDecodeError, ValueError):
            return
        if data.get("action_id") != self._current_action:
            return
        state = data.get("state", "")
        progress = data.get("progress", 0.0)
        self.get_logger().info(
            f"手臂动作 {self._current_action}: state={state}, progress={progress:.2f}")
        if state in ("completed", "failed"):
            self._done = True

    def _trigger_action(self, action_id: str, timeout: float):
        self._current_action = action_id
        self._done = False
        payload = {"action_id": action_id}
        self.get_logger().info(f"触发手臂动作 {action_id}")
        self._action_pub.publish(String(data=json.dumps(payload)))

        deadline = time.time() + timeout
        while rclpy.ok() and not self._done and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

    def _move_relative(self, delta_m: float, wait: float, tag: str):
        msg = JointState()
        msg.name = ["lift_joint"]
        msg.position = [float(delta_m)]
        self.get_logger().info(f"[{tag}] 升降相对位移 {delta_m:+.3f} m")
        self._rel_pub.publish(msg)
        time.sleep(wait)

    def run(self, delta: float, wait: float, action_timeout: float,
            up: float = None, down: float = None) -> int:
        time.sleep(1.0)  # DDS 发现

        # 手动模式：仅控制升降柱（--down 先降，--up 后升）
        if up is not None or down is not None:
            if down is not None:
                self._move_relative(-abs(down), wait, "手动下降")
            if up is not None:
                self._move_relative(abs(up), wait, "手动上升")
            self.get_logger().info("手动升降完成")
            return 0

        # 默认演示：抬臂 -> 下降 -> 上升复位 -> 恢复手臂
        self._trigger_action("ready", action_timeout)  # 1. 抬臂保持
        self._move_relative(-delta, wait, "下降")       # 2. 下降
        self._move_relative(delta, wait, "上升复位")     # 3. 上升复位
        self._trigger_action("home", action_timeout)   # 4. 恢复手臂

        self.get_logger().info("抬臂/下降/上升复位/恢复手臂 完成")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="升降控制：不带参数播放默认演示，--up/--down 手动控制升降柱")
    parser.add_argument("--up", type=float, default=None, metavar="M",
                        help="上升指定距离（米），如 --up 0.1")
    parser.add_argument("--down", type=float, default=None, metavar="M",
                        help="下降指定距离（米），如 --down 0.1")
    parser.add_argument("--delta", type=float, default=0.5,
                        help="默认演示的下降/上升位移（米）")
    parser.add_argument("--wait", type=float, default=10.0,
                        help="升降每步到位等待时间（秒），按实际升降速度调整")
    parser.add_argument("--action-timeout", type=float, default=20.0,
                        help="手臂动作等待超时（秒）")
    args = parser.parse_args()

    rclpy.init()
    node = LiftControlDemo()
    try:
        code = node.run(args.delta, args.wait, args.action_timeout,
                        args.up, args.down)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
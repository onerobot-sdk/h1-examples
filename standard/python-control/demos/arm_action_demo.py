#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""依次触发机械臂预置动作（默认：先左手挥手，再右手招手）。

通过 /action/execute 话题（std_msgs/String, JSON）逐个触发 arm_control_node 中
已注册的动作，并监听 /action/status 等待每个动作结束后再执行下一个。
预置动作由 arm_control_node 直接按 yaml 定义 + speed_scale 执行，速度快。

默认顺序 = [wave 左臂挥手, beckon 右手招手]，符合「先左手后右手」的打招呼动作。

用法示例：
    python3 arm_action_demo.py                      # 左臂挥手 -> 右手招手
    python3 arm_action_demo.py wave                 # 只左臂挥手
    python3 arm_action_demo.py salute open_arms     # 敬礼 -> 张开双臂
    python3 arm_action_demo.py --speed-scale 0.8      # 速度 0.8 倍
"""
import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# 与 armcontrol/config/arm_actions.yaml 中 registered_arm_actions 保持一致
AVAILABLE_ACTIONS = [
    "wave", "home", "salute", "open_arms", "guide",
    "point", "handshake", "handover", "beckon", "ready",
]

DEFAULT_ACTIONS = ["wave", "beckon"]


class ArmActionDemo(Node):

    def __init__(self, actions: list, speed_scale: float, timeout: float):
        super().__init__("arm_action_demo")
        self.actions = actions
        self.speed_scale = speed_scale
        self.timeout = timeout

        self._pub = self.create_publisher(String, "/action/execute", 10)
        self._sub = self.create_subscription(
            String, "/action/status", self._status_callback, 10)

        self._current_action = None
        self._done = False
        self._result_state = None

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
            f"动作 {self._current_action}: state={state}, progress={progress:.2f}")
        if state in ("completed", "failed"):
            self._result_state = state
            self._done = True

    def _execute(self, action_id: str) -> int:
        """触发单个动作并等待结束，返回 0 成功 / 非 0 失败。"""
        self._current_action = action_id
        self._done = False
        self._result_state = None

        payload = {"action_id": action_id, "speed_scale": self.speed_scale}
        msg = String(data=json.dumps(payload))
        self.get_logger().info(f"发布 /action/execute: {msg.data}")
        self._pub.publish(msg)

        deadline = time.time() + self.timeout
        while rclpy.ok() and not self._done and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

        if not self._done:
            self.get_logger().warn(f"动作 {action_id} 等待超时（{self.timeout}s）")
            return 1
        if self._result_state != "completed":
            self.get_logger().error(f"动作 {action_id} 执行失败: {self._result_state}")
            return 1
        self.get_logger().info(f"动作 {action_id} 完成")
        return 0

    def run(self) -> int:
        time.sleep(1.0)  # DDS 发现

        for action_id in self.actions:
            if self._execute(action_id) != 0:
                return 1

        self.get_logger().info("全部动作执行完成")
        return 0


def main():
    parser = argparse.ArgumentParser(description="依次触发机械臂预置动作")
    parser.add_argument("actions", nargs="*", choices=AVAILABLE_ACTIONS,
                        default=None,
                        help="要依次执行的动作列表（默认：wave 左臂挥手 -> beckon 右手招手）")
    parser.add_argument("--speed-scale", type=float, default=1.0,
                        help="速度倍率，范围 [0.01, 5.0]")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="每个动作的等待超时时间（秒）")
    args = parser.parse_args()

    actions = args.actions if args.actions else DEFAULT_ACTIONS

    rclpy.init()
    node = ArmActionDemo(list(actions), args.speed_scale, args.timeout)
    try:
        code = node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
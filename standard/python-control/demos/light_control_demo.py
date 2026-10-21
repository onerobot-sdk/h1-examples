#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""灯光控制（灯板）。

通过 /light_board/control 话题（std_msgs/String, JSON）控制 4 块灯板。

JSON 格式（boards 固定 4 个元素，可为 null 跳过对应板）：
  {"boards": [{"color": "#RRGGBB", "brightness": 0-100, "blink_hz": 0-100}, ...]}
  - color      十六进制颜色，如 "#FF0000"（红色）、"#000000"（关闭）
  - brightness 整体亮度 0-100
  - blink_hz   闪烁频率 0-100，0 表示常亮

等价的 ros2 命令参考（本 demo 即此格式的封装）：
  ros2 topic pub --once /light_board/control std_msgs/msg/String \
    '{data: "{\"boards\": [{\"color\":\"#FF0000\",\"brightness\":100,\"blink_hz\":0},null,null,null]}"}'

用法示例：
    python3 light_control_demo.py                                       # 自动播放灯光演示
    python3 light_control_demo.py --on                                  # 四板白色 100% 常亮（恢复默认状态）
    python3 light_control_demo.py --color "#FF0000" --brightness 100    # 四板红色常亮
    python3 light_control_demo.py --board 1 --color "#00FF00"           # 仅灯板 1 绿色
    python3 light_control_demo.py --color "#0000FF" --blink-hz 10       # 四板蓝色 10Hz 闪烁
    python3 light_control_demo.py --off                                 # 关闭所有灯
    python3 light_control_demo.py --demo                                # 灯光演示（同不带参数）
"""
import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

TOPIC = "/light_board/control"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _board(color: str, brightness: float, blink_hz: float) -> dict:
    return {"color": color,
            "brightness": int(_clamp(brightness, 0, 100)),
            "blink_hz": int(_clamp(blink_hz, 0, 100))}


class LightControlDemo(Node):

    def __init__(self):
        super().__init__("light_control_demo")
        self._pub = self.create_publisher(String, TOPIC, 10)

    def _publish(self, boards: list):
        data = json.dumps({"boards": boards})
        self.get_logger().info(f"发布 {TOPIC}: {data}")
        self._pub.publish(String(data=data))

    def set_all(self, color: str, brightness: float, blink_hz: float):
        board = _board(color, brightness, blink_hz)
        self._publish([board, board, board, board])

    def set_board(self, board_no: int, color: str, brightness: float, blink_hz: float):
        """点亮单块灯板（board_no 1-4），其余板发 null 跳过。"""
        boards = [None] * 4
        boards[board_no - 1] = _board(color, brightness, blink_hz)
        self._publish(boards)

    def off(self):
        board = _board("#000000", 0, 0)
        self._publish([board, board, board, board])

    def _run_demo(self):
        """灯光演示：颜色循环 -> 逐板白色点亮 -> 黄色闪烁 -> 关闭。"""
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"]
        for color in colors:
            self.set_all(color, 60, 0)
            time.sleep(1.0)
        for board_no in range(1, 5):  # 逐板白色点亮
            self.set_board(board_no, "#FFFFFF", 100, 0)
            time.sleep(0.8)
        self.set_all("#FFFF00", 50, 5)  # 黄色 5Hz 闪烁
        time.sleep(2.0)
        self.off()

    def run(self, args) -> int:
        time.sleep(1.0)  # DDS 发现

        if args.off:
            self.off()
            self.get_logger().info("所有灯已关闭")
            return 0

        if args.on:
            # 白色 100% 常亮，恢复测试前的常用状态
            self.set_all("#FFFFFF", 100, 0)
            self.get_logger().info("已恢复白色常亮")
            return 0

        if args.demo:
            self.get_logger().info("开始灯光演示")
            self._run_demo()
            self.get_logger().info("灯光演示结束")
            return 0

        if args.board is not None:
            self.set_board(args.board, args.color, args.brightness, args.blink_hz)
            self.get_logger().info(f"灯板 {args.board} 设置完成")
            return 0

        if args.color is not None:
            self.set_all(args.color, args.brightness, args.blink_hz)
            self.get_logger().info("灯光设置完成")
            return 0

        # 默认：不带参数自动播放灯光演示
        self.get_logger().info("未指定参数，自动播放灯光演示")
        self._run_demo()
        self.get_logger().info("灯光演示结束")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="灯光控制（灯板）。不带参数时自动播放灯光演示")
    parser.add_argument("--board", type=int, choices=[1, 2, 3, 4], default=None,
                        help="仅控制指定灯板（1-4），其余板跳过；不给则控制全部 4 块")
    parser.add_argument("--color", default=None,
                        help="颜色，格式 #RRGGBB")
    parser.add_argument("--brightness", type=float, default=50.0,
                        help="亮度 0-100（默认 50）")
    parser.add_argument("--blink-hz", type=float, default=0.0,
                        help="闪烁频率 0-100，0 为常亮（默认 0）")
    parser.add_argument("--on", action="store_true",
                        help="四板白色 100%% 常亮（恢复默认状态）")
    parser.add_argument("--off", action="store_true",
                        help="关闭所有灯")
    parser.add_argument("--demo", action="store_true",
                        help="运行灯光演示（颜色循环+逐板点亮+闪烁）")
    args = parser.parse_args()

    rclpy.init()
    node = LightControlDemo()
    try:
        code = node.run(args)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""底盘控制：默认播放「前进 -> 后退 -> 左转 -> 右转复原」演示，
也可用参数单独控制前进/后退/左转/右转。

通过 /cmd_vel 话题（geometry_msgs/Twist）以开环速度控制实现：
  - linear.x  前进/后退速度（m/s）
  - angular.z 转向角速度（rad/s），正值左转、负值右转

每个动作在时长内以 10Hz 持续发布（等价 `ros2 topic pub` 不带 --once），
结束时发布零速停止；前进/后退带 1 秒起步斜坡，避免起步过冲。

转向用「时间」控制而不是角度：底盘起步加速/停止滞后会吃掉有效转动
时间，按 `角度/角速度` 折算的时长实际转不到（实测 90° 只转约 45°）。
直接指定「以 angular.z 角速度转 T 秒」，转多少度交给实际执行；
默认演示左转/右转时长相同，误差相互抵消，仍能大致复位。

手动控制示例：
    python3 base_move_demo.py --forward 0.3              # 前进 0.3 m
    python3 base_move_demo.py --back 0.2                 # 后退 0.2 m
    python3 base_move_demo.py --left 2.0                 # 以 angular 速度左转 2 秒
    python3 base_move_demo.py --right 3.0 --angular 0.5  # 右转 3 秒（角速度 0.5）
    python3 base_move_demo.py --forward 0.3 --right 2.0  # 组合：先前进再右转

默认演示（不带参数）：
    前进 0.5m -> 后退 0.5m -> 左转 3s -> 等 2s -> 右转 3s 复原（时长对称）

如需更精确的距离/角度，可改为订阅 /odom 做闭环控制。
"""
import argparse
import sys
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class BaseMoveDemo(Node):

    def __init__(self):
        super().__init__("base_move_demo")
        self._pub = self.create_publisher(Twist, "/cmd_vel", 10)

    def _send(self, linear_x: float = 0.0, angular_z: float = 0.0):
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z
        self._pub.publish(msg)

    def _send_timed(self, linear_x: float, angular_z: float, duration: float,
                    ramp_up: bool = False):
        if ramp_up and linear_x != 0.0:
            # 1 秒内从 0.3 倍速度线性加速到全速，平滑起步
            ramp_t = min(1.0, duration)
            n = 10
            for i in range(1, n + 1):
                v = linear_x * (0.3 + 0.7 * i / n)
                self._send(v, 0.0)
                time.sleep(ramp_t / n)
            duration -= ramp_t
        if duration > 0:
            self._send(linear_x, angular_z)
            time.sleep(duration)
        self._send(0.0, 0.0)  # 每步结束立即停止

    def _move(self, distance_m: float, linear_speed: float):
        """前进/后退（distance 正=前进，负=后退），带起步斜坡。"""
        direction = 1.0 if distance_m >= 0 else -1.0
        self._send_timed(direction * linear_speed, 0.0,
                         abs(distance_m) / linear_speed, ramp_up=True)

    def _turn(self, duration_s: float, angular_speed: float):
        """左转/右转（duration 正=左转，负=右转），持续指定秒数。"""
        direction = 1.0 if duration_s >= 0 else -1.0
        self._send_timed(0.0, direction * angular_speed, abs(duration_s))

    def _stop(self):
        """复位：确保底盘速度归零、静止。"""
        self._send(0.0, 0.0)
        time.sleep(0.5)
        self._send(0.0, 0.0)

    def run_demo(self, distance: float, linear_speed: float,
                 angular_speed: float, turn_time_s: float,
                 step_wait: float = 2.0) -> int:
        """默认演示：前进 -> 后退 -> 左转 -> 右转复原（转向时长对称抵消）。"""
        time.sleep(1.0)  # DDS 发现

        self.get_logger().info(f"前进 {distance:.2f} m")
        self._move(distance, linear_speed)
        time.sleep(step_wait)  # 步间等待，给底盘响应时间

        self.get_logger().info(f"后退 {distance:.2f} m（抵消）")
        self._move(-distance, linear_speed)
        time.sleep(step_wait)

        self.get_logger().info(f"左转 {turn_time_s:.1f} s（angular={angular_speed} rad/s）")
        self._turn(turn_time_s, angular_speed)
        time.sleep(step_wait)

        self.get_logger().info(f"右转 {turn_time_s:.1f} s（复原）")
        self._turn(-turn_time_s, angular_speed)

        self._stop()
        self.get_logger().info("动作完成，底盘已停止复位")
        return 0

    def run_manual(self, steps, linear_speed: float,
                   angular_speed: float, step_wait: float = 2.0) -> int:
        """手动模式：按 steps 顺序执行。steps 为 ("move", 米) / ("turn", 秒)。"""
        time.sleep(1.0)  # DDS 发现

        for kind, value in steps:
            if kind == "move":
                tag = f"前进 {value:.2f} m" if value >= 0 else f"后退 {abs(value):.2f} m"
                self.get_logger().info(tag)
                self._move(value, linear_speed)
            else:
                tag = f"左转 {value:.1f} s" if value >= 0 else f"右转 {abs(value):.1f} s"
                self.get_logger().info(tag)
                self._turn(value, angular_speed)
            time.sleep(step_wait)

        self._stop()
        self.get_logger().info("手动动作完成，底盘已停止")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="底盘控制：不带参数播放默认演示，带参数则手动控制")
    parser.add_argument("--forward", type=float, default=None, metavar="M",
                        help="前进指定距离（米），如 --forward 0.3")
    parser.add_argument("--back", type=float, default=None, metavar="M",
                        help="后退指定距离（米），如 --back 0.2")
    parser.add_argument("--left", type=float, default=None, metavar="SEC",
                        help="以 angular 速度左转指定时长（秒），如 --left 2.0")
    parser.add_argument("--right", type=float, default=None, metavar="SEC",
                        help="以 angular 速度右转指定时长（秒），如 --right 2.0")
    parser.add_argument("--linear", type=float, default=0.1,
                        help="直线速度 m/s（默认 0.1，wheel 限速约 0.35 m/s）")
    parser.add_argument("--angular", type=float, default=0.4,
                        help="转向角速度 rad/s（默认 0.4）")
    parser.add_argument("--distance", type=float, default=0.5,
                        help="默认演示的前进/后退距离（米）")
    parser.add_argument("--turn-time", type=float, default=3.0,
                        help="默认演示的左转/右转时长（秒，左右对称抵消）")
    parser.add_argument("--step-wait", type=float, default=2.0,
                        help="每步动作之间的等待时间（秒，默认 2.0）")
    args = parser.parse_args()

    rclpy.init()
    node = BaseMoveDemo()
    try:
        # 手动模式：按 前进 -> 后退 -> 左转 -> 右转 的顺序执行给定动作
        steps = []
        if args.forward is not None:
            steps.append(("move", abs(args.forward)))
        if args.back is not None:
            steps.append(("move", -abs(args.back)))
        if args.left is not None:
            steps.append(("turn", abs(args.left)))
        if args.right is not None:
            steps.append(("turn", -abs(args.right)))

        if steps:
            code = node.run_manual(steps, args.linear, args.angular, args.step_wait)
        else:
            code = node.run_demo(args.distance, args.linear, args.angular,
                                 args.turn_time, args.step_wait)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()

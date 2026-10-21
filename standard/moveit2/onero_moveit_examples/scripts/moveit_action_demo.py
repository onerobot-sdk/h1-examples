#!/usr/bin/env python3
"""Plan a small joint target; execute the reviewed plan only with --execute."""
import argparse
import math
import time

import rclpy
from action_msgs.msg import GoalStatus
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState


class MoveItClient(Node):
    def __init__(self):
        super().__init__("onero_moveit_python_demo")
        self.state = {}
        self.create_subscription(JointState, "/joint_states", self.on_state, qos_profile_sensor_data)

    def on_state(self, message):
        stamp = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
        age = (self.get_clock().now().nanoseconds - stamp) * 1e-9
        if age < 0.0 or age > 0.5:
            return
        received = time.monotonic()
        for name, position in zip(message.name, message.position):
            if math.isfinite(position):
                self.state[name] = (position, received)

    def current_positions(self, names):
        def complete():
            return all(name in self.state and time.monotonic() - self.state[name][1] <= 0.5 for name in names)

        deadline = time.monotonic() + 10.0
        while rclpy.ok() and not complete() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
        if not complete():
            raise RuntimeError("Missing or stale joint feedback")
        return {name: self.state[name][0] for name in names}

    def wait(self, future, timeout):
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done():
            raise TimeoutError("Action timeout; timeout does not mean the goal was canceled")
        return future.result()

    def call_action(self, action_type, endpoint, goal):
        client = ActionClient(self, action_type, endpoint)
        try:
            if not client.wait_for_server(timeout_sec=10.0):
                raise RuntimeError(f"{endpoint} unavailable")
            handle = self.wait(client.send_goal_async(goal, feedback_callback=self.on_feedback), 10.0)
            if handle is None or not handle.accepted:
                raise RuntimeError(f"{endpoint} goal rejected")
            wrapped = self.wait(handle.get_result_async(), 60.0)
            if (wrapped.status != GoalStatus.STATUS_SUCCEEDED
                    or wrapped.result.error_code.val != MoveItErrorCodes.SUCCESS):
                raise RuntimeError(f"{endpoint}: status={wrapped.status}, error_code={wrapped.result.error_code.val}")
            return wrapped.result
        finally:
            client.destroy()

    def on_feedback(self, message):
        # Python 回调收到 FeedbackMessage 包装层。
        self.get_logger().info(f"feedback: {message.feedback.state}")

    def run(self, group, delta, execute):
        suffixes = ["l", "r"] if group == "both_arms" else ["l" if group == "left_arm" else "r"]
        names = [f"joint{i}-{suffix}" for suffix in suffixes for i in range(1, 8)]
        positions = self.current_positions(names)
        goal = MoveGroup.Goal()
        goal.request.group_name = group
        goal.request.num_planning_attempts = 1
        goal.request.allowed_planning_time = 5.0
        goal.request.max_velocity_scaling_factor = 0.05
        goal.request.max_acceleration_scaling_factor = 0.05
        goal.request.start_state.is_diff = True
        goal.planning_options.plan_only = True
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        constraints = Constraints()
        for name in names:
            joint = JointConstraint()
            joint.joint_name = name
            joint.position = positions[name]
            if name == "joint1-l":
                joint.position += delta
            if name == "joint1-r":
                joint.position += -delta if group == "both_arms" else delta
            joint.tolerance_above = joint.tolerance_below = 0.001
            joint.weight = 1.0
            constraints.joint_constraints.append(joint)
        goal.request.goal_constraints = [constraints]
        planned = self.call_action(MoveGroup, "/move_action", goal)
        trajectory = planned.planned_trajectory.joint_trajectory
        if not trajectory.points:
            raise RuntimeError("Empty planned trajectory")
        print("joint_names:", list(trajectory.joint_names))
        for point in trajectory.points:
            seconds = point.time_from_start.sec + point.time_from_start.nanosec * 1e-9
            print(f"t={seconds:.6f}", list(point.positions))
        if execute:
            confirmation = input("Review the entire trajectory and clear the workspace. Type EXECUTE: ")
            if confirmation != "EXECUTE":
                raise RuntimeError("Execution not confirmed")
            execution = ExecuteTrajectory.Goal()
            execution.trajectory = planned.planned_trajectory
            self.call_action(ExecuteTrajectory, "/execute_trajectory", execution)
            print("Execution action succeeded; verify actual joint feedback.")
        else:
            print("Plan-only complete; no execution goal was sent.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=["left_arm", "right_arm", "both_arms"], default="left_arm")
    parser.add_argument("--delta", type=float, default=0.02)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.delta) or abs(args.delta) > 0.05:
        parser.error("delta must be finite and within +/-0.05 rad")
    rclpy.init(args=[])
    node = MoveItClient()
    exit_code = 0
    try:
        node.run(args.group, args.delta, args.execute)
    except (RuntimeError, TimeoutError, EOFError) as error:
        node.get_logger().error(str(error))
        exit_code = 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

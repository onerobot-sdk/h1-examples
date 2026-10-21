#!/usr/bin/env python3
"""Copy the running move_group model parameters into a client YAML file."""
import argparse
from pathlib import Path

import rclpy
from rcl_interfaces.msg import ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, ListParameters
from rclpy.node import Node
from rclpy.parameter import parameter_value_to_python
import yaml


def request(node, service_type, endpoint, message):
    client = node.create_client(service_type, endpoint)
    try:
        if not client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError(f"{endpoint} unavailable; start the matching MoveIt service first")
        future = client.call_async(message)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
        if not future.done() or future.result() is None:
            raise RuntimeError(f"{endpoint} timed out")
        return future.result()
    finally:
        node.destroy_client(client)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/onero_moveit_params.yaml")
    args = parser.parse_args()
    rclpy.init(args=[])
    node = Node("onero_moveit_parameter_reader")
    try:
        listing = ListParameters.Request()
        listing.prefixes = ["robot_description_kinematics", "robot_description_planning"]
        listing.depth = 0
        names = ["robot_description", "robot_description_semantic"]
        names += request(node, ListParameters, "/move_group/list_parameters", listing).result.names
        query = GetParameters.Request()
        query.names = names
        values = request(node, GetParameters, "/move_group/get_parameters", query).values
        if len(values) != len(names):
            # rclcpp may return an empty batch if an optional parameter is uninitialized.
            # Read separately so initialized model parameters are still preserved.
            values = []
            for name in names:
                query.names = [name]
                result = request(node, GetParameters, "/move_group/get_parameters", query).values
                values.append(result[0] if result else ParameterValue())
        parameters = {
            name: parameter_value_to_python(value)
            for name, value in zip(names, values)
            if value.type != ParameterType.PARAMETER_NOT_SET
        }
        # ROS parameter YAML cannot infer an element type for an empty array.
        parameters = {name: value for name, value in parameters.items() if value != []}
        for name in names[:2]:
            if not isinstance(parameters.get(name), str) or not parameters[name]:
                raise RuntimeError(f"{name} is missing or empty on /move_group")
        path = Path(args.output)
        path.write_text(yaml.safe_dump({"/**": {"ros__parameters": parameters}}), encoding="utf-8")
        print(f"Wrote {len(parameters)} parameters to {path}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

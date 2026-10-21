#include <chrono>
#include <cmath>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include <moveit_msgs/action/execute_trajectory.hpp>
#include <moveit_msgs/action/move_group.hpp>
#include <moveit_msgs/msg/constraints.hpp>
#include <moveit_msgs/msg/joint_constraint.hpp>
#include <moveit_msgs/msg/move_it_error_codes.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <sensor_msgs/msg/joint_state.hpp>

using namespace std::chrono_literals;
using Clock = std::chrono::steady_clock;
using MoveGroup = moveit_msgs::action::MoveGroup;
using ExecuteTrajectory = moveit_msgs::action::ExecuteTrajectory;

template<class Action>
std::shared_ptr<typename Action::Result> callAction(
    const rclcpp::Node::SharedPtr& node, const std::string& endpoint,
    const typename Action::Goal& goal) {
    auto client = rclcpp_action::create_client<Action>(node, endpoint);
    if (!client->wait_for_action_server(10s)) throw std::runtime_error(endpoint + " unavailable");
    typename rclcpp_action::Client<Action>::SendGoalOptions options;
    options.feedback_callback = [](auto, const auto feedback) {
        // C++ 回调收到 Feedback 本体，直接访问 state。
        std::cout << "feedback: " << feedback->state << '\n';
    };
    auto accepted = client->async_send_goal(goal, options);
    if (rclcpp::spin_until_future_complete(node, accepted, 10s) != rclcpp::FutureReturnCode::SUCCESS) {
        throw std::runtime_error(endpoint + " goal response timeout");
    }
    const auto handle = accepted.get();
    if (!handle) throw std::runtime_error(endpoint + " goal rejected");
    auto finished = client->async_get_result(handle);
    if (rclcpp::spin_until_future_complete(node, finished, 60s) != rclcpp::FutureReturnCode::SUCCESS) {
        throw std::runtime_error(endpoint + " result timeout; timeout does not mean canceled");
    }
    const auto wrapped = finished.get();
    if (wrapped.code != rclcpp_action::ResultCode::SUCCEEDED || !wrapped.result ||
        wrapped.result->error_code.val != moveit_msgs::msg::MoveItErrorCodes::SUCCESS) {
        throw std::runtime_error(endpoint + " failed, error_code=" +
            std::to_string(wrapped.result ? wrapped.result->error_code.val : 0));
    }
    return wrapped.result;
}

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("onero_moveit_action_demo");
    const auto group = node->declare_parameter<std::string>("group", "left_arm");
    const double delta = node->declare_parameter<double>("delta", 0.02);
    const bool execute = node->declare_parameter<bool>("execute", false);
    int exit_code = 0;
    try {
        if (group != "left_arm" && group != "right_arm" && group != "both_arms") {
            throw std::runtime_error("Invalid planning group");
        }
        if (!std::isfinite(delta) || std::abs(delta) > 0.05) {
            throw std::runtime_error("delta must be finite and within +/-0.05 rad");
        }
        std::vector<std::string> names;
        for (const auto& suffix : std::vector<std::string>{"l", "r"}) {
            if ((group == "left_arm" && suffix == "r") || (group == "right_arm" && suffix == "l")) continue;
            for (int i = 1; i <= 7; ++i) names.push_back("joint" + std::to_string(i) + "-" + suffix);
        }
        struct Sample { double position; Clock::time_point received; };
        std::map<std::string, Sample> state;
        auto subscription = node->create_subscription<sensor_msgs::msg::JointState>(
            "/joint_states", rclcpp::SensorDataQoS(), [&](const sensor_msgs::msg::JointState& msg) {
                const double age = (node->now() - rclcpp::Time(msg.header.stamp)).seconds();
                if (age < 0.0 || age > 0.5) return;
                const auto received = Clock::now();
                for (std::size_t i = 0; i < msg.name.size() && i < msg.position.size(); ++i) {
                    if (std::isfinite(msg.position[i])) state[msg.name[i]] = {msg.position[i], received};
                }
            });
        auto complete = [&] {
            for (const auto& name : names) {
                if (!state.count(name) || Clock::now() - state.at(name).received > 500ms) return false;
            }
            return true;
        };
        const auto deadline = Clock::now() + 10s;
        while (rclcpp::ok() && !complete() && Clock::now() < deadline) rclcpp::spin_some(node);
        if (!complete()) throw std::runtime_error("Missing or stale joint feedback");

        MoveGroup::Goal goal;
        goal.request.group_name = group;
        goal.request.num_planning_attempts = 1;
        goal.request.allowed_planning_time = 5.0;
        goal.request.max_velocity_scaling_factor = 0.05;
        goal.request.max_acceleration_scaling_factor = 0.05;
        goal.request.start_state.is_diff = true;
        goal.planning_options.plan_only = true;
        goal.planning_options.planning_scene_diff.is_diff = true;
        goal.planning_options.planning_scene_diff.robot_state.is_diff = true;
        moveit_msgs::msg::Constraints constraints;
        for (const auto& name : names) {
            moveit_msgs::msg::JointConstraint joint;
            joint.joint_name = name;
            joint.position = state.at(name).position;
            if (name == "joint1-l") joint.position += delta;
            if (name == "joint1-r") joint.position += group == "both_arms" ? -delta : delta;
            joint.tolerance_above = joint.tolerance_below = 0.001;
            joint.weight = 1.0;
            constraints.joint_constraints.push_back(joint);
        }
        goal.request.goal_constraints.push_back(constraints);
        const auto planned = callAction<MoveGroup>(node, "/move_action", goal);
        const auto& trajectory = planned->planned_trajectory.joint_trajectory;
        if (trajectory.points.empty()) throw std::runtime_error("Empty planned trajectory");
        std::cout << "joint_names:";
        for (const auto& name : trajectory.joint_names) std::cout << ' ' << name;
        std::cout << '\n';
        for (const auto& point : trajectory.points) {
            std::cout << "t=" << point.time_from_start.sec + point.time_from_start.nanosec * 1e-9;
            for (double position : point.positions) std::cout << ' ' << position;
            std::cout << '\n';
        }
        if (execute) {
            std::cout << "Review the entire trajectory and clear the workspace. Type EXECUTE: " << std::flush;
            std::string confirmation;
            if (!std::getline(std::cin, confirmation) || confirmation != "EXECUTE") {
                throw std::runtime_error("Execution not confirmed");
            }
            ExecuteTrajectory::Goal execution;
            execution.trajectory = planned->planned_trajectory;
            callAction<ExecuteTrajectory>(node, "/execute_trajectory", execution);
            std::cout << "Execution action succeeded; verify actual joint feedback.\n";
        } else {
            std::cout << "Plan-only complete; no execution goal was sent.\n";
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        exit_code = 1;
    }
    node.reset();
    rclcpp::shutdown();
    return exit_code;
}

#include <cmath>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <Eigen/Geometry>
#include <geometry_msgs/msg/pose.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>
#include <moveit_msgs/msg/move_it_error_codes.hpp>
#include <rclcpp/rclcpp.hpp>

using MoveGroup = moveit::planning_interface::MoveGroupInterface;

geometry_msgs::msg::Pose currentPose(
    const moveit::core::RobotState& state, const std::string& link) {
    const auto& transform = state.getGlobalLinkTransform(link);
    const Eigen::Quaterniond quaternion(transform.rotation());
    geometry_msgs::msg::Pose pose;
    pose.position.x = transform.translation().x();
    pose.position.y = transform.translation().y();
    pose.position.z = transform.translation().z();
    pose.orientation.x = quaternion.x();
    pose.orientation.y = quaternion.y();
    pose.orientation.z = quaternion.z();
    pose.orientation.w = quaternion.w();
    return pose;
}

void printTrajectory(const moveit_msgs::msg::RobotTrajectory& trajectory) {
    const auto& joints = trajectory.joint_trajectory;
    if (joints.points.empty()) throw std::runtime_error("Planner returned an empty trajectory");
    std::cout << "joint_names:";
    for (const auto& name : joints.joint_names) std::cout << ' ' << name;
    std::cout << '\n';
    for (const auto& point : joints.points) {
        std::cout << "t=" << point.time_from_start.sec + point.time_from_start.nanosec * 1e-9;
        for (double position : point.positions) std::cout << ' ' << position;
        std::cout << '\n';
    }
}

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>(
        "onero_move_group_demo",
        rclcpp::NodeOptions().automatically_declare_parameters_from_overrides(true));
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(node);
    std::thread spinner([&executor] { executor.spin(); });
    int exit_code = 0;
    try {
        const auto group_name = node->get_parameter_or<std::string>("group", "left_arm");
        const auto goal_type = node->get_parameter_or<std::string>("goal", "joint");
        const double delta = node->get_parameter_or<double>("delta", 0.02);
        const bool execute = node->get_parameter_or<bool>("execute", false);
        if (group_name != "left_arm" && group_name != "right_arm" && group_name != "both_arms") {
            throw std::runtime_error("group must be left_arm, right_arm, or both_arms");
        }
        if (!std::isfinite(delta) || std::abs(delta) > 0.05) {
            throw std::runtime_error("delta must be finite and within +/-0.05 rad");
        }

        // node 已由 shared_ptr 托管；背景 executor 持续处理关节反馈。
        MoveGroup group(node, group_name, nullptr, rclcpp::Duration::from_seconds(10.0));
        group.setPlanningTime(5.0);
        group.setNumPlanningAttempts(1);
        group.setMaxVelocityScalingFactor(0.05);
        group.setMaxAccelerationScalingFactor(0.05);
        const auto state = group.getCurrentState(10.0);
        if (!state) throw std::runtime_error("No complete current robot state within 10 seconds");
        state->update();
        group.setStartState(*state);
        group.setPoseReferenceFrame(group.getRobotModel()->getModelFrame());

        MoveGroup::Plan plan;
        if (goal_type == "joint") {
            // 名称映射包含当前组的全部关节，不依赖双臂 vector 的排列顺序。
            std::map<std::string, double> targets;
            for (const auto& name : group.getJointNames()) {
                const double value = state->getVariablePosition(name);
                if (!std::isfinite(value)) throw std::runtime_error("Non-finite joint feedback");
                targets[name] = value;
            }
            if (group_name != "right_arm") targets.at("joint1-l") += delta;
            if (group_name != "left_arm") targets.at("joint1-r") +=
                group_name == "both_arms" ? -delta : delta;
            if (!group.setJointValueTarget(targets)) throw std::runtime_error("Invalid joint target");
        } else if (goal_type == "named") {
            const auto name = node->get_parameter_or<std::string>(
                "named_target", group_name == "both_arms" ? "dual_ready" : "ready");
            if (!group.setNamedTarget(name)) throw std::runtime_error("Unknown named target: " + name);
        } else if (goal_type == "pose" || goal_type == "cartesian") {
            if (goal_type == "cartesian" && group_name == "both_arms") {
                throw std::runtime_error("Cartesian example requires a single-arm group");
            }
            std::vector<std::string> tips;
            if (group_name != "right_arm") tips.push_back("left_link7");
            if (group_name != "left_arm") tips.push_back("right_link7");
            for (const auto& tip : tips) {
                auto pose = currentPose(*state, tip);
                pose.position.z += 0.005;  // 从当前 FK 位姿向上移动 5 mm。
                if (goal_type == "pose") {
                    if (!group.setPoseTarget(pose, tip)) throw std::runtime_error("Invalid pose target");
                } else {
                    group.setEndEffectorLink(tip);
                    moveit_msgs::msg::MoveItErrorCodes error;
                    const double fraction = group.computeCartesianPath(
                        {currentPose(*state, tip), pose}, 0.001, plan.trajectory, true, &error);
                    std::cout << "fraction=" << fraction << " error_code=" << error.val << '\n';
                    if (error.val != moveit_msgs::msg::MoveItErrorCodes::SUCCESS ||
                        !std::isfinite(fraction) || std::abs(fraction - 1.0) > 1e-6) {
                        throw std::runtime_error("Cartesian path is incomplete; execution skipped");
                    }
                }
            }
        } else {
            throw std::runtime_error("goal must be joint, named, pose, or cartesian");
        }

        if (goal_type != "cartesian") {
            const auto result = group.plan(plan);
            if (result != moveit::core::MoveItErrorCode::SUCCESS) {
                throw std::runtime_error("Planning failed: " + std::to_string(result.val));
            }
        }
        printTrajectory(plan.trajectory);
        if (execute) {
            std::cout << "Review the entire trajectory and clear the workspace. Type EXECUTE: " << std::flush;
            std::string confirmation;
            if (!std::getline(std::cin, confirmation) || confirmation != "EXECUTE") {
                throw std::runtime_error("Execution not confirmed");
            }
            // 执行这次打印的轨迹；不用 move() 重新规划。
            const auto result = group.execute(plan.trajectory);
            if (result != moveit::core::MoveItErrorCode::SUCCESS) {
                throw std::runtime_error("Execution failed: " + std::to_string(result.val));
            }
            std::cout << "Execution action succeeded; verify actual joint feedback.\n";
        } else {
            std::cout << "Plan-only complete; no execution goal was sent.\n";
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        exit_code = 1;
    }
    // MoveGroupInterface 在离开 try 作用域时先析构，然后停止 executor。
    executor.cancel();
    spinner.join();
    node.reset();
    rclcpp::shutdown();
    return exit_code;
}

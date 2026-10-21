cmake_minimum_required(VERSION 3.8)
project(onero_moveit_examples)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(move_group_demo src/move_group_demo.cpp)
target_compile_features(move_group_demo PRIVATE cxx_std_17)
ament_target_dependencies(move_group_demo
  geometry_msgs moveit_msgs moveit_ros_planning_interface rclcpp)

add_executable(action_demo src/action_demo.cpp)
target_compile_features(action_demo PRIVATE cxx_std_17)
ament_target_dependencies(action_demo
  moveit_msgs rclcpp rclcpp_action sensor_msgs)

install(TARGETS move_group_demo action_demo DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS scripts/moveit_action_demo.py scripts/read_moveit_params.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()

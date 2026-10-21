# MoveIt2 客户端示例

本目录包含完整 ROS 2 包 [`onero_moveit_examples`](./onero_moveit_examples/)，演示双臂规划、读取服务端模型参数，以及执行已审查的规划轨迹。

按标准版现有接口整理。智能版使用前还需核对 Zenoh 通信、服务端 MoveIt 配置和关节反馈，当前不声明已完成智能版验证。

## 文件与用途

| 文件 | 用途 | 运行前提 |
| --- | --- | --- |
| [`src/move_group_demo.cpp`](./onero_moveit_examples/src/move_group_demo.cpp) | 使用 MoveGroupInterface 规划关节、命名姿态、位姿目标和单臂笛卡尔路径 | 客户端模型参数，以及同版本 `armcontrol` 模型资源 |
| [`src/action_demo.cpp`](./onero_moveit_examples/src/action_demo.cpp) | 从实时关节反馈生成小幅目标，调用 MoveGroup / ExecuteTrajectory Action | 可用的 `/move_action`、`/execute_trajectory` 和 `/joint_states` |
| [`scripts/moveit_action_demo.py`](./onero_moveit_examples/scripts/moveit_action_demo.py) | Python Action 示例，可直接运行或通过 ROS 包启动 | 与 C++ Action 相同；无需本地 URDF/SRDF |
| [`scripts/read_moveit_params.py`](./onero_moveit_examples/scripts/read_moveit_params.py) | 从 `/move_group` 读取 URDF、SRDF、运动学和限位，生成客户端 YAML | `/move_group` 参数服务可访问 |
| [`CMakeLists.txt`](./onero_moveit_examples/CMakeLists.txt)、[`package.xml`](./onero_moveit_examples/package.xml) | 构建、依赖和安装定义 | C++17、ament_cmake |

## 环境与适用范围

- 验证基线：Ubuntu 24.04、ROS 2 Jazzy、MoveIt 2.12.4。
- 现有手册记录的验证范围为 ARM64 / x86_64 客户端编译、规划和模拟执行；不代表真机运动已经验证。
- 示例依赖 **A1 双臂 MoveIt 配置**：规划组为 `left_arm`、`right_arm`、`both_arms`，关节为 `joint1-l` 至 `joint7-l`、`joint1-r` 至 `joint7-r`，末端为 `left_link7`、`right_link7`。不能替换为 H1 v1.4 整机显示模型中的名称。
- 机器人端需先启动对应的 MoveIt 服务和真实关节反馈。本包只运行客户端，不启动驱动、MoveIt 服务或 fake joint states。
- 开发电脑按[标准版使用说明](../python-control/README.md#电脑端-ros-2-与-dds-配置)准备 DDS；客户端与机器人使用一致的 ROS 域、中间件和系统时间。
- Humble 的高级 C++ API 需要适配；其他平台尚未验证。

完整接口说明和规划参数见[开发手册：MoveIt2](https://onerobot-sdk.github.io/onerobot-H1/advanced/moveit2.html)。

## 获取与编译

先获取完整仓库，再把完整 ROS 包放入工作空间。下面假设仓库位于 `~/h1-examples`；已下载 ZIP 时使用解压后的实际路径。

```bash
git clone https://github.com/onerobot-sdk/h1-examples.git ~/h1-examples
mkdir -p ~/moveit_example_ws/src
cp -a ~/h1-examples/standard/moveit2/onero_moveit_examples ~/moveit_example_ws/src/

source /opt/ros/jazzy/setup.bash
sudo apt-get install -y build-essential cmake python3-colcon-common-extensions python3-yaml \
  ros-jazzy-moveit-ros-planning-interface ros-jazzy-moveit-msgs \
  ros-jazzy-ament-cmake ros-jazzy-rclcpp ros-jazzy-rclcpp-action ros-jazzy-rclpy \
  ros-jazzy-sensor-msgs ros-jazzy-geometry-msgs \
  ros-jazzy-action-msgs ros-jazzy-rcl-interfaces

cd ~/moveit_example_ws/src/onero_moveit_examples
chmod +x scripts/read_moveit_params.py scripts/moveit_action_demo.py
cd ~/moveit_example_ws
colcon build --packages-select onero_moveit_examples
source install/local_setup.bash
```

如果本地已经有同名 ROS 包，请更新已有包，不要把两份同名包同时放入工作空间。

## 运行

每个运行终端先加载 ROS、设备 SDK（如已安装）以及示例包环境：

```bash
source /opt/ros/jazzy/setup.bash
if [ -f /opt/wlab/robot/setup.bash ]; then
  source /opt/wlab/robot/setup.bash
fi
source ~/moveit_example_ws/install/local_setup.bash
```

运行 Action 示例，默认只规划：

```bash
ros2 run onero_moveit_examples action_demo
ros2 run onero_moveit_examples moveit_action_demo.py --group left_arm
```

高级 C++ 接口还需要模型参数和客户端对应模型资源。先读取参数，再启动：

```bash
ros2 run onero_moveit_examples read_moveit_params.py --output /tmp/onero_moveit_params.yaml
ros2 run onero_moveit_examples move_group_demo --ros-args \
  --params-file /tmp/onero_moveit_params.yaml
```

`/tmp/onero_moveit_params.yaml` 保存在执行读取命令的机器上；切换设备或模型配置后应重新生成。

三个规划程序默认只规划，默认速度与加速度缩放为 `0.05`。执行需显式启用 `execute:=true` 或 `--execute`，并在审查整条输出轨迹后输入 `EXECUTE`。更多目标、双臂和执行示例见[手册](https://onerobot-sdk.github.io/onerobot-H1/advanced/moveit2.html#执行已规划轨迹)。

本包保留原有 `package.xml` 中的 `BSD-3-Clause` 许可声明。

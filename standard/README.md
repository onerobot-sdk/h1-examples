# 标准版示例

[返回示例索引](../README.md) · [智能版入口](../intelligent/README.md)

本目录面向 H1 标准版。推荐使用最新配套固件，基础环境为 Ubuntu 24.04 / ROS 2 Jazzy，通信方式为 **原生 Zenoh（`rmw_zenoh_cpp`）**。示例是客户端，调用机器人已有接口；机器人对应服务需要事先运行。

## 连接与环境

建议先查询[设备固件版本](https://onerobot-sdk.github.io/onerobot-H1/firmware.html)，并按[OTA 说明](https://onerobot-sdk.github.io/onerobot-H1/faq/network-ota.html#q17)升级到最新配套固件。开发电脑完成 [ROS 2 Jazzy 安装](https://onerobot-sdk.github.io/onerobot-H1/getting-started/ros2-installation.html)，连接机器人所在网络，再按 [Python 控制说明](python-control/README.md#电脑端-ros-2-通信配置)准备通信环境。

先完成[开发电脑的 Zenoh 配置](https://onerobot-sdk.github.io/onerobot-H1/getting-started/communication.html#pc-zenoh)，包括支持包、router 与环境文件；仅修改 `RMW_IMPLEMENTATION` 不足以完成连接。配置完成后，在电脑的运行终端执行：

```bash
source ~/h1-zenoh-env.sh
ros2 daemon stop
ros2 topic list
```

确认能看到 `/device_info` 等机器人话题，再按通信配置页订阅数据检查连接。若此前使用其他中间件，先退出电脑上的旧示例或 RViz2，再加载环境。机器人本机运行时使用设备交付的 ROS 环境与通信配置。

暂时无法升级的标准版，可查看 Python 使用说明中的[兼容配置](python-control/README.md#电脑端-ros-2-与-dds-配置)。

## Python 控制

[`python-control/demos/`](python-control/demos/) 包含 8 个可直接运行的 Python 脚本，无需 `colcon build`。它们依赖 `rclpy` 以及 `std_msgs`、`sensor_msgs`、`geometry_msgs`、`diagnostic_msgs` 中的相应消息包；每个脚本的用途见[根目录索引](../README.md#示例用途索引)。

从本仓库根目录进入脚本目录，先查看参数：

```bash
cd standard/python-control/demos
python3 light_control_demo.py --help
```

具体动作、参数、单位、坐标系与话题见 [`python-control/README.md`](python-control/README.md)。脚本不带参数会执行默认演示；控制完成条件和停止方式应按该说明逐项确认。

## MoveIt2

完整包位于 [`moveit2/onero_moveit_examples/`](moveit2/onero_moveit_examples/)，包名为 `onero_moveit_examples`。其中两个 C++ 客户端需要编译；两个 Python 工具也可以直接运行。

使用前确认机器人已启动配套 **A1 双臂 MoveIt 服务**，可提供 `/move_action`、`/execute_trajectory`、真实 `/joint_states` 及 `/move_group` 参数服务。客户端和机器人需匹配 ROS 发行版、消息版本与通信环境；跨机器使用还需同步系统时钟。

客户端环境基线为 **Ubuntu 24.04 / ROS 2 Jazzy / MoveIt 2.12.4**。`move_group_demo` 额外需要模型参数及同版本 `armcontrol` 模型资源；C++ / Python Action 客户端直接请求服务端规划，无需这些客户端模型资源。H1 v1.4 显示模型不能替代本包要求的 MoveIt 模型。

依赖安装、复制完整 ROS 包、编译和只规划运行步骤集中在 [MoveIt2 示例 README](moveit2/README.md)。按该说明开始，再根据需要查阅[开发手册中的完整接口和参数](https://onerobot-sdk.github.io/onerobot-H1/advanced/moveit2.html)。

现有手册记录的验证范围为 ARM64 / x86_64 客户端编译、规划和模拟执行；目标真机的驱动、模型和反馈仍需核对。

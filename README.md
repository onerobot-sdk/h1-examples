# Onero H1 示例

本仓库提供 Onero H1 的 Python 控制脚本、MoveIt2 客户端示例和智能版洗衣应用。接口定义、连接方式及设备说明见 [H1 开发手册](https://onerobot-sdk.github.io/onerobot-H1/)。

## 先选择产品版本

| 产品版本 | 通信方式（推荐固件） | 示例入口 |
| --- | --- | --- |
| H1 标准版 | ROS 2 Jazzy + 原生 Zenoh（`rmw_zenoh_cpp`） | [标准版运行说明](standard/README.md)；基础 Python 与 MoveIt2 示例归入标准版 |
| H1 智能版 | ROS 2 Jazzy + 原生 Zenoh（`rmw_zenoh_cpp`） | [智能版连接与示例说明](intelligent/README.md)；[NVIDIA 计算板洗衣应用](intelligent/laundry/README.md) |

建议先将机器人升级到[最新配套固件](https://onerobot-sdk.github.io/onerobot-H1/firmware.html)，标准版和智能版统一按[原生 Zenoh 通信配置](https://onerobot-sdk.github.io/onerobot-H1/getting-started/communication.html)准备电脑。浏览器打开 `http://<机器人 IP>:8080/`，在“状态 → 机器人信息 → 软件版本”查看已安装版本；升级操作见[网络配置与 OTA](https://onerobot-sdk.github.io/onerobot-H1/faq/network-ota.html#q17)。

示例仍按产品和应用需求分类。通信方式统一不代表标准版源码已经完成智能版适配；复用前仍需核对接口、模型、依赖服务和运行位置。

## 获取示例与运行包

标准版示例源码与全部使用说明可通过 **Code → Download ZIP** 下载；也可以使用 Git。洗衣运行包请单独从 Release 附件下载：

```bash
git clone https://github.com/onerobot-sdk/h1-examples.git
cd h1-examples
```

- Python 控制示例位于 [`standard/python-control/`](standard/python-control/)，参数与话题说明见 [`standard/python-control/README.md`](standard/python-control/README.md)。
- MoveIt2 完整 ROS 包位于 [`standard/moveit2/onero_moveit_examples/`](standard/moveit2/onero_moveit_examples/)，依赖、编译与运行入口见 [`standard/moveit2/README.md`](standard/moveit2/README.md)。请保留包内的 `CMakeLists.txt`、`package.xml`、`src/` 和 `scripts/`。
- 智能版洗衣应用位于 [`intelligent/laundry/`](intelligent/laundry/)，提供使用说明和场景地图，已编译程序、ONNX 模型、URDF 与运行依赖通过 [Release 附件](https://github.com/onerobot-sdk/h1-examples/releases/tag/laundry-runtime-2026.10.21-rc1) 下载；安装及启动步骤见 [洗衣示例 README](intelligent/laundry/README.md)。

## 示例用途索引

以下示例以 **Ubuntu 24.04 / ROS 2 Jazzy** 为基础环境。“开发电脑 / 机器人”表示可将客户端放在连接机器人的开发电脑上，也可放在已配置相应依赖的机器人上；两端的通信环境和接口服务须匹配。依赖列列出主要客户端包，安装步骤见各运行说明。

| 示例与用途 | 用途 | 适用版本 | 运行位置 | 主要依赖 |
| --- | --- | --- | --- | --- |
| [预置动作 `arm_action_demo.py`](standard/python-control/demos/arm_action_demo.py) | 顺序触发挥手、招手等动作，并监听动作状态 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`std_msgs`；机器人预置动作服务 |
| [关节运动 `movej_demo.py`](standard/python-control/demos/movej_demo.py) | 左右臂 MoveJ，支持自定义 7 个关节角 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`std_msgs`、`diagnostic_msgs`；机械臂控制服务 |
| [点到点运动 `movep_demo.py`](standard/python-control/demos/movep_demo.py) | 左右臂笛卡尔位姿目标，配合 MoveJ 复位 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`std_msgs`、`diagnostic_msgs`；机械臂控制服务 |
| [直线运动 `movel_demo.py`](standard/python-control/demos/movel_demo.py) | 先 MoveJ 到收拢姿态，再执行笛卡尔直线运动 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`std_msgs`、`diagnostic_msgs`；机械臂控制服务 |
| [底盘 `base_move_demo.py`](standard/python-control/demos/base_move_demo.py) | 发布前进、后退和转向速度，按时间控制运动 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`geometry_msgs`；底盘服务 |
| [升降 `lift_control_demo.py`](standard/python-control/demos/lift_control_demo.py) | 相对升降；默认包含抬臂、下降、上升与恢复手臂 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`sensor_msgs`、`std_msgs`；升降及预置动作服务 |
| [头部 `head_control_demo.py`](standard/python-control/demos/head_control_demo.py) | 摇头、点头或指定俯仰与偏航角 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`sensor_msgs`；头部服务 |
| [灯光 `light_control_demo.py`](standard/python-control/demos/light_control_demo.py) | 四块灯板的颜色、亮度、闪烁与开关 | 标准版 | 开发电脑 / 机器人 | `rclpy`、`std_msgs`；灯板服务 |
| [C++ MoveGroup `move_group_demo.cpp`](standard/moveit2/onero_moveit_examples/src/move_group_demo.cpp) | 关节、命名姿态、位姿和单臂笛卡尔路径规划；默认只规划 | 标准版，需配套 A1 双臂 MoveIt 配置 | 开发电脑 / 机器人 | `ament_cmake`、`rclcpp`、MoveIt 规划接口；客户端模型参数及同版本模型资源 |
| [C++ Action `action_demo.cpp`](standard/moveit2/onero_moveit_examples/src/action_demo.cpp) | 根据当前关节反馈请求规划，可执行同一条规划轨迹；默认只规划 | 标准版，需配套 A1 双臂 MoveIt 配置 | 开发电脑 / 机器人 | `ament_cmake`、`rclcpp`、`rclcpp_action`、`moveit_msgs`、`sensor_msgs` |
| [Python Action `moveit_action_demo.py`](standard/moveit2/onero_moveit_examples/scripts/moveit_action_demo.py) | Python 版规划与轨迹执行客户端；默认只规划，可直接运行 | 标准版，需配套 A1 双臂 MoveIt 配置 | 开发电脑 / 机器人 | `rclpy`、`moveit_msgs`、`action_msgs`、`sensor_msgs` |
| [模型参数读取 `read_moveit_params.py`](standard/moveit2/onero_moveit_examples/scripts/read_moveit_params.py) | 从运行中的 `/move_group` 读取模型、运动学和限位参数，写入本地 YAML | 标准版，需配套 A1 双臂 MoveIt 配置 | 运行 MoveGroup 客户端的开发电脑 / 机器人 | `rclpy`、`rcl_interfaces`、`python3-yaml` |
| [洗衣应用 `laundry/`](intelligent/laundry/README.md) | 识别与抓取衣服、开门、放衣、关门并归位；提供网页控制台，不按洗衣机启动按钮 | 智能版，需配套场景与三处深度相机 | NVIDIA 计算板；电脑通过 SSH 隧道操作网页 | ROS 2 Jazzy、原生 Zenoh、OpenCV DNN、RBDL/HPP-FCL/Pinocchio；见应用依赖清单 |

Python 控制脚本不带参数时会执行默认演示，其中手臂、底盘、升降和头部示例会真实驱动机器人。先阅读对应说明并用 `--help` 查看参数，再选择目标动作。MoveIt2 的三个规划程序默认不执行；显式启用执行后，还需审查打印的轨迹并在终端输入 `EXECUTE`。

MoveIt2 示例面向 **A1 双臂 MoveIt 配置**，使用 `joint1-l`～`joint7-l`、`joint1-r`～`joint7-r` 等关节名，与 H1 v1.4 整机显示模型不同。客户端环境基线为 MoveIt **2.12.4**；具体平台兼容性、模型依赖及真机使用边界见 [MoveIt2 手册](https://onerobot-sdk.github.io/onerobot-H1/advanced/moveit2.html)。

## 其他开发入口

- [接口示例索引](https://onerobot-sdk.github.io/onerobot-H1/examples/)：传感器、诊断、导航、SLAM、人脸和手势等接口命令与代码片段仍保留在手册对应章节。
- [LeRobot 适配器 `OpenWonderLabs/onero_lerobot`](https://github.com/OpenWonderLabs/onero_lerobot)：独立维护的外部项目，提供数据录制、回放及策略接入；安装和使用见 [LeRobot 手册](https://onerobot-sdk.github.io/onerobot-H1/software/lerobot.html)。
- [智能版洗衣场景与部署](https://onerobot-sdk.github.io/onerobot-H1/example/laundry.html)：相机要求、场景尺寸、8090 地图导入与 NVIDIA 计算板部署。洗衣部分按运行包交付，无需客户编译业务 C++；下载入口和环境检查见 `intelligent/laundry/README.md`。

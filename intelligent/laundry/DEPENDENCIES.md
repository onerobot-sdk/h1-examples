# 运行依赖说明

本包按 Ubuntu 24.04 ARM64、ROS 2 Jazzy、Python 3.12 交付。二进制文件依赖同一环境系列的 ROS 与系统动态库；操作系统名称相同并不保证二进制兼容。具体组件信息以随包 `manifest.json` 为准。

## 随包组件

`install/` 包含以下六个包的完整运行内容：

| 包 | 用途 |
| --- | --- |
| `grasp` | 导航、双臂、升降、夹爪及洗衣动作程序 |
| `base_interfaces_msg` | 自定义 ROS 2 接口及运行时类型支持 |
| `h1_laundry` | 调度、视觉和网页服务 |
| `rbdl_vendor` | RBDL 3.3.1 及 URDF Reader |
| `hpp_fcl_vendor` | HPP-FCL 2.4.5 |
| `pinocchio_vendor` | Pinocchio 3.9.0 |

模型、URDF、网页、launch 文件和动态库均应保留在原目录。不要用系统中的其他 Pinocchio、Coal/HPP-FCL 或 RBDL 版本替换随包库，也不要删减自定义消息的类型支持文件。

## Python 环境

在最终安装位置运行：

```bash
bash scripts/setup_python.sh
.venv/bin/python -m pip check
```

脚本使用系统 Python 3.12 创建独立 `.venv`，不启用 `--system-site-packages`，默认以 `--no-index` 从随包 `wheelhouse/` 离线安装依赖。轮子适用于交付的 ARM64 / Python 3.12 环境，不用于 x86 电脑或其他 Python 版本。

启动脚本加载 `/opt/ros/jazzy/setup.bash` 后引入 ROS Python 模块。`rclpy`、ROS 消息和 `ament_index_python` 来自设备的 ROS 安装，不从 PyPI 安装。不要用 Conda Python 替换，也不要使用 `sudo pip` 或 `--break-system-packages`。

应用的主要 Python 依赖如下，安装时以随包 `requirements.txt` 和 `constraints.txt` 为准，不逐个修改版本：

| 包 | 版本 | 用途 |
| --- | --- | --- |
| `numpy` | 2.2.6 | 图像、深度和矩阵数据 |
| `opencv-python-headless` | 4.12.0.88 | OpenCV DNN CPU 推理和图像处理 |
| `fastapi` | 0.116.1 | 网页后端接口 |
| `uvicorn` | 0.35.0 | HTTP 服务 |
| `websockets` | 15.0.1 | 网页实时状态 |
| `PyYAML` | 6.0.2 | YAML 配置 |

`opencv-python-headless` 的导入名是 `cv2`。不要在同一个环境额外安装 `opencv-python` 或 `opencv-contrib-python`，它们提供同名模块。系统自带的 OpenCV 也不能代替本包固定的推理版本。

当前视觉路径使用 OpenCV CPU 推理，不要求 CUDA、cuDNN、TensorRT、PyTorch、ONNX Runtime 或 MobileSAM。网页静态文件已随包交付，无需 Node.js 或前端构建工具。

## 系统与 ROS

设备应已安装 ROS 2 Jazzy 与 `rmw_zenoh_cpp`，保留交付的 Zenoh Router/Session 配置。需要系统运行库及 ROS 的 C++/Python 客户端、launch、消息、TF 和包索引组件。系统和 ROS 依赖由预装环境提供，`wheelhouse/` 只提供 Python 依赖。

运行 `bash scripts/check_system.sh` 可只读检查系统包，查看缺失项与安装建议；该脚本不会执行安装。缺失的系统包应来自 Ubuntu 24.04 / ROS Jazzy 对应软件源，不混装其他发行版或用 `/usr/local` 中的同名库覆盖。

本包无需客户安装 C++ 编译工具链或 `colcon`。若检查出现动态库 `not found`，按错误中的库名和交付环境信息补齐运行依赖；不要通过复制其他机器的系统库解决。

`doctor.sh` 仅检查离线运行环境，不连接 ROS 图。离线检查与模拟网页通过，仅证明程序可启动；真机执行还依赖地图、定位、图像、标定、动作参数及机器人标准 SDK 服务。

## 许可与资源

第三方许可与声明保存在 `licenses/`，应随运行包一并保留。应用、ONNX 模型和 URDF 的使用范围遵循交付约定；本包不因此获得统一的开源许可，也不应把项目资源另行标注为第三方开源模型。

# 智能版开发入口

[返回示例索引](../README.md) · [标准版入口](../standard/README.md)

H1 智能版由 RK3576 主控与 NVIDIA 计算板组成，当前使用 ROS 2 Jazzy 和 **原生 Zenoh（`rmw_zenoh_cpp`）**。应用可按其部署要求运行在开发电脑、RK3576 或 NVIDIA 计算板；运行位置和依赖须由具体应用说明确定。

## 连接与 Zenoh 配置

按以下顺序准备环境：

1. 阅读[双板连接与地址说明](https://onerobot-sdk.github.io/onerobot-H1/getting-started/intelligent.html#connection)，确认开发电脑、RK3576 和 NVIDIA 计算板的连接关系。
2. 按[登录说明](https://onerobot-sdk.github.io/onerobot-H1/getting-started/intelligent.html#login)登录 RK3576，查询 NVIDIA 计算板的实际 IP 后继续登录。
3. 按[开发电脑的 Zenoh 环境](https://onerobot-sdk.github.io/onerobot-H1/getting-started/intelligent.html#pc-zenoh)配置电脑 router 与终端环境。板端继续使用设备交付配置。
4. 完成[通信验证](https://onerobot-sdk.github.io/onerobot-H1/getting-started/intelligent.html#verify)，再准备目标应用的依赖。

版本差异见[产品版本与开发路径](https://onerobot-sdk.github.io/onerobot-H1/getting-started/editions.html)。

## 洗衣服场景示例

[`laundry/`](laundry/) 提供运行在 NVIDIA 计算板上的洗衣应用使用说明和运行包下载入口：视觉识别、任务调度、C++ 八步动作状态机和网页控制台。它通过 H1 SDK 完成取衣、开门、放衣、关门与归位，不包含按下洗衣机启动按钮。

1. 阅读[洗衣示例 README](laundry/README.md)，确认深度相机、场景和运行环境。
2. 按[场景搭建与地图导入说明](https://onerobot-sdk.github.io/onerobot-H1/example/laundry.html#scene)量测场景，使用 H1 的 8090 工具导入配套地图。
3. 在 NVIDIA 计算板上按[运行包说明](laundry/README.md)安装依赖并完成离线检查，先查看 mock 页面，再做真机单步验收。

本目录保留说明和原始地图 ZIP；运行包通过 [Release 附件](https://github.com/onerobot-sdk/h1-examples/releases/tag/laundry-runtime-2026.10.21-rc1) 下载，包含已编译程序、三类别 ONNX 模型、URDF、运行脚本和固定版本的 Python 离线依赖。系统与 ROS 依赖由设备预装环境提供，见[依赖说明](laundry/DEPENDENCIES.md)。

洗衣应用面向 H1 智能版配套的 NVIDIA 计算板，目标环境为 Ubuntu 24.04 ARM64 / ROS 2 Jazzy，使用原生 Zenoh。更换设备或场景后，需重新核对相机标定、地图和动作参数，并按部署说明完成单步检查。

`standard/` 中的源码和 Cyclone DDS 配置仍属于标准版；它们尚未作为智能版兼容示例发布。复用接口代码时，需要核对目标设备的接口、消息类型、依赖服务和运行位置。

其余接口命令和代码片段仍可在 [H1 开发手册](https://onerobot-sdk.github.io/onerobot-H1/)中查阅。[LeRobot 适配器](https://github.com/OpenWonderLabs/onero_lerobot)由独立仓库维护，其适用通信环境与运行条件以该项目说明为准。

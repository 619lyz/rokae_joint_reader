# ROKAE Joint Reader

一个只读的小工具，用来读取这台 ROKAE 机器人各控制器当前关节角。它适合在数据采集前后记录标准姿态，例如固定 TaiHu 机身、左臂和右臂初始位，保证训练和部署时机器人构型一致。

## 当前适配的机器人

当前配置对应这台轮式人形机器人上的三个 ROKAE 控制器：

| 部位 | IP | Robot Assist 显示/用途 | SDK 类 |
| --- | --- | --- | --- |
| 右臂 | `192.168.71.160` | `AR5-5_0.7R-W4C1C1`，右 7 轴机械臂 | `xMateErProRobot` |
| 左臂 | `192.168.71.161` | `AR5-5_0.7L-W4C1C1`，左 7 轴机械臂 | `xMateErProRobot` |
| 机身/TaiHu | `192.168.71.254` | `TaiHu`，机身/腰部控制器 | `Robot_T_Industrial_4`，备用 `IndustrialRobot_4` |

本机在机器人网段上的 IP 默认为：

```text
192.168.71.56
```

## 文件说明

```text
ROKAE_Joint_Reader        # 双击启动 GUI 的 Linux 可执行入口
read_rokae_joints_gui.py  # GUI 界面，支持单次读取和定时刷新
read_rokae_joints.py      # 实际读取关节角的只读脚本
```

运行后可能自动生成：

```text
logs/
_rokae_log_/
__pycache__/
```

这些是 SDK 日志和 Python 缓存，可以删除；下次运行可能再次生成。

## 使用方式

### GUI

双击：

```text
ROKAE_Joint_Reader
```

界面里可以选择：

```text
all
right_arm
left_arm
taihu
```

按钮说明：

```text
Read Joints   读取一次
Start Live    按设定间隔持续刷新
Stop Live     停止刷新
Clear         清空显示
```

建议刷新间隔：

```text
单个控制器：0.5s - 1.0s
all 三个控制器：1.0s - 2.0s
```

### 命令行

```bash
cd /home/mars/Desktop/liuyizhou/rokae_joint_reader
/home/mars/miniforge3/envs/lerobot/bin/python read_rokae_joints.py
```

只读某一部分：

```bash
/home/mars/miniforge3/envs/lerobot/bin/python read_rokae_joints.py --target right_arm
/home/mars/miniforge3/envs/lerobot/bin/python read_rokae_joints.py --target left_arm
/home/mars/miniforge3/envs/lerobot/bin/python read_rokae_joints.py --target taihu
```

输出 JSON：

```bash
/home/mars/miniforge3/envs/lerobot/bin/python read_rokae_joints.py --json
```

## 这个工具会不会控制机器人？

不会。它只做：

```text
连接控制器
调用 SDK 的 jointPos()
读取 power/operate/operation 状态
打印角度
```

它不会：

```text
上电
下电
切模式
清报警
启动 realtime/RT 控制
发运动命令
移动机械臂
```

所以即使机器人 `power=off`，只要控制器和编码器状态可读，也可以读到当前角度。

## RT 是什么？

RT 是 real-time control，即实时控制。LeRobot 遥操作或 policy 部署时，`rokae_zmq_server` 会进入实时控制循环，持续向机器人发送目标动作。

这个工具不是 RT 控制。它只是定时读取快照：

```text
读角度工具：看仪表盘
RT 控制：接管方向盘并持续开车
```

## 数据采集建议

做右臂 pick-and-place 数据采集时，建议把右臂以外的构型固定，并记录角度：

```text
TaiHu/机身：固定
左臂：固定到不挡视野、不碰撞的位置
右臂：每个 episode 开始前回标准初始位
盒子：固定
目标物：可以随机摆放
```

推荐 episode 边界：

```text
右臂标准初始位
开始录制
抓取目标物
放入盒子
松开夹爪
停止录制
录制外执行复原
```

不要把“复原回初始位”录进同一个 pick-and-place policy 里。复原更适合用写死脚本或人工流程做 reset。

## 适配到其他 ROKAE 机器人要改哪里

主要改 `read_rokae_joints.py` 里的 `DEFAULT_TARGETS`。

当前配置：

```python
DEFAULT_TARGETS = (
    RobotTarget(
        name="right_arm",
        ip="192.168.71.160",
        sdk_classes=("xMateErProRobot",),
        joint_labels=("J1", "J2", "J3", "J4", "J5", "J6", "J7"),
    ),
    RobotTarget(
        name="left_arm",
        ip="192.168.71.161",
        sdk_classes=("xMateErProRobot",),
        joint_labels=("J1", "J2", "J3", "J4", "J5", "J6", "J7"),
    ),
    RobotTarget(
        name="taihu",
        ip="192.168.71.254",
        sdk_classes=("Robot_T_Industrial_4", "IndustrialRobot_4"),
        joint_labels=("J1", "J2", "J3", "J4"),
    ),
)
```

### 1. 修改 IP

把 `ip=` 改成目标机器人控制器 IP。

例如：

```python
ip="192.168.1.20"
```

### 2. 修改本机 IP

默认本机 IP 在 `parse_args()` 里：

```python
--host-ip 192.168.71.56
```

如果电脑在机器人网段里的 IP 不同，运行时传参：

```bash
/home/mars/miniforge3/envs/lerobot/bin/python read_rokae_joints.py --host-ip 192.168.x.x
```

或者直接改默认值。

### 3. 修改 SDK 类

不同 ROKAE 机型要用不同 SDK 类。常见类名可以在：

```text
/home/mars/cy/lerobot_rokae/rokae_python_wrapper/rokae_sdk/xCoreSDK_python/__init__.pyi
```

里找。

当前常见类型：

```python
xMateErProRobot      # 7 轴协作臂
xMateRobot           # 6 轴协作臂
xMateCr5Robot        # 5 轴协作臂
Robot_T_Industrial_4 # 4 轴工业/机身控制器
IndustrialRobot_4    # 4 轴工业机器人封装
StandardRobot        # 6 轴标准工业机器人
```

如果不确定，可以先把可能的类写成多个，工具会按顺序尝试：

```python
sdk_classes=("Robot_T_Industrial_4", "IndustrialRobot_4")
```

### 4. 修改关节标签

`joint_labels` 只影响显示名称，不影响读取。

例如 6 轴机械臂：

```python
joint_labels=("J1", "J2", "J3", "J4", "J5", "J6")
```

如果 SDK 返回的关节数量比标签多，程序会自动把多出来的命名为 `J5`、`J6` 等。

### 5. 修改 GUI 目标列表

如果新增/删除 target，需要同步修改 `read_rokae_joints_gui.py` 里的下拉框：

```python
values=("all", "right_arm", "left_arm", "taihu")
```

把它改成你的 target 名称即可。

## 常见问题

### power=off 还能读到角度正常吗？

正常。控制器开机且编码器可读时，即使电机下电，`jointPos()` 也可以返回当前角度。

### TaiHu 为什么 Robot Assist 只显示 J1-J4，这里可能显示 J5/J6？

Robot Assist 可能只显示可 Jog 的机身轴；SDK 的 `jointPos()` 返回的是控制器暴露的完整轴状态，可能包含附加轴、虚拟轴或扩展状态。要确认对应关系，可以打开 Live 模式，逐个 Jog TaiHu 的 J1-J4，看哪个读数变化。

### 会影响 LeRobot 采集或部署吗？

低频只读影响很小。但在 LeRobot 遥操作或部署时，建议：

```text
只读需要观察的单个 target
刷新间隔 1s 或 2s
不要 all + 0.5s 高频刷新
```

这样可以减少 SDK 通信占用。

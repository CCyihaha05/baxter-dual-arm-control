# 系统架构

## 控制流

```
UI / 控制逻辑
   │  键盘增量 · 关节滑杆 · 动作序列
   ▼
JointCommand（POSITION_MODE）
   │
   ├── /robot/limb/left/joint_command
   └── /robot/limb/right/joint_command
   │
   ▼
baxter_interface / Baxter SDK
   │
   ├── Gazebo（仿真）
   └── 真机 Baxter（ROS 网络）
```

## 反馈流

| 数据 | 话题 | 用途 |
|---|---|---|
| 全身关节位置 | `/robot/joint_states`（`sensor_msgs/JointState`） | 姿态到达判断、键盘控制基准、`head_pan` 角度 |
| 头部摄像头 | 由 `camera_control.py -o head_camera` 开启 | UI 视频流 |
| 左手摄像头 | `camera_control.py -o left_hand_camera` | UI 视频流 |
| 右手摄像头 | `camera_control.py -o right_hand_camera` | UI 视频流 |

## 关节命名

Baxter 每臂 7 个自由度：

```
s0 → s1 → e0 → e1 → w0 → w1 → w2
肩部旋转  肩部俯仰  肘部旋转  肘部俯仰  腕部旋转  腕部俯仰  腕部翻转
```

```python
JOINTS = {
    "left":  ["left_s0","left_s1","left_e0","left_e1","left_w0","left_w1","left_w2"],
    "right": ["right_s0","right_s1","right_e0","right_e1","right_w0","right_w1","right_w2"],
}
```

头部云台只有一个水平自由度：`head_pan`。

## 预定义姿态

```python
POSES = {
    "home":  {"left": {...全零...}, "right": {...全零...}},          # 垂直下垂
    "open":  {"left": {"left_s0": 0.55, "left_s1": -0.20},
              "right": {"right_s0": -0.55, "right_s1": -0.20}},      # 展开
    "bend":  {"left": {"left_s0": 0.35, "left_s1": -0.35},
              "right": {"right_s0": -0.35, "right_s1": -0.35}},      # 内收弯曲
    "cross": {"left": {"left_s0": 0.15, "left_s1": -0.45},
              "right": {"right_s0": -0.15, "right_s1": -0.45}},      # 最大内收交叉
}
```

`open` / `bend` / `cross` 只指定前两个关节，其余关节复用当前角度。

## 动作序列

```python
DEMOS = {
    "dual_move":  ["home", "open", "bend", "home"],
    "dual_collab": ["home", "open", "cross", "bend", "home"],
}
```

每个姿态之间按顺序执行，双臂同步下发指令。

## 控制频率

| 环节 | 频率 |
|---|---|
| 位置指令下发 | 20 Hz（`command_rate` 默认值） |
| 控制流预热 | 60 Hz × 200 ms |
| 姿态到达轮询 | 20 Hz |

## 仿真 / 真机的差异处理

| 维度 | 仿真 | 真机 |
|---|---|---|
| 环境配置 | `./baxter.sh sim` | `source ./baxter.sh`（不加 sim） |
| ROS Master | Gazebo 启动的 Master | 机器人自带的 Master |
| 到达误差阈值 | `tolerance` | `max(tolerance × 1.8, 0.18)` |
| 夹爪 | 不可用 | `baxter_interface.Gripper` |
| 控制流预热 | 不需要 | 200 ms @ 60 Hz |
| 响应延迟 | 低 | 较高（通信 + 机械间隙） |

> 真机的误差阈值更宽松，是因为机械间隙与通信延迟会让“仿真里能收敛”的姿态在真机上反复超时。

## 安全设计

- **缺失关节容错**：目标里没有的关节复用当前角度，避免被重置为 0
- **超时保护**：`move_to_pose` 带 `deadline`，超时返回 `False` 而不是死循环
- **夹爪阻塞控制**：`block=False` + 固定延时，避免阻塞控制循环

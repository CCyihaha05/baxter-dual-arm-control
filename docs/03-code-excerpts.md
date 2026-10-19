# 核心模块代码节选

> ⚠️ 以下代码来自课程报告，保留了核心逻辑，**省略了 import、日志、部分初始化与 UI 代码**。完整工程未随仓库发布。

---

## 模块一 · 左右臂关节定义与指令下发

**作用**：定义双臂关节名称、预定义姿态，提供位置指令发布与读取。

```python
JOINTS = {
    "left":  ["left_s0","left_s1","left_e0","left_e1","left_w0","left_w1","left_w2"],
    "right": ["right_s0","right_s1","right_e0","right_e1","right_w0","right_w1","right_w2"],
}

POSES = {
    "home":  {"left": {j: 0.0 for j in JOINTS["left"]},
              "right": {j: 0.0 for j in JOINTS["right"]}},
    "open":  {"left":  {"left_s0": 0.55,  "left_s1": -0.20},
              "right": {"right_s0": -0.55, "right_s1": -0.20}},
    "bend":  {"left":  {"left_s0": 0.35,  "left_s1": -0.35},
              "right": {"right_s0": -0.35, "right_s1": -0.35}},
    "cross": {"left":  {"left_s0": 0.15,  "left_s1": -0.45},
              "right": {"right_s0": -0.15, "right_s1": -0.45}},
}

class BaxterJointCommander:
    def __init__(self, real_robot=False, command_rate=20.0):
        self._left_pub  = rospy.Publisher("/robot/limb/left/joint_command",
                                          JointCommand, queue_size=1)
        self._right_pub = rospy.Publisher("/robot/limb/right/joint_command",
                                          JointCommand, queue_size=1)
        self._joint_positions = {}

    def joint_positions(self, side):
        return {name: self._joint_positions.get(name, 0.0)
                for name in JOINTS[side]}

    def send_position_command(self, side, targets):
        msg = JointCommand()
        msg.mode = JointCommand.POSITION_MODE
        msg.names = JOINTS[side]
        msg.command = [targets.get(name, self._joint_positions.get(name, 0.0))
                       for name in JOINTS[side]]
        publisher = self._left_pub if side == "left" else self._right_pub
        publisher.publish(msg)
```

**设计要点**

- `msg.command` 对缺失的关节**复用当前角度**，而不是填 0——避免一次姿态切换把未指定的关节全部拉回零位
- `queue_size=1`：控制指令只关心最新值，积压旧指令会导致动作滞后

---

## 模块二 · 头部状态读取

**作用**：订阅全局关节状态，封装 `head_pan` 角度读取。

```python
class BaxterJointCommander:
    def __init__(self):
        self._joint_sub = rospy.Subscriber(
            "/robot/joint_states", JointState, self._on_joint_states, queue_size=1
        )
        self._joint_positions = {}

    def _on_joint_states(self, msg):
        for index, name in enumerate(msg.name):
            self._joint_positions[name] = msg.position[index]

    def head_position(self):
        return float(self._joint_positions.get("head_pan", 0.0))
```

**设计要点**

- 回调里只做字典赋值，不做计算——`/robot/joint_states` 频率较高，回调过重会丢帧
- 无数据时返回 `0.0` 做容错

---

## 模块三 · 双臂协同控制

**作用**：双臂同步移动到预定义姿态，支持连续动作序列，仿真/真机自适应误差。

```python
DEMOS = {
    "dual_move":   ["home", "open", "bend", "home"],
    "dual_collab": ["home", "open", "cross", "bend", "home"],
}

class BaxterJointCommander:
    def move_to_pose(self, pose_name, tolerance, timeout):
        pose = POSES[pose_name]
        deadline = time.time() + timeout
        while not rospy.is_shutdown() and time.time() < deadline:
            self.send_position_command("left",  pose["left"])
            self.send_position_command("right", pose["right"])
            if (self._pose_reached("left",  pose["left"],  tolerance) and
                self._pose_reached("right", pose["right"], tolerance)):
                return True
            rospy.Rate(self._command_rate).sleep()
        return False

    def _pose_reached(self, side, targets, tolerance):
        errors, max_error, avg_error = self._target_errors(side, targets)
        relaxed_max = max(tolerance * 1.8, 0.18)
        return max_error <= relaxed_max
```

**设计要点**

- **循环内持续下发**：不是发一次就等，而是在整个运动过程中以 20 Hz 重发目标，对抗通信丢包
- **超时保护**：`deadline` 保证不会死循环
- **真机放宽阈值**：`max(tolerance × 1.8, 0.18)`——机械间隙与通信延迟会让仿真里能收敛的姿态在真机上超时

---

## 模块四 · 键盘控制底层支撑

**作用**：高频读取双臂全部关节位置作为增量基准，无锁快速下发。

```python
class BaxterJointCommander:
    def __init__(self, real_robot=False, command_rate=20.0):
        self._command_rate = command_rate
        self._joint_sub = rospy.Subscriber(
            "/robot/joint_states", JointState, self._on_joint_states, queue_size=1
        )

    def joint_positions_all(self):
        data = {}
        for side in ("left", "right"):
            data.update(self.joint_positions(side))
        return data

    def send_position_command(self, side, targets):
        msg = JointCommand()
        msg.mode = JointCommand.POSITION_MODE
        msg.names = JOINTS[side]
        msg.command = [targets.get(name, self._joint_positions.get(name, 0.0))
                       for name in JOINTS[side]]
        publisher = self._left_pub if side == "left" else self._right_pub
        publisher.publish(msg)

    def prime_control_stream(self, duration=0.20):
        left_targets  = self.joint_positions("left")
        right_targets = self.joint_positions("right")
        deadline = time.time() + duration
        while not rospy.is_shutdown() and time.time() < deadline:
            self.send_position_command("left",  left_targets)
            self.send_position_command("right", right_targets)
            rospy.Rate(60).sleep()
```

**设计要点**

- **无锁设计**：键盘控制要求低延迟，避免在控制路径上加锁
- **控制流预热**：真机首次下发前，以 60 Hz 连续发送 200 ms 当前位置，填充控制流缓冲，显著改善键盘操作的流畅度

---

## 模块五 · 夹爪控制

**作用**：左右独立/同步开合，仅真机可用。

```python
GRIPPER_ACTIONS = {
    "open":        ("left", "right"),
    "close":       ("left", "right"),
    "left_open":   ("left",),
    "right_close": ("right",),
}
REAL_POSITION_SPEED = 0.75

class BaxterJointCommander:
    def __init__(self, real_robot=False):
        self._real_robot = real_robot
        self._grippers = {}

    def _ensure_grippers(self):
        for side in ("left", "right"):
            self._grippers[side] = baxter_interface.Gripper(side)

    def move_gripper(self, action_name):
        if not self._real_robot:
            raise RuntimeError("Gripper only for real robot")
        self._ensure_grippers()
        command = "open" if "open" in action_name else "close"
        for side in GRIPPER_ACTIONS[action_name]:
            getattr(self._grippers[side], command)(block=False, timeout=2.0)
        rospy.sleep(1.0)
```

**设计要点**

- **仅真机**：Gazebo 仿真中的夹爪接口行为不一致，因此显式限制
- **非阻塞**：`block=False` 避免夹爪动作阻塞控制循环，随后 `rospy.sleep(1.0)` 保证机械到位
- **延迟初始化**：夹爪接口在第一次使用时才创建，避免无夹爪环境下的构造失败

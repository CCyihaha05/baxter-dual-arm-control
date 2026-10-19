"""
左右臂关节定义与位置指令下发

EXCERPT — 来自课程报告，保留了核心逻辑。
import、日志、初始化与 UI 代码已省略，本文件不是可直接运行的完整模块。
"""

JOINTS = {
    "left":  ["left_s0", "left_s1", "left_e0", "left_e1", "left_w0", "left_w1", "left_w2"],
    "right": ["right_s0", "right_s1", "right_e0", "right_e1", "right_w0", "right_w1", "right_w2"],
}

POSES = {
    "home": {
        "left":  {"left_s0": 0.0, "left_s1": 0.0, "left_e0": 0.0, "left_e1": 0.0,
                  "left_w0": 0.0, "left_w1": 0.0, "left_w2": 0.0},
        "right": {"right_s0": 0.0, "right_s1": 0.0, "right_e0": 0.0, "right_e1": 0.0,
                  "right_w0": 0.0, "right_w1": 0.0, "right_w2": 0.0},
    },
    "open": {
        "left":  {"left_s0": 0.55,  "left_s1": -0.20},
        "right": {"right_s0": -0.55, "right_s1": -0.20},
    },
    "bend": {
        "left":  {"left_s0": 0.35,  "left_s1": -0.35},
        "right": {"right_s0": -0.35, "right_s1": -0.35},
    },
    "cross": {
        "left":  {"left_s0": 0.15,  "left_s1": -0.45},
        "right": {"right_s0": -0.15, "right_s1": -0.45},
    },
}


class BaxterJointCommander:
    def __init__(self, real_robot=False, command_rate=20.0):
        self._left_pub = rospy.Publisher(
            "/robot/limb/left/joint_command", JointCommand, queue_size=1
        )
        self._right_pub = rospy.Publisher(
            "/robot/limb/right/joint_command", JointCommand, queue_size=1
        )
        self._joint_positions = {}

    def joint_positions(self, side):
        return {name: self._joint_positions.get(name, 0.0) for name in JOINTS[side]}

    def send_position_command(self, side, targets):
        msg = JointCommand()
        msg.mode = JointCommand.POSITION_MODE
        msg.names = JOINTS[side]
        # 缺失的关节复用当前角度，避免被重置到 0
        msg.command = [
            targets.get(name, self._joint_positions.get(name, 0.0))
            for name in JOINTS[side]
        ]
        publisher = self._left_pub if side == "left" else self._right_pub
        publisher.publish(msg)

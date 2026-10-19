"""
夹爪控制：左右独立 / 双臂同步开合

EXCERPT — 来自课程报告，保留了核心逻辑。
import、日志与 UI 代码已省略。仅支持真机。

注意：在 Gazebo 仿真中 baxter_interface.Gripper 的行为不一致，
因此这里显式限制为 real_robot=True 时可用。
"""

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
        """延迟初始化夹爪硬件接口。"""
        for side in ("left", "right"):
            self._grippers[side] = baxter_interface.Gripper(side)

    def move_gripper(self, action_name):
        """执行夹爪开合动作。

        block=False 避免阻塞控制循环；随后的固定延时保证机械到位。
        """
        if not self._real_robot:
            raise RuntimeError("Gripper only for real robot")

        self._ensure_grippers()
        command = "open" if "open" in action_name else "close"

        for side in GRIPPER_ACTIONS[action_name]:
            getattr(self._grippers[side], command)(block=False, timeout=2.0)

        rospy.sleep(1.0)

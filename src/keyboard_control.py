"""
键盘控制的底层支撑

EXCERPT — 来自课程报告，保留了核心逻辑。
import、日志、键盘事件处理与 UI 代码已省略。
"""


class BaxterJointCommander:
    def __init__(self, real_robot=False, command_rate=20.0):
        self._command_rate = command_rate
        self._joint_sub = rospy.Subscriber(
            "/robot/joint_states", JointState, self._on_joint_states, queue_size=1
        )

    def joint_positions_all(self):
        """获取双臂所有关节实时位置，作为键盘增量调节的基准。"""
        data = {}
        for side in ("left", "right"):
            data.update(self.joint_positions(side))
        return data

    def send_position_command(self, side, targets):
        """高频无锁关节指令下发。

        键盘控制要求低延迟，因此控制路径上不加锁。
        """
        msg = JointCommand()
        msg.mode = JointCommand.POSITION_MODE
        msg.names = JOINTS[side]
        msg.command = [
            targets.get(name, self._joint_positions.get(name, 0.0))
            for name in JOINTS[side]
        ]
        publisher = self._left_pub if side == "left" else self._right_pub
        publisher.publish(msg)

    def prime_control_stream(self, duration=0.20):
        """真机控制流预热。

        首次下发前以 60 Hz 连续发送当前位置 200 ms，
        填充控制流缓冲，改善键盘操作的流畅度。
        """
        left_targets = self.joint_positions("left")
        right_targets = self.joint_positions("right")
        deadline = time.time() + duration
        while not rospy.is_shutdown() and time.time() < deadline:
            self.send_position_command("left", left_targets)
            self.send_position_command("right", right_targets)
            rospy.Rate(60).sleep()

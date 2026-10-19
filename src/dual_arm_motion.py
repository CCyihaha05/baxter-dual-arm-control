"""
双臂协同控制：预定义姿态与连续动作序列

EXCERPT — 来自课程报告，保留了核心逻辑。
POSES 的完整数值见 joint_commander.py；import、日志、UI 代码已省略。
"""

# 双臂同步预定义姿态（完整定义见 joint_commander.py）
POSES = {
    "home":  {"left": {...}, "right": {...}},
    "open":  {"left": {...}, "right": {...}},
    "bend":  {"left": {...}, "right": {...}},
    "cross": {"left": {...}, "right": {...}},
}

DEMOS = {
    "dual_move":   ["home", "open", "bend", "home"],
    "dual_collab": ["home", "open", "cross", "bend", "home"],
}


class BaxterJointCommander:
    def move_to_pose(self, pose_name, tolerance, timeout):
        """双臂同步移动到预定义姿态。

        在整个运动过程中以 command_rate 持续重发目标，
        而不是发一次就等待——对抗通信丢包。
        """
        pose = POSES[pose_name]
        deadline = time.time() + timeout
        while not rospy.is_shutdown() and time.time() < deadline:
            self.send_position_command("left", pose["left"])
            self.send_position_command("right", pose["right"])
            if (self._pose_reached("left", pose["left"], tolerance) and
                    self._pose_reached("right", pose["right"], tolerance)):
                return True
            rospy.Rate(self._command_rate).sleep()
        return False

    def _pose_reached(self, side, targets, tolerance):
        """姿态到达判断（仿真 / 真机自适应）。

        真机需要更宽松的阈值：机械间隙、通信延迟、编码器噪声
        会让仿真里能收敛的姿态在真机上反复超时。
        """
        errors, max_error, avg_error = self._target_errors(side, targets)
        relaxed_max = max(tolerance * 1.8, 0.18)
        return max_error <= relaxed_max

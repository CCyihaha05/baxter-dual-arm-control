"""
头部云台状态读取

EXCERPT — 来自课程报告，保留了核心逻辑。
import、日志、初始化与 UI 代码已省略，本文件不是可直接运行的完整模块。
"""


class BaxterJointCommander:
    def __init__(self):
        # 订阅机器人全局关节状态（包含头部）
        self._joint_sub = rospy.Subscriber(
            "/robot/joint_states", JointState, self._on_joint_states, queue_size=1
        )
        self._joint_positions = {}

    def _on_joint_states(self, msg):
        # 回调里只做字典赋值，保持轻量
        for index, name in enumerate(msg.name):
            self._joint_positions[name] = msg.position[index]

    def head_position(self):
        # 无数据时返回 0.0 做容错
        return float(self._joint_positions.get("head_pan", 0.0))

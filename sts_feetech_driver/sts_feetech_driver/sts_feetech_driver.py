#!/usr/bin/env python3
"""
ROS 2 драйвер для сервоприводов STS Feetech.
Совместим с MoveIt 2: предоставляет action-сервер FollowJointTrajectory
и непрерывно публикует sensor_msgs/JointState.
"""

import math
import asyncio
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from control_msgs.action import FollowJointTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint

from scservo_sdk import PortHandler, sms_sts, GroupSyncWrite


class STSFeetechDriver(Node):
    def __init__(self):
        super().__init__('sts_feetech_driver')

        # --- параметры порта ---
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 1000000)

        port_name = self.get_parameter('port').value
        baudrate = self.get_parameter('baudrate').value

        # --- параметры суставов ---
        self.declare_parameter('joint_names', ['joint_1'])
        self.joint_names = self.get_parameter('joint_names').value

        self.joint_config = {}  # имя -> {id, raw_min, raw_max, angle_min, angle_max}
        for jname in self.joint_names:
            self.declare_parameter(f'joint_{jname}.id', 1)
            self.declare_parameter(f'joint_{jname}.angle_min', -math.pi)
            self.declare_parameter(f'joint_{jname}.angle_max', math.pi)
            self.declare_parameter(f'joint_{jname}.raw_min', 0)
            self.declare_parameter(f'joint_{jname}.raw_max', 4095)

            sid = self.get_parameter(f'joint_{jname}.id').value
            self.joint_config[jname] = {
                'id': sid,
                'raw_min': self.get_parameter(f'joint_{jname}.raw_min').value,
                'raw_max': self.get_parameter(f'joint_{jname}.raw_max').value,
                'angle_min': self.get_parameter(f'joint_{jname}.angle_min').value,
                'angle_max': self.get_parameter(f'joint_{jname}.angle_max').value,
            }

        # --- инициализация железа ---
        self.port_handler = PortHandler(port_name)
        if not self.port_handler.openPort():
            self.get_logger().error('Не удалось открыть порт')
            raise RuntimeError('Port open failed')
        if not self.port_handler.setBaudRate(baudrate):
            self.get_logger().error('Не удалось установить скорость порта')
            raise RuntimeError('Set baudrate failed')

        # Основной объект для работы с протоколом STS (endian = 0)
        self.protocol = sms_sts(self.port_handler)

        # Включение крутящего момента на всех сервоприводах (широковещательно)
        comm_result = self.protocol.write1ByteTxRx(254, sms_sts.SMS_STS_TORQUE_ENABLE, 1)
        if comm_result != sms_sts.COMM_SUCCESS:
            self.get_logger().error(f'Ошибка включения момента: {self.protocol.getTxRxResult(comm_result)}')
        else:
            self.get_logger().info('Крутящий момент включён на всех сервоприводах')

        # Групповая синхронная запись позиций (2 байта)
        self.sync_write = GroupSyncWrite(
            self.port_handler, self.protocol, sms_sts.SMS_STS_GOAL_POSITION_L, 2
        )

        # --- ROS-интерфейс ---
        self.joint_state_pub = self.create_publisher(JointState, 'joint_states', 10)
        self.timer = self.create_timer(0.02, self.publish_joint_states)  # 50 Гц

        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            'follow_joint_trajectory',
            execute_callback=self.execute_trajectory,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=ReentrantCallbackGroup()
        )

        self.get_logger().info('Драйвер STS Feetech успешно запущен')

    # ------------------------------------------------------------------
    # Конвертация углов
    # ------------------------------------------------------------------
    def angle_to_raw(self, joint_name, angle_rad):
        cfg = self.joint_config[joint_name]
        raw = cfg['raw_min'] + (angle_rad - cfg['angle_min']) * \
              (cfg['raw_max'] - cfg['raw_min']) / (cfg['angle_max'] - cfg['angle_min'])
        return int(max(cfg['raw_min'], min(cfg['raw_max'], raw)))

    def raw_to_angle(self, joint_name, raw):
        cfg = self.joint_config[joint_name]
        angle = cfg['angle_min'] + (raw - cfg['raw_min']) * \
                (cfg['angle_max'] - cfg['angle_min']) / (cfg['raw_max'] - cfg['raw_min'])
        return angle

    # ------------------------------------------------------------------
    # Публикация состояния суставов
    # ------------------------------------------------------------------
    def publish_joint_states(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = []
        msg.position = []
        msg.velocity = []
        msg.effort = []

        for jname in self.joint_names:
            cfg = self.joint_config[jname]
            sid = cfg['id']
            try:
                pos_raw, result, error = self.protocol.ReadPos(sid)
                if result == sms_sts.COMM_SUCCESS:
                    angle = self.raw_to_angle(jname, pos_raw)
                    msg.name.append(jname)
                    msg.position.append(angle)
                    msg.velocity.append(float('nan'))
                    msg.effort.append(float('nan'))
                else:
                    self.get_logger().warn(
                        f'Ошибка чтения {jname} (ID {sid}): {self.protocol.getTxRxResult(result)}'
                    )
            except Exception as e:
                self.get_logger().error(f'Исключение при чтении {jname}: {e}')

        if msg.name:
            self.joint_state_pub.publish(msg)

    # ------------------------------------------------------------------
    # Обработчики action-сервера
    # ------------------------------------------------------------------
    def goal_callback(self, goal_request):
        self.get_logger().info('Получена цель траектории')
        for name in goal_request.trajectory.joint_names:
            if name not in self.joint_names:
                self.get_logger().error(f'Неизвестный сустав: {name}')
                return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Запрос отмены траектории')
        return CancelResponse.ACCEPT

    async def execute_trajectory(self, goal_handle):
        trajectory = goal_handle.request.trajectory
        joint_names = trajectory.joint_names

        for n in joint_names:
            if n not in self.joint_config:
                goal_handle.abort()
                return FollowJointTrajectory.Result(
                    error_code=FollowJointTrajectory.Result.INVALID_JOINTS,
                    error_string=f'Неизвестный сустав: {n}'
                )

        self.get_logger().info(f'Выполнение траектории из {len(trajectory.points)} точек')
        start_time = self.get_clock().now()

        for i, point in enumerate(trajectory.points):
            if goal_handle.is_cancel_requested:
                self.get_logger().info('Траектория отменена')
                goal_handle.canceled()
                # Выключаем момент на всех сервах
                self.protocol.write1ByteTxRx(254, sms_sts.SMS_STS_TORQUE_ENABLE, 0)
                return FollowJointTrajectory.Result(error_code=FollowJointTrajectory.Result.SUCCESSFUL)

            # Время, когда должна быть достигнута эта точка
            time_from_start = point.time_from_start
            target_time = start_time + rclpy.duration.Duration(
                seconds=time_from_start.sec,
                nanoseconds=time_from_start.nanosec
            )

            sleep_duration = target_time - self.get_clock().now()
            if sleep_duration.nanoseconds > 0:
                await asyncio.sleep(sleep_duration.nanoseconds * 1e-9)

            # Отправка целевых позиций
            raw_targets = {}
            for jname, angle in zip(joint_names, point.positions):
                raw = self.angle_to_raw(jname, angle)
                sid = self.joint_config[jname]['id']
                raw_targets[sid] = raw

            self.write_raw_positions(raw_targets)

            # Публикация обратной связи
            feedback = FollowJointTrajectory.Feedback()
            feedback.header.stamp = self.get_clock().now().to_msg()
            feedback.joint_names = joint_names
            feedback.actual.positions = point.positions
            feedback.actual.velocities = point.velocities if point.velocities else [0.0] * len(joint_names)
            feedback.desired = feedback.actual
            goal_handle.publish_feedback(feedback)

        goal_handle.succeed()
        self.get_logger().info('Траектория завершена успешно')
        return FollowJointTrajectory.Result(error_code=FollowJointTrajectory.Result.SUCCESSFUL)

    # ------------------------------------------------------------------
    # Синхронная запись позиций
    # ------------------------------------------------------------------
    def write_raw_positions(self, id_raw_dict: dict):
        self.sync_write.clearParam()
        for sid, raw in id_raw_dict.items():
            param = [sms_sts.SMS_STS_LOBYTE(raw), sms_sts.SMS_STS_HIBYTE(raw)]
            self.sync_write.addParam(sid, param)
        result = self.sync_write.txPacket()
        if result != sms_sts.COMM_SUCCESS:
            self.get_logger().error(f'Ошибка синхронной записи: {self.protocol.getTxRxResult(result)}')

    # ------------------------------------------------------------------
    # Завершение работы
    # ------------------------------------------------------------------
    def shutdown(self):
        self.get_logger().info('Выключение драйвера...')
        self.protocol.write1ByteTxRx(254, sms_sts.SMS_STS_TORQUE_ENABLE, 0)
        self.port_handler.closePort()
        self.get_logger().info('Порт закрыт')


def main(args=None):
    rclpy.init(args=args)
    driver = STSFeetechDriver()

    executor = MultiThreadedExecutor()
    executor.add_node(driver)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        driver.shutdown()
        executor.shutdown()
        driver.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
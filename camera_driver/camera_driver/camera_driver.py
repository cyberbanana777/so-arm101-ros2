#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, CameraInfo
import cv2
import numpy as np

class JpegPublisher(Node):
    def __init__(self):
        super().__init__('jpeg_publisher')

        # --- Объявление параметров ---
        self.declare_parameter('fps', 10.0)                      # частота кадров
        self.declare_parameter('enable_logging', True)           # включать/отключать информационные логи
        self.declare_parameter('camera_image_topic', 'camera/image/compressed')
        self.declare_parameter('camera_info_topic', 'camera/camera_info')
        
        # Чтение параметров
        fps = self.get_parameter('fps').get_parameter_value().double_value
        self.enable_logging = self.get_parameter('enable_logging').get_parameter_value().bool_value
        self.camera_image_topic = self.get_parameter('camera_image_topic').get_parameter_value().string_value
        self.camera_info_topic = self.get_parameter('camera_info_topic').get_parameter_value().string_value

        # Период таймера (секунды)
        timer_period = 1.0 / fps if fps > 0 else 0.1
        self.get_logger().info(f'Настройки: FPS={fps}, период={timer_period:.3f} с, логирование={self.enable_logging}')

        # Публикаторы
        self.image_publisher = self.create_publisher(CompressedImage, self.camera_image_topic, 10)
        self.camera_info_publisher = self.create_publisher(CameraInfo, self.camera_info_topic, 10)

        # Таймер
        self.timer = self.create_timer(timer_period, self.timer_callback)

        # Открываем камеру
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error('Не удалось открыть камеру')
            rclpy.shutdown()

        # Получаем реальное разрешение, которое установила камера
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.get_logger().info(f'Разрешение камеры: {self.width} x {self.height}')

        # Создаём сообщение CameraInfo (один раз, будем обновлять только штамп времени)
        self.camera_info_msg = self.create_camera_info_msg()

        self.get_logger().info('Узел JPEG publisher запущен')

    def create_camera_info_msg(self):
        """
        Создаёт и возвращает сообщение CameraInfo с приблизительными параметрами.
        При наличии файла калибровки можно загрузить реальные данные.
        """
        msg = CameraInfo()
        msg.header.frame_id = 'camera_frame'  # должно совпадать с frame_id изображения
        msg.width = self.width
        msg.height = self.height

        # Модель искажений: plumb_bob (radial-tangential) - наиболее распространённая
        msg.distortion_model = 'plumb_bob'

        # Коэффициенты искажений (D) - пока все нули (нет искажений)
        msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]

        # Матрица камеры (K) - приблизительная:
        # fx, fy - фокусные расстояния в пикселях (можно оценить как width * 0.8..1.2)
        # cx, cy - оптический центр (обычно центр изображения: width/2, height/2)
        fx = self.width * 0.9  # примерная оценка
        fy = self.width * 0.9
        cx = self.width / 2.0
        cy = self.height / 2.0
        msg.k = [fx, 0.0, cx,
                 0.0, fy, cy,
                 0.0, 0.0, 1.0]

        # Матрица исправления (R) - единичная (нет поворота)
        msg.r = [1.0, 0.0, 0.0,
                 0.0, 1.0, 0.0,
                 0.0, 0.0, 1.0]

        # Матрица проекции (P) - для монокуляра обычно совпадает с K, дополненная нулями
        msg.p = [fx, 0.0, cx, 0.0,
                 0.0, fy, cy, 0.0,
                 0.0, 0.0, 1.0, 0.0]

        # Если вы хотите использовать бинирование (если изображение уменьшалось), укажите
        msg.binning_x = 0
        msg.binning_y = 0

        # Область интереса (если не используется, пустая)
        msg.roi.do_rectify = False
        msg.roi.x_offset = 0
        msg.roi.y_offset = 0
        msg.roi.height = 0
        msg.roi.width = 0

        return msg

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn('Не удалось захватить кадр')
            return

        # --- Публикация изображения ---
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        result, encimg = cv2.imencode('.jpg', frame, encode_param)
        if not result:
            self.get_logger().error('Ошибка сжатия JPEG')
            return

        img_msg = CompressedImage()
        img_msg.header.stamp = self.get_clock().now().to_msg()
        img_msg.header.frame_id = 'camera_frame'
        img_msg.format = 'jpeg'
        img_msg.data = np.array(encimg).tobytes()

        self.image_publisher.publish(img_msg)

        # --- Публикация CameraInfo ---
        # Обновляем штамп времени (должен совпадать со штампом изображения)
        self.camera_info_msg.header.stamp = img_msg.header.stamp
        self.camera_info_publisher.publish(self.camera_info_msg)

        # Логирование, если включено
        if self.enable_logging:
            self.get_logger().info('Опубликован JPEG кадр и CameraInfo', throttle_duration_sec=2)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = JpegPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
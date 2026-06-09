# sts_feetech_driver.launch.py (упрощённый)
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    config_path = os.path.join(
        get_package_share_directory('sts_feetech_driver'),
        'config',
        'sts_feetech_driver_params.yaml'
    )

    return LaunchDescription([
        Node(
            package='sts_feetech_driver',
            executable='sts_feetech_driver',
            name='sts_feetech_driver',
            output='screen',
            parameters=[config_path],
        )
    ])
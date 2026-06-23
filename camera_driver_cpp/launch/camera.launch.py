import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config_file_path = os.path.join(
        get_package_share_directory('camera_driver_cpp'),
        'config',
        'camera_params.yaml'
    )

    camera_driver_node = Node(
        package='camera_driver_cpp',
        executable='camera_driver_node',
        name='jpeg_publisher',
        parameters=[config_file_path],
        output='screen',
    )

    return LaunchDescription([
        camera_driver_node,
    ])

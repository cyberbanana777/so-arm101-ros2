## hsv_filter_cpp/launch/filter.launch.py
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config_file_path = os.path.join(
        get_package_share_directory('hsv_filter_cpp'),
        'config',
        'params.yaml'
    )

    hsv_filter_node = Node(
        package='hsv_filter_cpp',
        executable='hsv_filter_node',
        name='hsv_filter_node',
        parameters=[config_file_path],
        output='screen',
    )

    return LaunchDescription([
        hsv_filter_node,
    ])

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    return LaunchDescription([

        Node(
            package='camera_driver',
            executable='camera_driver',
            name='camera_driver',  # должно совпадать с именем в YAML
            output='screen',
            parameters=[
                # Загружаем параметры из YAML-файла внутри пакета
                PathJoinSubstitution([
                    FindPackageShare('camera_driver'),
                    'config', 'debug_params.yaml'
                ]),
            ]
        )
    ])
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Объяви аргументы
    declare_use_fake_hardware = DeclareLaunchArgument(
        'use_fake_hardware',
        default_value='false',
        description='Use fake hardware instead of real motors'
    )
    
    declare_port = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyACM0',
        description='Serial port for motors'
    )
    
    # Сгенерируй URDF из xacro - ПРАВИЛЬНЫЙ СПОСОБ
    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        PathJoinSubstitution([
            FindPackageShare('so101_moveit'),
            'config',
            'so101_new_calib.urdf.xacro'
        ]),
        ' use_fake_hardware:=',
        LaunchConfiguration('use_fake_hardware'),
        ' port:=',
        LaunchConfiguration('port')
    ])
    
    robot_description = {'robot_description': ParameterValue(robot_description_content, value_type=str)}
    
    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )
    
    # ros2_control_node
    ros2_control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            robot_description,
            PathJoinSubstitution([
                FindPackageShare('so101_moveit'),
                'config',
                'ros2_controllers.yaml'
            ])
        ],
        output='screen'
    )
    
    # Joint State Broadcaster
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Arm Controller
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Gripper Controller
    gripper_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Запускаем контроллеры последовательно
    delayed_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=ros2_control_node,
            on_exit=[joint_state_broadcaster_spawner]
        )
    )
    
    delayed_arm_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner]
        )
    )
    
    delayed_gripper_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=arm_controller_spawner,
            on_exit=[gripper_controller_spawner]
        )
    )
    
    return LaunchDescription([
        declare_use_fake_hardware,
        declare_port,
        robot_state_publisher,
        ros2_control_node,
        delayed_joint_state_broadcaster,
        delayed_arm_controller,
        delayed_gripper_controller,
    ])
cmake_minimum_required(VERSION 3.8)
project(camera_driver_cpp)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Поиск зависимостей
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(OpenCV REQUIRED)

# Создание исполняемого файла
add_executable(camera_driver_node src/camera_driver_node.cpp)

target_include_directories(camera_driver_node PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# Линковка с библиотеками
ament_target_dependencies(camera_driver_node
  rclcpp
  sensor_msgs
  OpenCV
)
target_link_libraries(camera_driver_node ${OpenCV_LIBS})

# Установка ноды
install(TARGETS camera_driver_node
  DESTINATION lib/${PROJECT_NAME}
)

# Установка launch и config
install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
cmake_minimum_required(VERSION 3.8)
project(hsv_filter_cpp)

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
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)
find_package(OpenCV REQUIRED)

# Создание исполняемого файла
add_executable(hsv_filter_node src/hsv_filter_node.cpp)

target_include_directories(hsv_filter_node PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# Линковка с библиотеками ROS2 и OpenCV
ament_target_dependencies(hsv_filter_node
  rclcpp
  sensor_msgs
  cv_bridge
  image_transport
  OpenCV
)
target_link_libraries(hsv_filter_node ${OpenCV_LIBS})

# Указываем, куда установить скомпилированную ноду
install(TARGETS hsv_filter_node
  DESTINATION lib/${PROJECT_NAME}
)

# Установка launch-файлов и конфигураций
install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
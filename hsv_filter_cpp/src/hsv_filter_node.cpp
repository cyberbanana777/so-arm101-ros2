#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/compressed_image.hpp>
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>
#include <rcl_interfaces/msg/parameter_descriptor.hpp>

class HsvFilterNode : public rclcpp::Node
{
public:
    HsvFilterNode() : Node("hsv_filter_node")
    {
        // --- НАСТРОЙКА ПАРАМЕТРОВ С ДИАПАЗОНАМИ ---
        
        // Дескриптор для H (0-179 в OpenCV)
        rcl_interfaces::msg::ParameterDescriptor h_descriptor;
        h_descriptor.description = "Hue range (0-179 in OpenCV)";
        rcl_interfaces::msg::IntegerRange h_range;
        h_range.from_value = 0;
        h_range.to_value = 179;
        h_range.step = 1;
        h_descriptor.integer_range.push_back(h_range);

        // Дескриптор для S и V (0-255)
        rcl_interfaces::msg::ParameterDescriptor sv_descriptor;
        sv_descriptor.description = "Saturation/Value range (0-255)";
        rcl_interfaces::msg::IntegerRange sv_range;
        sv_range.from_value = 0;
        sv_range.to_value = 255;
        sv_range.step = 1;
        sv_descriptor.integer_range.push_back(sv_range);

        // Объявляем параметры с диапазонами
        this->declare_parameter("h_min", 0, h_descriptor);
        this->declare_parameter("s_min", 100, sv_descriptor);
        this->declare_parameter("v_min", 100, sv_descriptor);
        this->declare_parameter("h_max", 10, h_descriptor);
        this->declare_parameter("s_max", 255, sv_descriptor);
        this->declare_parameter("v_max", 255, sv_descriptor);

        // --- ПОДПИСКА И ПУБЛИКАЦИЯ ---
        subscription_ = this->create_subscription<sensor_msgs::msg::CompressedImage>(
            "camera/image/compressed", 10,
            std::bind(&HsvFilterNode::image_callback, this, std::placeholders::_1));

        publisher_ = this->create_publisher<sensor_msgs::msg::CompressedImage>("camera/filtered_image/compressed", 10);

        RCLCPP_INFO(this->get_logger(), "HSV Filter Node has been started.");
    }

private:
    rclcpp::Subscription<sensor_msgs::msg::CompressedImage>::SharedPtr subscription_;
    rclcpp::Publisher<sensor_msgs::msg::CompressedImage>::SharedPtr publisher_;

    void image_callback(const sensor_msgs::msg::CompressedImage::SharedPtr msg)
    {
        // 1. Получаем параметры из ROS2
        int h_min = this->get_parameter("h_min").as_int();
        int s_min = this->get_parameter("s_min").as_int();
        int v_min = this->get_parameter("v_min").as_int();
        int h_max = this->get_parameter("h_max").as_int();
        int s_max = this->get_parameter("s_max").as_int();
        int v_max = this->get_parameter("v_max").as_int();

        // 2. Конвертируем ROS CompressedImage в OpenCV Mat
        cv::Mat cv_image;
        try {
            cv_image = cv::imdecode(cv::Mat(msg->data), cv::IMREAD_COLOR);
        } catch (cv::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
            return;
        }

        if (cv_image.empty()) {
            RCLCPP_WARN(this->get_logger(), "Received empty image");
            return;
        }

        // 3. OpenCV магия (HSV фильтр)
        cv::Mat hsv_image;
        cv::Mat mask;
        cv::Mat result;

        cv::cvtColor(cv_image, hsv_image, cv::COLOR_BGR2HSV);

        cv::Scalar lower_bound(h_min, s_min, v_min);
        cv::Scalar upper_bound(h_max, s_max, v_max);

        cv::inRange(hsv_image, lower_bound, upper_bound, mask);

        cv::bitwise_and(cv_image, cv_image, result, mask);

        // 4. Кодируем обратно в JPEG и публикуем
        std::vector<int> compression_params;
        compression_params.push_back(cv::IMWRITE_JPEG_QUALITY);
        compression_params.push_back(90);

        std::vector<uchar> encoded_image;
        cv::imencode(".jpg", result, encoded_image, compression_params);

        sensor_msgs::msg::CompressedImage output_msg;
        output_msg.header = msg->header;
        output_msg.format = "jpeg";
        output_msg.data = encoded_image;

        publisher_->publish(output_msg);
    }
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<HsvFilterNode>());
    rclcpp::shutdown();
    return 0;
}
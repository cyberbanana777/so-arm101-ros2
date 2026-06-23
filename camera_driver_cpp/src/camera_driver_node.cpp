#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/compressed_image.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <opencv2/opencv.hpp>
#include <chrono>
#include <vector>

using namespace std::chrono_literals;

class CameraDriverNode : public rclcpp::Node
{
public:
    CameraDriverNode() : Node("jpeg_publisher")
    {
        // --- Объявление параметров ---
        this->declare_parameter("fps", 30.0);
        this->declare_parameter("enable_logging", true);
        this->declare_parameter("camera_image_topic", std::string("camera/image/compressed"));
        this->declare_parameter("camera_info_topic", std::string("camera/camera_info"));
        
        // Новые параметры для режима работы камеры
        this->declare_parameter("device_id", 0);  // ID устройства (0 = /dev/video0)
        this->declare_parameter("width", 1280);    // Ширина изображения
        this->declare_parameter("height", 720);    // Высота изображения
        this->declare_parameter("jpeg_quality", 90);  // Качество JPEG сжатия
        
        // Параметры калибровки
        this->declare_parameter("frame_id", std::string("camera_frame"));
        this->declare_parameter("distortion_model", std::string("plumb_bob"));
        
        std::vector<double> default_d = {0.0, 0.0, 0.0, 0.0, 0.0};
        this->declare_parameter("distortion_coefficients", default_d);
        
        std::vector<double> default_k = {
            500.0, 0.0, 320.0,
            0.0, 500.0, 240.0,
            0.0, 0.0, 1.0
        };
        this->declare_parameter("camera_matrix", default_k);
        
        std::vector<double> default_r = {
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        };
        this->declare_parameter("rectification_matrix", default_r);
        
        std::vector<double> default_p = {
            500.0, 0.0, 320.0, 0.0,
            0.0, 500.0, 240.0, 0.0,
            0.0, 0.0, 1.0, 0.0
        };
        this->declare_parameter("projection_matrix", default_p);

        // Чтение параметров
        double fps = this->get_parameter("fps").as_double();
        enable_logging_ = this->get_parameter("enable_logging").as_bool();
        camera_image_topic_ = this->get_parameter("camera_image_topic").as_string();
        camera_info_topic_ = this->get_parameter("camera_info_topic").as_string();
        
        int device_id = this->get_parameter("device_id").as_int();
        int width = this->get_parameter("width").as_int();
        int height = this->get_parameter("height").as_int();
        jpeg_quality_ = this->get_parameter("jpeg_quality").as_int();
        
        frame_id_ = this->get_parameter("frame_id").as_string();
        distortion_model_ = this->get_parameter("distortion_model").as_string();
        distortion_coefficients_ = this->get_parameter("distortion_coefficients").as_double_array();
        camera_matrix_ = this->get_parameter("camera_matrix").as_double_array();
        rectification_matrix_ = this->get_parameter("rectification_matrix").as_double_array();
        projection_matrix_ = this->get_parameter("projection_matrix").as_double_array();

        // Период таймера
        auto timer_period = std::chrono::milliseconds(static_cast<int>(1000.0 / fps));
        
        RCLCPP_INFO(this->get_logger(), 
            "Настройки: FPS=%.1f, период=%ld мс, логирование=%s",
            fps, timer_period.count(), enable_logging_ ? "true" : "false");

        // Публикаторы
        image_publisher_ = this->create_publisher<sensor_msgs::msg::CompressedImage>(
            camera_image_topic_, 10);
        camera_info_publisher_ = this->create_publisher<sensor_msgs::msg::CameraInfo>(
            camera_info_topic_, 10);

        // Таймер
        timer_ = this->create_wall_timer(timer_period, 
            std::bind(&CameraDriverNode::timer_callback, this));

        // Открываем камеру с параметрами
        RCLCPP_INFO(this->get_logger(), "Открытие камеры: device=%d, resolution=%dx%d", 
            device_id, width, height);
        
        cap_ = cv::VideoCapture(device_id);
        if (!cap_.isOpened()) {
            RCLCPP_ERROR(this->get_logger(), "Не удалось открыть камеру %d", device_id);
            rclcpp::shutdown();
            return;
        }

        // Устанавливаем запрошенные параметры
        cap_.set(cv::CAP_PROP_FRAME_WIDTH, width);
        cap_.set(cv::CAP_PROP_FRAME_HEIGHT, height);
        cap_.set(cv::CAP_PROP_FPS, fps);

        // Получаем реальное разрешение, которое установила камера
        width_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_WIDTH));
        height_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_HEIGHT));
        double actual_fps = cap_.get(cv::CAP_PROP_FPS);
        
        RCLCPP_INFO(this->get_logger(), "Разрешение камеры: %d x %d @ %.1f fps", 
            width_, height_, actual_fps);
        
        // Предупреждение, если камера не смогла установить запрошенные параметры
        if (width_ != width || height_ != height) {
            RCLCPP_WARN(this->get_logger(), 
                "Камера не поддерживает запрошенное разрешение %dx%d, используется %dx%d",
                width, height, width_, height_);
        }

        // Создаём сообщение CameraInfo с параметрами калибровки
        camera_info_msg_ = create_camera_info_msg();

        RCLCPP_INFO(this->get_logger(), "Узел JPEG publisher запущен");
    }

    ~CameraDriverNode()
    {
        if (cap_.isOpened()) {
            cap_.release();
        }
    }

private:
    rclcpp::Publisher<sensor_msgs::msg::CompressedImage>::SharedPtr image_publisher_;
    rclcpp::Publisher<sensor_msgs::msg::CameraInfo>::SharedPtr camera_info_publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    
    cv::VideoCapture cap_;
    int width_;
    int height_;
    int jpeg_quality_;
    
    bool enable_logging_;
    std::string camera_image_topic_;
    std::string camera_info_topic_;
    
    // Параметры калибровки
    std::string frame_id_;
    std::string distortion_model_;
    std::vector<double> distortion_coefficients_;
    std::vector<double> camera_matrix_;
    std::vector<double> rectification_matrix_;
    std::vector<double> projection_matrix_;
    
    sensor_msgs::msg::CameraInfo camera_info_msg_;

    sensor_msgs::msg::CameraInfo create_camera_info_msg()
    {
        sensor_msgs::msg::CameraInfo msg;
        msg.header.frame_id = frame_id_;
        msg.width = width_;
        msg.height = height_;

        msg.distortion_model = distortion_model_;
        msg.d = distortion_coefficients_;

        if (camera_matrix_.size() == 9) {
            msg.k = {
                camera_matrix_[0], camera_matrix_[1], camera_matrix_[2],
                camera_matrix_[3], camera_matrix_[4], camera_matrix_[5],
                camera_matrix_[6], camera_matrix_[7], camera_matrix_[8]
            };
        }

        if (rectification_matrix_.size() == 9) {
            msg.r = {
                rectification_matrix_[0], rectification_matrix_[1], rectification_matrix_[2],
                rectification_matrix_[3], rectification_matrix_[4], rectification_matrix_[5],
                rectification_matrix_[6], rectification_matrix_[7], rectification_matrix_[8]
            };
        }

        if (projection_matrix_.size() == 12) {
            msg.p = {
                projection_matrix_[0], projection_matrix_[1], projection_matrix_[2], projection_matrix_[3],
                projection_matrix_[4], projection_matrix_[5], projection_matrix_[6], projection_matrix_[7],
                projection_matrix_[8], projection_matrix_[9], projection_matrix_[10], projection_matrix_[11]
            };
        }

        msg.binning_x = 0;
        msg.binning_y = 0;

        msg.roi.do_rectify = false;
        msg.roi.x_offset = 0;
        msg.roi.y_offset = 0;
        msg.roi.height = 0;
        msg.roi.width = 0;

        return msg;
    }

    void timer_callback()
    {
        cv::Mat frame;
        if (!cap_.read(frame)) {
            RCLCPP_WARN(this->get_logger(), "Не удалось захватить кадр");
            return;
        }

        // --- Публикация изображения ---
        std::vector<int> encode_param;
        encode_param.push_back(cv::IMWRITE_JPEG_QUALITY);
        encode_param.push_back(jpeg_quality_);

        std::vector<uchar> encoded_image;
        if (!cv::imencode(".jpg", frame, encoded_image, encode_param)) {
            RCLCPP_ERROR(this->get_logger(), "Ошибка сжатия JPEG");
            return;
        }

        sensor_msgs::msg::CompressedImage img_msg;
        img_msg.header.stamp = this->now();
        img_msg.header.frame_id = frame_id_;
        img_msg.format = "jpeg";
        img_msg.data = encoded_image;

        image_publisher_->publish(img_msg);

        // --- Публикация CameraInfo ---
        camera_info_msg_.header.stamp = img_msg.header.stamp;
        camera_info_publisher_->publish(camera_info_msg_);

        // Логирование
        if (enable_logging_) {
            RCLCPP_INFO_THROTTLE(this->get_logger(), *this->get_clock(), 2000,
                "Опубликован JPEG кадр (%dx%d) и CameraInfo", width_, height_);
        }
    }
};

int main(int argc, char* argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<CameraDriverNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
#include <SCServo.h>
#include <iostream>
#include <thread>
#include <chrono>

int main(int argc, char** argv) {
    // Порт и baud rate можно переопределить через аргументы
    const char* port = (argc > 1) ? argv[1] : "/dev/ttyACM0";
    int baud = (argc > 2) ? std::atoi(argv[2]) : 1000000;

    std::cout << "=== Feetech SMS_STS SDK Test ===" << std::endl;
    std::cout << "Port: " << port << ", Baud: " << baud << std::endl;

    SMS_STS servo;
    if (!servo.begin(baud, port)) {
        std::cerr << "[ERROR] Failed to open port: " << port << std::endl;
        std::cerr << "Check: ls /dev/ttyACM* /dev/ttyUSB*" << std::endl;
        std::cerr << "Check: sudo usermod -aG dialout $USER" << std::endl;
        return 1;
    }
    std::cout << "[OK] Port opened" << std::endl;

    // 1. Пинг всех моторов 1-6
    std::cout << "\n--- Ping motors 1-6 ---" << std::endl;
    for (int id = 1; id <= 6; id++) {
        int pos = servo.ReadPos(id);
        if (pos != -1) {
            std::cout << "  Motor " << id << ": OK, position = " << pos << std::endl;
        } else {
            std::cout << "  Motor " << id << ": NOT FOUND" << std::endl;
        }
    }

    // 2. Тест gripper (motor 6) — самый безопасный для теста
    int test_id = 6;
    std::cout << "\n--- Testing motor " << test_id << " (gripper) ---" << std::endl;

    // Включаем момент
    int ret = servo.EnableTorque(test_id, 1);
    std::cout << "EnableTorque returned: " << ret << std::endl;
    if (ret == -1) {
        std::cerr << "[ERROR] Cannot enable torque. Motor not responding." << std::endl;
        servo.end();
        return 1;
    }
    std::cout << "[OK] Torque enabled. You should feel resistance on the servo." << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // Читаем текущую позицию
    int current = servo.ReadPos(test_id);
    std::cout << "Current position: " << current << std::endl;
    if (current == -1) {    
        std::cerr << "[ERROR] ReadPos failed after EnableTorque!" << std::endl;
        servo.EnableTorque(test_id, 0);
        servo.end();
        return 1;
    }

    // Двигаем на +200 "сырых" единиц
    int target = current + 200;
    std::cout << "Moving to position " << target << " (speed=1000, acc=50)..." << std::endl;
    servo.WritePosEx(test_id, target, 1000, 50);
    std::this_thread::sleep_for(std::chrono::seconds(2));

    int after1 = servo.ReadPos(test_id);
    std::cout << "Position after move: " << after1 << std::endl;

    // Возврат назад
    std::cout << "Returning to " << current << "..." << std::endl;
    servo.WritePosEx(test_id, current, 1000, 50);
    std::this_thread::sleep_for(std::chrono::seconds(2));

    int after2 = servo.ReadPos(test_id);
    std::cout << "Position after return: " << after2 << std::endl;

    // Выключаем момент
    servo.EnableTorque(test_id, 0);
    std::cout << "[OK] Torque disabled" << std::endl;

    servo.end();
    std::cout << "\n=== Test complete ===" << std::endl;
    return 0;
}
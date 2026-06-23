import cv2
import os
import time

# Создаём папку для изображений
os.makedirs("calibration_images", exist_ok=True)

# Открываем камеру (используй те же параметры, что в ROS2 драйвере!)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Не удалось открыть камеру")
    exit()

print("Нажмите 's' для сохранения кадра")
print("Нажмите 'q' для выхода")
print("Сделайте 15-20 снимков с разных ракурсов")

img_count = 0
last_save_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Показываем изображение
    display = frame.copy()
    cv2.putText(display, f"Images: {img_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(display, "'s' - save, 'q' - quit", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("Capture", display)
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break
    elif key == ord('s'):
        # Защита от слишком частого сохранения
        current_time = time.time()
        if current_time - last_save_time < 0.5:
            continue
        
        filename = f"calibration_images/img_{img_count:03d}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Сохранено: {filename}")
        img_count += 1
        last_save_time = current_time

cap.release()
cv2.destroyAllWindows()
print(f"\nВсего сохранено: {img_count} изображений")
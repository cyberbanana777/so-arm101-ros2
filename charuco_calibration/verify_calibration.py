import cv2
import numpy as np

# Загружаем калибровку
with open('camera_calibration.yaml', 'r') as f:
    # Пропускаем первую строку (имя ноды)
    content = f.read()
    
# Простой парсинг
import re
camera_matrix_match = re.search(r'camera_matrix: \[\s*([\d\.,\s\n]+?)\s*\]', content)
dist_coeffs_match = re.search(r'distortion_coefficients: \[([\d\.,\s-]+)\]', content)

# Извлекаем значения
camera_matrix = np.array([float(x) for x in re.findall(r'[\d.]+', camera_matrix_match.group(1))]).reshape(3, 3)
dist_coeffs = np.array([float(x) for x in dist_coeffs_match.group(1).split(',')])

print("Camera Matrix:")
print(camera_matrix)
print("\nDistortion Coefficients:")
print(dist_coeffs)

# Тестируем на новом изображении
img = cv2.imread("calibration_images/img_000.jpg")
h, w = img.shape[:2]

# Корректируем искажения
new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
    camera_matrix, dist_coeffs, (w, h), 1, (w, h)
)
undistorted = cv2.undistort(img, camera_matrix, dist_coeffs, None, new_camera_matrix)

# Сохраняем результат
combined = np.hstack((img, undistorted))
cv2.putText(combined, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
cv2.putText(combined, "Undistorted", (w + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
cv2.imwrite("verification.jpg", combined)

print("\nПроверка сохранена в verification.jpg")
print("Прямые линии на оригинале должны быть изогнуты, а на скорректированном — прямыми")
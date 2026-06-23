import cv2
import glob
import sys

# === ПАРАМЕТРЫ ДОСКИ (должны совпадать с create_charuco_board.py) ===
SQUARES_X = 7
SQUARES_Y = 5
SQUARE_LENGTH = 0.04  # метры
MARKER_LENGTH = 0.02  # метры

# === ПАРАМЕТРЫ ===
IMAGE_PATH = "calibration_images/*.jpg"  # Путь к изображениям
OUTPUT_FILE = "camera_calibration.yaml"  # Выходной файл

def main():
    # 1. Создаём ChArUco board
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    board = cv2.aruco.CharucoBoard(
        (SQUARES_X, SQUARES_Y),
        SQUARE_LENGTH,
        MARKER_LENGTH,
        aruco_dict
    )
    
    charuco_detector = cv2.aruco.CharucoDetector(board)
    
    # 2. Загружаем изображения
    image_files = sorted(glob.glob(IMAGE_PATH))
    if not image_files:
        print(f"Ошибка: не найдены изображения по пути {IMAGE_PATH}")
        sys.exit(1)
    
    print(f"Найдено {len(image_files)} изображений")
    
    # 3. Детектируем углы на каждом изображении
    all_corners = []
    all_ids = []
    image_size = None
    
    for i, img_file in enumerate(image_files):
        img = cv2.imread(img_file)
        if img is None:
            print(f"Не удалось загрузить {img_file}")
            continue
        
        if image_size is None:
            image_size = (img.shape[1], img.shape[0])
            print(f"Размер изображения: {image_size[0]}x{image_size[1]}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Детектируем ArUco маркеры
        corners, ids, rejected = charuco_detector.detectMarkers(gray)
        
        if ids is None or len(ids) < 4:
            print(f"[{i+1}/{len(image_files)}] {img_file}: мало маркеров ({len(ids) if ids is not None else 0})")
            continue
        
        # Интерполируем углы ChArUco
        ret, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
            corners, ids, gray, board
        )
        
        if ret and len(charuco_ids) >= 4:
            all_corners.append(charuco_corners)
            all_ids.append(charuco_ids)
            print(f"[{i+1}/{len(image_files)}] {img_file}: OK ({len(charuco_ids)} углов)")
            
            # Визуализация
            img_copy = img.copy()
            cv2.aruco.drawDetectedCornersCharuco(img_copy, charuco_corners, charuco_ids)
            cv2.imwrite(f"debug_{i:03d}.jpg", img_copy)
        else:
            print(f"[{i+1}/{len(image_files)}] {img_file}: не удалось найти углы")
    
    if len(all_corners) < 5:
        print(f"Ошибка: слишком мало успешных изображений ({len(all_corners)}). Нужно минимум 5.")
        sys.exit(1)
    
    print(f"\nУспешно обработано {len(all_corners)} изображений")
    
    # 4. Калибровка камеры
    print("\nВыполняется калибровка...")
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(
        all_corners,
        all_ids,
        board,
        image_size,
        None,
        None
    )
    
    print(f"RMS ошибка: {ret:.4f} пикселей")
    
    if ret > 1.0:
        print("ВНИМАНИЕ: высокая ошибка калибровки! Попробуйте больше изображений.")
    
    # 5. Сохраняем результаты
    calibration_data = {
        'image_width': image_size[0],
        'image_height': image_size[1],
        'camera_matrix': camera_matrix.tolist(),
        'distortion_coefficients': dist_coeffs[0].tolist(),
        'distortion_model': 'plumb_bob',
        'rms_error': ret,
        'num_images': len(all_corners)
    }
    
    # Сохраняем в YAML формате, совместимом с ROS2
    with open(OUTPUT_FILE, 'w') as f:
        f.write("jpeg_publisher:\n")
        f.write("  ros__parameters:\n")
        f.write(f"    frame_id: \"camera_frame\"\n")
        f.write(f"    distortion_model: \"plumb_bob\"\n")
        f.write(f"    \n")
        f.write(f"    # Калибровка выполнена с помощью ChArUco board\n")
        f.write(f"    # RMS error: {ret:.4f} pixels\n")
        f.write(f"    # Количество изображений: {len(all_corners)}\n")
        f.write(f"    \n")
        f.write(f"    distortion_coefficients: [{', '.join(f'{x:.6f}' for x in dist_coeffs[0])}]\n")
        f.write(f"    \n")
        f.write(f"    camera_matrix: [\n")
        for i in range(3):
            row = ', '.join(f'{camera_matrix[i][j]:.6f}' for j in range(3))
            comma = ',' if i < 2 else ''
            f.write(f"      {row}{comma}\n")
        f.write(f"    ]\n")
        f.write(f"    \n")
        f.write(f"    rectification_matrix: [\n")
        f.write(f"      1.0, 0.0, 0.0,\n")
        f.write(f"      0.0, 1.0, 0.0,\n")
        f.write(f"      0.0, 0.0, 1.0\n")
        f.write(f"    ]\n")
        f.write(f"    \n")
        f.write(f"    projection_matrix: [\n")
        for i in range(3):
            row = ', '.join(f'{camera_matrix[i][j]:.6f}' for j in range(3))
            f.write(f"      {row}, 0.0{',' if i < 2 else ''}\n")
        f.write(f"    ]\n")
    
    print(f"\nКалибровка сохранена в {OUTPUT_FILE}")
    
    # 6. Выводим результаты
    print("\n=== РЕЗУЛЬТАТЫ КАЛИБРОВКИ ===")
    print(f"Размер изображения: {image_size[0]}x{image_size[1]}")
    print(f"\nCamera Matrix K:")
    print(camera_matrix)
    print(f"\nDistortion Coefficients D:")
    print(dist_coeffs[0])
    print(f"\nФокусные расстояния: fx={camera_matrix[0,0]:.2f}, fy={camera_matrix[1,1]:.2f}")
    print(f"Оптический центр: cx={camera_matrix[0,2]:.2f}, cy={camera_matrix[1,2]:.2f}")

if __name__ == "__main__":
    main()
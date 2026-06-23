import cv2

# Параметры доски
squares_x = 7       # Количество клеток по X
squares_y = 5       # Количество клеток по Y
square_length = 0.04  # Длина клетки в метрах (4 см)
marker_length = 0.02  # Длина маркера в метрах (2 см)
marker_separation = 0.005  # Отступ маркера от края клетки (0.5 см)

# Создаём словарь ArUco маркеров
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

# Создаём ChArUco board
board = cv2.aruco.CharucoBoard(
    (squares_x, squares_y),
    square_length,
    marker_length,
    aruco_dict
)

# Генерируем изображение доски
img = board.generateImage((800, 600))

# Сохраняем
cv2.imwrite("charuco_board.png", img)
print("ChArUco board saved to charuco_board.png")
print(f"Распечатайте это изображение в реальном размере!")
print(f"Размер клетки должен быть: {square_length*100} см")
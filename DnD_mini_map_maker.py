import pygame
import sys
import json
import os

# Инициализация pygame
pygame.init()

# Настройки окна
WIDTH, HEIGHT = 1400, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Редактор карт: Зажми C + [1-9] для смены цвета, C + ЛКМ для рисования")

# Базовые цвета (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRID_LINE_COLOR = (210, 210, 210)      
DIFFICULT_TERRAIN_COLOR = (160, 160, 160) # Серая клетка
IMPASSABLE_TERRAIN_COLOR = (40, 40, 40)   # Чёрная клетка
WALL_COLOR = (20, 20, 20)                 
WALL_PREVIEW_COLOR = (255, 50, 50)      
BROKEN_MARK_COLOR = (255, 110, 20)        # Оранжевая звезда

# Палитра кастомных цветов (1-9)
COLOR_PALETTE = {
    1: (46, 204, 113),   # Зеленый
    2: (52, 152, 219),   # Синий
    3: (231, 76, 60),    # Красный
    4: (241, 196, 15),   # Желтый
    5: (155, 89, 182),   # Фиолетовый
    6: (230, 126, 34),   # Оранжевый
    7: (139, 69, 19),    # Коричневый
    8: (244, 143, 177),  # Розовый
    9: (79, 195, 247)    # Бирюзовый
}
current_selected_color_id = 1 # По умолчанию выбран первый цвет (зеленый)

# Настройки сетки
TILE_SIZE = 100  
MIN_TILE_SIZE = 30   
MAX_TILE_SIZE = 200  
SCALE_SPEED = 10     

DOT_RADIUS = 3   
WALL_THICKNESS = 6  

COLS, ROWS = 50, 50

# --- ХРАНИЛИЩЕ КАРТЫ ---
# Структура cells_data теперь поддерживает ключ "custom_color": id (или None)
cells_data = {}
v_walls = set()          
h_walls = set()          

last_placed_wall = None
last_edited_cell = None  

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛАМИ ---
def save_map():
    serializable_cells = {}
    for (col, row), data in cells_data.items():
        # Сохраняем клетку, если она изменена
        if data["type"] != "normal" or data["broken"] or data.get("custom_color") is not None:
            serializable_cells[f"{col},{row}"] = data

    map_data = {
        "cells": serializable_cells,
        "v_walls": [list(wall) for wall in v_walls],
        "h_walls": [list(wall) for wall in h_walls]
    }
    
    with open("map.json", "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=4)
    print("Карта успешно сохранена в файл map.json!")

def load_map():
    global cells_data, v_walls, h_walls
    if not os.path.exists("map.json"):
        print("Файл сохранения map.json не найден!")
        return

    with open("map.json", "r", encoding="utf-8") as f:
        map_data = json.load(f)
        
    cells_data.clear()
    for key, data in map_data.get("cells", {}).items():
        col, row = map(int, key.split(","))
        # Обеспечиваем обратную совместимость (если в старых сейвах нет ключа custom_color)
        if "custom_color" not in data:
            data["custom_color"] = None
        cells_data[(col, row)] = data
        
    v_walls = {tuple(wall) for wall in map_data.get("v_walls", [])}
    h_walls = {tuple(wall) for wall in map_data.get("h_walls", [])}
    print("Карта успешно загружена из файла map.json!")

# Главный цикл программы
running = True
while running:
    mx, my = pygame.mouse.get_pos()
    
    hover_col = mx // TILE_SIZE
    hover_row = my // TILE_SIZE
    current_cell = (hover_col, hover_row)

    preview_wall = None

    if 0 <= hover_col < COLS and 0 <= hover_row < ROWS:
        cell_x = mx % TILE_SIZE
        cell_y = my % TILE_SIZE
        dist_left, dist_top = cell_x, cell_y
        dist_right, dist_bottom = TILE_SIZE - cell_x, TILE_SIZE - cell_y
        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

        if min_dist == dist_left: preview_wall = ('v', hover_col, hover_row)
        elif min_dist == dist_right: preview_wall = ('v', hover_col + 1, hover_row)
        elif min_dist == dist_top: preview_wall = ('h', hover_col, hover_row)
        elif min_dist == dist_bottom: preview_wall = ('h', hover_col, hover_row + 1)

    mouse_buttons = pygame.mouse.get_pressed()
    keys = pygame.key.get_pressed()

    if not (0 <= hover_col < COLS and 0 <= hover_row < ROWS):
        last_placed_wall = None
        current_cell = None

    # Определение активных режимов
    wall_mode_active = mouse_buttons[0] and keys[pygame.K_LSHIFT] or mouse_buttons[1]
    broken_mode_active = keys[pygame.K_b] and mouse_buttons[0]
    color_mode_active = keys[pygame.K_c] # Клавиша C зажата

    # Создаем базовую пустую структуру для новой ячейки
    if current_cell and current_cell not in cells_data:
        cells_data[current_cell] = {"type": "normal", "broken": False, "custom_color": None}

    # 1. РЕЖИМ СТЕН
    if wall_mode_active:
        if preview_wall is not None and preview_wall != last_placed_wall:
            w_type, w_col, w_row = preview_wall
            target_set = v_walls if w_type == 'v' else h_walls
            if (w_col, w_row) in target_set: target_set.remove((w_col, w_row))
            else: target_set.add((w_col, w_row))
            last_placed_wall = preview_wall

    # 2. РЕЖИМ ЦВЕТНЫХ КЛЕТОК (Зажата C)
    elif color_mode_active:
        if mouse_buttons[0]:  # ЛКМ -> Красим в выбранный цвет из палитры
            if current_cell:
                cells_data[current_cell]["custom_color"] = current_selected_color_id
                # Сбрасываем тип на normal, чтобы серая/черная подложка не перекрывала цвет
                cells_data[current_cell]["type"] = "normal" 
        elif mouse_buttons[2]:  # ПКМ -> Стираем цвет
            if current_cell:
                cells_data[current_cell]["custom_color"] = None

    # 3. БИТЫЕ КЛЕТКИ (B + ЛКМ)
    elif broken_mode_active:
        if current_cell and current_cell != last_edited_cell:
            cells_data[current_cell]["broken"] = not cells_data[current_cell]["broken"]
            last_edited_cell = current_cell

    # 4. СТАДИИ КЛЕТОК (Просто ЛКМ без модификаторов)
    elif mouse_buttons[0]:
        if current_cell and current_cell != last_edited_cell:
            c_type = cells_data[current_cell]["type"]
            # Сбрасываем кастомный цвет при переключении стандартных стадий
            cells_data[current_cell]["custom_color"] = None 
            if c_type == "normal": cells_data[current_cell]["type"] = "gray"
            elif c_type == "gray": cells_data[current_cell]["type"] = "black"
            elif c_type == "black": cells_data[current_cell]["type"] = "normal"
            last_edited_cell = current_cell

    # 5. ОБЫЧНЫЙ ЛАСТИК (ПКМ без модификаторов)
    elif mouse_buttons[2]:
        if current_cell:
            cells_data[current_cell] = {"type": "normal", "broken": False, "custom_color": None}
            last_edited_cell = None
    else:
        last_placed_wall = None
        last_edited_cell = None

    # Одиночные события (Клавиатура)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Выбор активного цвета при зажатой С
            if keys[pygame.K_c]:
                if event.key == pygame.K_1: current_selected_color_id = 1
                elif event.key == pygame.K_2: current_selected_color_id = 2
                elif event.key == pygame.K_3: current_selected_color_id = 3
                elif event.key == pygame.K_4: current_selected_color_id = 4
                elif event.key == pygame.K_5: current_selected_color_id = 5
                elif event.key == pygame.K_6: current_selected_color_id = 6
                elif event.key == pygame.K_7: current_selected_color_id = 7
                elif event.key == pygame.K_8: current_selected_color_id = 8
                elif event.key == pygame.K_9: current_selected_color_id = 9
                pygame.display.set_caption(f"Редактор карт | Выбран цвет под номером: {current_selected_color_id}")
            
            # Стандартные горячие клавиши
            elif event.key == pygame.K_SPACE:
                cells_data.clear()
                v_walls.clear()
                h_walls.clear()
            elif event.key == pygame.K_s:
                save_map()
            elif event.key == pygame.K_l:
                load_map()
            elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                if TILE_SIZE < MAX_TILE_SIZE: TILE_SIZE += SCALE_SPEED
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                if TILE_SIZE > MIN_TILE_SIZE: TILE_SIZE -= SCALE_SPEED

    # --- ОТРИСОВКА ---
    screen.fill(WHITE)

    # 1. Подложка клеток
    for (col, row), data in cells_data.items():
        x_pos, y_pos = col * TILE_SIZE, row * TILE_SIZE
        
        # Определяем цвет фона клетки
        if data.get("custom_color") is not None:
            # Отрисовка кастомного цвета из палитры 1-9
            cell_color = COLOR_PALETTE[data["custom_color"]]
            pygame.draw.rect(screen, cell_color, (x_pos, y_pos, TILE_SIZE, TILE_SIZE))
        elif data["type"] == "gray":
            pygame.draw.rect(screen, DIFFICULT_TERRAIN_COLOR, (x_pos, y_pos, TILE_SIZE, TILE_SIZE))
        elif data["type"] == "black":
            pygame.draw.rect(screen, IMPASSABLE_TERRAIN_COLOR, (x_pos, y_pos, TILE_SIZE, TILE_SIZE))
        
        # Отрисовка оранжевой 8-конечной звезды (*) в центре клетки
        if data["broken"]:
            center_x = x_pos + TILE_SIZE // 2
            center_y = y_pos + TILE_SIZE // 2
            star_size = max(5, TILE_SIZE // 7)

            pygame.draw.line(screen, BROKEN_MARK_COLOR, (center_x, center_y - star_size), (center_x, center_y + star_size), 2)
            pygame.draw.line(screen, BROKEN_MARK_COLOR, (center_x - star_size, center_y), (center_x + star_size, center_y), 2)
            pygame.draw.line(screen, BROKEN_MARK_COLOR, (center_x - star_size, center_y - star_size), (center_x + star_size, center_y + star_size), 2)
            pygame.draw.line(screen, BROKEN_MARK_COLOR, (center_x + star_size, center_y - star_size), (center_x - star_size, center_y + star_size), 2)

    # 2. Базовая сетка
    for x in range(0, WIDTH + TILE_SIZE, TILE_SIZE):
        pygame.draw.line(screen, GRID_LINE_COLOR, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT + TILE_SIZE, TILE_SIZE):
            pygame.draw.line(screen, GRID_LINE_COLOR, (0, y), (WIDTH, y), 1)

    # 3. Предпросмотр стены
    if preview_wall is not None:
        w_type, w_col, w_row = preview_wall
    if w_type == 'v':
        pygame.draw.line(screen, WALL_PREVIEW_COLOR, (w_col * TILE_SIZE, w_row * TILE_SIZE), (w_col * TILE_SIZE, (w_row + 1) * TILE_SIZE), WALL_THICKNESS)
    elif w_type == 'h':
        pygame.draw.line(screen, WALL_PREVIEW_COLOR, (w_col * TILE_SIZE, w_row * TILE_SIZE), ((w_col + 1) * TILE_SIZE, w_row * TILE_SIZE), WALL_THICKNESS)

    # 4. Построенные стены
    for w_col, w_row in v_walls:
        pygame.draw.line(screen, WALL_COLOR, (w_col * TILE_SIZE, w_row * TILE_SIZE), (w_col * TILE_SIZE, (w_row + 1) * TILE_SIZE), WALL_THICKNESS)
        for w_col, w_row in h_walls:pygame.draw.line(screen, WALL_COLOR, (w_col * TILE_SIZE, w_row * TILE_SIZE), ((w_col + 1) * TILE_SIZE, w_row * TILE_SIZE), WALL_THICKNESS)

    # 5. Черные точки на углах
    for x in range(0, WIDTH + TILE_SIZE, TILE_SIZE):
        for y in range(0, HEIGHT + TILE_SIZE, TILE_SIZE):
            pygame.draw.circle(screen, BLACK, (x, y), DOT_RADIUS)
    
    pygame.display.flip()
    
pygame.quit()
sys.exit()
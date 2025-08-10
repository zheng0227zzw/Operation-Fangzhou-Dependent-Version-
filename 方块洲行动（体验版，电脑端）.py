import pygame
import random
import time
import math
import sys
import json
import os
from typing import List, Dict, Tuple, Optional

# 初始化pygame并设置中文字体
pygame.init()
try:
    # 尝试使用系统默认中文字体
    font = pygame.font.SysFont("simhei", 24)
    large_font = pygame.font.SysFont("simhei", 36)
except:
    # 如果失败则使用备用字体
    font = pygame.font.SysFont(None, 24)
    large_font = pygame.font.SysFont(None, 36)

screen_width, screen_height = 1900, 1000
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("方块洲行动")
clock = pygame.time.Clock()

# 保存文件路径
SAVE_FILE = "havoc_coins_save.json"

class GameState:
    MENU = 0
    PLAYING = 1
    DEAD = 2
    EXTRACTING = 3
    SUCCESS = 4

COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "purple": (128, 0, 128),
    "gold": (255, 215, 0),
    "ammo": (255, 215, 0),
    "health": (50, 205, 50),
    "container": (70, 130, 180),
    "grid": (100, 100, 120),
    "money": (255, 215, 0),
    "wall": (50, 50, 80)
}

ITEM_VALUES = {
    "海盗银币": 13000,
    "溶解液": 3600,
    "鼠标": 1000,
    "间谍笔": 32000,
    "海盗金币": 65000,
    "非洲之星": 13460000,
    "步战车": 30610
}

def save_havoc_coins(coins):
    """保存哈弗币到文件"""
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump({"havoc_coins": coins}, f)
    except Exception as e:
        print(f"保存数据失败: {e}")

def load_havoc_coins():
    """从文件加载哈弗币"""
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("havoc_coins", 0)
    except Exception as e:
        print(f"加载数据失败: {e}")
    return 0

class Player:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.x, self.y = screen_width // 2, screen_height // 2
        self.speed = 5
        self.health = 100
        self.max_health = 100
        self.ammo = 60
        self.max_ammo = 60
        self.reloading = False
        self.reload_start = 0
        self.reload_time = 3.5
        self.rect = pygame.Rect(self.x - 15, self.y - 15, 30, 30)
        self.bullets = []
        self.fire_rate = 6
        self.last_shot = 0
        self.inventory = [None] * 25
        self.last_damage_time = 0
        self.damage_cooldown = 1.0
        self.shooting = False
        self.last_reload_progress = 0
        
    def update(self, keys, can_shoot=True):
        # 保存旧位置用于碰撞检测
        old_x, old_y = self.x, self.y
        
        if keys[pygame.K_a]: self.x -= self.speed
        if keys[pygame.K_d]: self.x += self.speed
        if keys[pygame.K_w]: self.y -= self.speed
        if keys[pygame.K_s]: self.y += self.speed
        
        # 空气墙碰撞检测（边界外50像素）
        wall_padding = 50
        if self.x < wall_padding:
            self.x = wall_padding
        elif self.x > screen_width - wall_padding:
            self.x = screen_width - wall_padding
        if self.y < wall_padding:
            self.y = wall_padding
        elif self.y > screen_height - wall_padding:
            self.y = screen_height - wall_padding
        
        self.rect.center = (self.x, self.y)
        
        if self.reloading:
            current_time = time.time()
            reload_progress = (current_time - self.reload_start) / self.reload_time
            
            if reload_progress <= 1.0:
                self.last_reload_progress = reload_progress
            else:
                self.ammo = self.max_ammo
                self.reloading = False
        
        if self.shooting and can_shoot and not self.reloading and self.ammo > 0:
            self.shoot(pygame.mouse.get_pos())
    
    def shoot(self, target_pos):
        now = time.time()
        if now - self.last_shot >= 1 / self.fire_rate:
            self.last_shot = now
            self.ammo -= 1
            angle = math.atan2(target_pos[1] - self.y, target_pos[0] - self.x)
            self.bullets.append({
                "x": self.x, "y": self.y, "angle": angle,
                "speed": 15, "damage": 25, "create_time": now
            })
    
    def take_damage(self, amount):
        now = time.time()
        if now - self.last_damage_time >= self.damage_cooldown:
            self.last_damage_time = now
            self.health -= amount
            return self.health <= 0
        return False
    
    def heal(self):
        if self.health <= 50:
            self.health = min(self.max_health, self.health + 50)
        else:
            self.health = self.max_health
    
    def can_pickup(self):
        return None in self.inventory
    
    def add_to_inventory(self, item):
        for i, slot in enumerate(self.inventory):
            if slot is None:
                self.inventory[i] = item
                return True
        return False

class Enemy:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.speed = 2
        self.health = 100
        self.damage = 15
        self.attack_cooldown = 1.0
        self.last_attack = 0
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.bullets = []
        
    def update(self, player):
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            dx, dy = dx/dist, dy/dist
            self.x += dx * self.speed
            self.y += dy * self.speed
        
        self.rect.center = (self.x, self.y)
        
        now = time.time()
        if now - self.last_attack >= self.attack_cooldown and dist < 300:
            self.last_attack = now
            angle = math.atan2(dy, dx)
            self.bullets.append({
                "x": self.x, "y": self.y, "angle": angle,
                "speed": 10, "damage": self.damage, "create_time": now
            })
    
    def take_damage(self, amount):
        self.health -= amount
        return self.health <= 0

class Container:
    def __init__(self, x, y, name, game):
        self.x, self.y = x, y
        self.name = name
        self.game = game
        self.rect = pygame.Rect(x - 25, y - 25, 50, 50)
        self.items = []
        self.grid_size = 5
        self.max_items = 7
        self.generate_items()
        self.is_open = False
        
    def generate_items(self):
        common_items = [
            {"name": "海盗银币", "color": COLORS["blue"], "value": ITEM_VALUES["海盗银币"], "weight": 40},
            {"name": "溶解液", "color": COLORS["green"], "value": ITEM_VALUES["溶解液"], "weight": 30},
            {"name": "鼠标", "color": COLORS["white"], "value": ITEM_VALUES["鼠标"], "weight": 30},
            {"name": "间谍笔", "color": COLORS["purple"], "value": ITEM_VALUES["间谍笔"], "weight": 10},  # 降低间谍笔刷新率
            {"name": "海盗金币", "color": COLORS["gold"], "value": ITEM_VALUES["海盗金币"], "weight": 5}  # 海盗金币刷新率更低
        ]
        
        rare_items = [
            {"name": "非洲之星", "color": COLORS["red"], "value": ITEM_VALUES["非洲之星"]},
            {"name": "步战车", "color": COLORS["red"], "value": ITEM_VALUES["步战车"]}
        ]
        
        # 生成3-7个物品
        num_items = random.randint(3, self.max_items)
        
        # 非洲之星生成逻辑 (1%基础概率，100局保底)
        if not self.game.africa_star_spawned and (random.random() < 0.01 or self.game.africa_star_counter >= 100):
            self.items.append(rare_items[0])
            self.game.africa_star_spawned = True
            self.game.africa_star_counter = 0
            num_items -= 1
        
        # 步战车生成逻辑 (2%基础概率，50局保底)
        if not self.game.tank_spawned and (random.random() < 0.02 or self.game.tank_counter >= 50):
            self.items.append(rare_items[1])
            self.game.tank_spawned = True
            self.game.tank_counter = 0
            num_items -= 1
        
        # 生成普通物品（使用加权随机）
        weights = [item["weight"] for item in common_items]
        for _ in range(num_items):
            item = random.choices(common_items, weights=weights, k=1)[0].copy()
            del item["weight"]  # 移除权重属性
            self.items.append(item)
    
    def transfer_item(self, grid_index, player):
        if 0 <= grid_index < len(self.items) and player.can_pickup():
            transferred_item = self.items.pop(grid_index)
            if player.add_to_inventory(transferred_item):
                self.game.current_raid_value += transferred_item["value"]
                return True
        return False
    
    def receive_item(self, item):
        if len(self.items) < self.max_items:
            self.items.append(item)
            return True
        return False

class Game:
    def __init__(self):
        # 初始化时加载保存的哈弗币
        self.havoc_coins = load_havoc_coins()
        self.reset_game()
    
    def reset_game(self):
        self.state = GameState.MENU
        self.player = Player()
        self.enemies = []
        self.containers = []
        self.medkits = []
        self.extract_zone = None
        self.last_enemy_spawn = 0
        self.enemy_spawn_interval = 60
        self.last_medkit_spawn = 0
        self.medkit_spawn_interval = 30
        self.extraction_start = 0
        self.extraction_time = 10
        self.container_open = None
        self.inventory_open = False
        self.current_raid_value = 0
        self.extracted_value = 0
        self.africa_star_counter = 0
        self.tank_counter = 0
        self.africa_star_spawned = False
        self.tank_spawned = False
        
        self.setup_level()
    
    def setup_level(self):
        self.containers = []
        self.enemies = []
        self.medkits = []
        self.current_raid_value = 0
        self.extracted_value = 0
        self.africa_star_counter += 1
        self.tank_counter += 1
        self.africa_star_spawned = False
        self.tank_spawned = False
        
        # 更自然分散的容器分布
        container_types = ["衣服", "衣柜", "武器箱", "高级储物箱", "收纳盒", "野外物资箱"]
        container_positions = [
            (200, 150),  # 左上
            (1000, 180),  # 右上
            (250, 550),   # 左下
            (950, 600),   # 右下
            (600, 300),   # 中上
            (650, 500)    # 中下
        ]
        
        for name, pos in zip(container_types, container_positions):
            self.containers.append(Container(pos[0], pos[1], name, self))
        
        self.extract_zone = pygame.Rect(
            screen_width - 150, screen_height - 150, 100, 100)
        
        for _ in range(5):
            self.spawn_enemy()
    
    def spawn_enemy(self):
        side = random.randint(0, 3)
        padding = 100
        if side == 0:  # 上
            x = random.randint(padding, screen_width - padding)
            y = -50
        elif side == 1:  # 右
            x = screen_width + 50
            y = random.randint(padding, screen_height - padding)
        elif side == 2:  # 下
            x = random.randint(padding, screen_width - padding)
            y = screen_height + 50
        else:  # 左
            x = -50
            y = random.randint(padding, screen_height - padding)
        
        self.enemies.append(Enemy(x, y))
        self.last_enemy_spawn = time.time()
    
    def spawn_medkit(self):
        valid_position = False
        while not valid_position:
            x = random.randint(50, screen_width - 50)
            y = random.randint(50, screen_height - 50)
            new_rect = pygame.Rect(x - 15, y - 15, 30, 30)
            
            valid_position = True
            for container in self.containers:
                if new_rect.colliderect(container.rect):
                    valid_position = False
                    break
            
            if valid_position:
                self.medkits.append(new_rect)
                self.last_medkit_spawn = time.time()
                break
    
    def calculate_inventory_value(self):
        total = 0
        for item in self.player.inventory:
            if item is not None:
                total += item["value"]
        return total
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # 退出时保存哈弗币
                save_havoc_coins(self.havoc_coins)
                return False
            
            if self.state == GameState.MENU:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.reset_game()  # 先重置游戏
                    self.state = GameState.PLAYING  # 再改变状态
            
            elif self.state in [GameState.PLAYING, GameState.EXTRACTING]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and not self.player.reloading and self.player.ammo < self.player.max_ammo:
                        self.player.reloading = True
                        self.player.reload_start = time.time()
                    
                    if event.key == pygame.K_e:
                        self.inventory_open = not self.inventory_open
                    
                    if event.key == pygame.K_f:
                        if self.container_open:
                            if self.container_open.is_open:
                                self.container_open.is_open = False
                                self.inventory_open = False
                            else:
                                self.container_open.is_open = True
                                self.inventory_open = True
                
                # 修改：左键射击
                if event.type == pygame.MOUSEBUTTONDOWN and not self.inventory_open:
                    if event.button == 1:  # 左键射击
                        self.player.shooting = True
                        self.player.shoot(pygame.mouse.get_pos())
                
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # 左键释放
                        self.player.shooting = False
                
                if event.type == pygame.MOUSEBUTTONDOWN and self.inventory_open:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    backpack_area = pygame.Rect(50, 100, screen_width//2 - 100, screen_height - 200)
                    if backpack_area.collidepoint(mouse_pos):
                        col = (mouse_pos[0] - 50) // ((screen_width//2 - 100) // 5)
                        row = (mouse_pos[1] - 100) // ((screen_height - 200) // 5)
                        clicked_index = row * 5 + col
                        
                        # 右键点击背包物品放回容器
                        if event.button == 3 and clicked_index < len(self.player.inventory):
                            if self.container_open and self.container_open.is_open:
                                # 将物品转移到容器中
                                item = self.player.inventory[clicked_index]
                                if item is not None and len(self.container_open.items) < self.container_open.max_items:
                                    self.container_open.items.append(item)
                                    self.player.inventory[clicked_index] = None
                                    self.current_raid_value -= item["value"]
                    
                    if self.container_open and self.container_open.is_open:
                        container_area = pygame.Rect(screen_width//2 + 50, 100, screen_width//2 - 100, screen_height - 200)
                        if container_area.collidepoint(mouse_pos):
                            col = (mouse_pos[0] - (screen_width//2 + 50)) // ((screen_width//2 - 100) // 5)
                            row = (mouse_pos[1] - 100) // ((screen_height - 200) // 5)
                            clicked_index = row * 5 + col
                            
                            # 左键点击容器物品拾取
                            if event.button == 1 and clicked_index < len(self.container_open.items):
                                self.container_open.transfer_item(clicked_index, self.player)
            
            elif self.state in (GameState.DEAD, GameState.SUCCESS):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_v:
                    self.reset_game()
        
        return True
    
    def update(self):
        if self.state in [GameState.PLAYING, GameState.EXTRACTING]:
            keys = pygame.key.get_pressed()
            can_shoot = not self.inventory_open
            self.player.update(keys, can_shoot)
            
            current_time = time.time()
            for bullet in self.player.bullets[:]:
                bullet["x"] += math.cos(bullet["angle"]) * bullet["speed"]
                bullet["y"] += math.sin(bullet["angle"]) * bullet["speed"]
                
                for enemy in self.enemies[:]:
                    if math.sqrt((bullet["x"] - enemy.x)**2 + (bullet["y"] - enemy.y)**2) < 20:
                        if enemy.take_damage(bullet["damage"]):
                            self.enemies.remove(enemy)
                        if bullet in self.player.bullets:
                            self.player.bullets.remove(bullet)
                        break
                
                if (bullet["x"] < 0 or bullet["x"] > screen_width or 
                    bullet["y"] < 0 or bullet["y"] > screen_height):
                    if bullet in self.player.bullets:
                        self.player.bullets.remove(bullet)
            
            for enemy in self.enemies[:]:
                enemy.update(self.player)
                
                for bullet in enemy.bullets[:]:
                    bullet["x"] += math.cos(bullet["angle"]) * bullet["speed"]
                    bullet["y"] += math.sin(bullet["angle"]) * bullet["speed"]
                    
                    if self.player.rect.collidepoint(bullet["x"], bullet["y"]):
                        if self.player.take_damage(bullet["damage"]):
                            self.state = GameState.DEAD
                            self.extracted_value = 0
                        enemy.bullets.remove(bullet)
                        continue
                    
                    if (bullet["x"] < 0 or bullet["x"] > screen_width or 
                        bullet["y"] < 0 or bullet["y"] > screen_height):
                        enemy.bullets.remove(bullet)
            
            if current_time - self.last_enemy_spawn >= self.enemy_spawn_interval:
                for _ in range(5):
                    self.spawn_enemy()
            
            if (len(self.medkits) == 0 and 
                current_time - self.last_medkit_spawn >= self.medkit_spawn_interval):
                self.spawn_medkit()
            
            for medkit in self.medkits[:]:
                if self.player.rect.colliderect(medkit):
                    self.player.heal()
                    self.medkits.remove(medkit)
            
            self.container_open = None
            for container in self.containers:
                if self.player.rect.colliderect(container.rect):
                    self.container_open = container
                    break
            
            if self.player.rect.colliderect(self.extract_zone):
                if self.state != GameState.EXTRACTING:
                    self.state = GameState.EXTRACTING
                    self.extraction_start = current_time
            else:
                if self.state == GameState.EXTRACTING:
                    self.state = GameState.PLAYING
            
            if (self.state == GameState.EXTRACTING and 
                current_time - self.extraction_start >= self.extraction_time):
                self.state = GameState.SUCCESS
                if self.player.reloading:
                    self.player.ammo = self.player.max_ammo
                    self.player.reloading = False
                
                # 计算并增加哈弗币
                self.extracted_value = self.calculate_inventory_value()
                self.havoc_coins += self.extracted_value
    
    def draw_grid_ui(self, x, y, width, height, cols, rows, items, title):
        cell_width = width // cols
        cell_height = height // rows
        
        pygame.draw.rect(screen, (50, 50, 80), (x, y, width, height), border_radius=10)
        pygame.draw.rect(screen, COLORS["blue"], (x, y, width, height), 2, border_radius=10)
        
        title_text = large_font.render(title, True, COLORS["white"])
        screen.blit(title_text, (x + width//2 - title_text.get_width()//2, y - 40))
        
        for col in range(cols + 1):
            pygame.draw.line(screen, COLORS["grid"], 
                           (x + col * cell_width, y),
                           (x + col * cell_width, y + height), 1)
        for row in range(rows + 1):
            pygame.draw.line(screen, COLORS["grid"],
                           (x, y + row * cell_height),
                           (x + width, y + row * cell_height), 1)
        
        for i, item in enumerate(items):
            if item is not None:
                row = i // cols
                col = i % cols
                item_x = x + col * cell_width + 10
                item_y = y + row * cell_height + 10
                
                item_text = font.render(item["name"], True, item["color"])
                screen.blit(item_text, (item_x, item_y))
                
                value_text = font.render(f"¥{item['value']:,}", True, COLORS["money"])
                screen.blit(value_text, (item_x, item_y + 20))
    
    def draw(self):
        screen.fill(COLORS["black"])
        
        # 绘制空气墙
        wall_padding = 50
        wall_rects = [
            pygame.Rect(0, 0, screen_width, wall_padding),  # 上墙
            pygame.Rect(0, 0, wall_padding, screen_height),  # 左墙
            pygame.Rect(screen_width - wall_padding, 0, wall_padding, screen_height),  # 右墙
            pygame.Rect(0, screen_height - wall_padding, screen_width, wall_padding)  # 下墙
        ]
        for wall in wall_rects:
            pygame.draw.rect(screen, COLORS["wall"], wall)
        
        if self.state == GameState.MENU:
            menu_bg = pygame.Surface((screen_width, screen_height))
            menu_bg.fill((20, 20, 40))
            screen.blit(menu_bg, (0, 0))
            
            title = large_font.render("方块洲行动（内测版）", True, COLORS["white"])
            subtitle = font.render("代号: DRO", True, (200, 50, 50))
            start = large_font.render("按Enter键开始行动", True, COLORS["green"])
            
            coins_text = large_font.render(f"方块币: ¥{self.havoc_coins:,}", True, COLORS["money"])
            
            screen.blit(title, (screen_width//2 - title.get_width()//2, screen_height//3))
            screen.blit(subtitle, (screen_width//2 - subtitle.get_width()//2, screen_height//3 + 60))
            screen.blit(start, (screen_width//2 - start.get_width()//2, screen_height//2 + 100))
            screen.blit(coins_text, (screen_width//2 - coins_text.get_width()//2, screen_height//2 + 180))
        
        elif self.state in [GameState.PLAYING, GameState.EXTRACTING]:
            pygame.draw.rect(screen, COLORS["green"], self.extract_zone, border_radius=5)
            
            for container in self.containers:
                color = COLORS["container"] if container == self.container_open else COLORS["white"]
                pygame.draw.rect(screen, color, container.rect, 2, border_radius=5)
                
                name_text = font.render(container.name, True, COLORS["white"])
                screen.blit(name_text, (container.rect.centerx - name_text.get_width()//2, 
                                      container.rect.y - 30))
            
            for medkit in self.medkits:
                pygame.draw.rect(screen, COLORS["health"], medkit, border_radius=3)
                pygame.draw.line(screen, COLORS["white"], 
                               (medkit.x + 5, medkit.centery), 
                               (medkit.right - 5, medkit.centery), 3)
                pygame.draw.line(screen, COLORS["white"], 
                               (medkit.centerx, medkit.y + 5), 
                               (medkit.centerx, medkit.bottom - 5), 3)
            
            pygame.draw.rect(screen, COLORS["white"], self.player.rect, border_radius=3)
            mouse_pos = pygame.mouse.get_pos()
            angle = math.atan2(mouse_pos[1] - self.player.y, mouse_pos[0] - self.player.x)
            end_x = self.player.x + math.cos(angle) * 25
            end_y = self.player.y + math.sin(angle) * 25
            pygame.draw.line(screen, COLORS["red"], (self.player.x, self.player.y), (end_x, end_y), 2)
            
            for bullet in self.player.bullets:
                pygame.draw.circle(screen, COLORS["ammo"], (int(bullet["x"]), int(bullet["y"])), 4)
            
            for enemy in self.enemies:
                pygame.draw.rect(screen, COLORS["red"], enemy.rect, border_radius=3)
                pygame.draw.rect(screen, COLORS["black"], 
                               (enemy.rect.x, enemy.rect.y - 12, enemy.rect.width, 6))
                pygame.draw.rect(screen, COLORS["health"], 
                               (enemy.rect.x, enemy.rect.y - 12, 
                                enemy.rect.width * (enemy.health / 100), 6))
                
                for bullet in enemy.bullets:
                    pygame.draw.circle(screen, (255, 100, 100), (int(bullet["x"]), int(bullet["y"])), 3)
            
            ui_panel = pygame.Surface((screen_width, 80), pygame.SRCALPHA)
            ui_panel.fill((0, 0, 0, 150))
            screen.blit(ui_panel, (0, 0))
            
            health_text = font.render(f"生命: {self.player.health}/{self.player.max_health}", True, COLORS["white"])
            pygame.draw.rect(screen, (50, 50, 50), (120, 30, 200, 20))
            pygame.draw.rect(screen, COLORS["health"], 
                           (120, 30, 200 * (self.player.health / self.player.max_health), 20))
            screen.blit(health_text, (20, 30))
            
            ammo_text = font.render(f"弹药: {self.player.ammo}/{self.player.max_ammo}", True, COLORS["ammo"])
            screen.blit(ammo_text, (20, 55))
            
            value_text = font.render(f"物资价值: ¥{self.current_raid_value:,}", True, COLORS["money"])
            screen.blit(value_text, (screen_width - value_text.get_width() - 20, 30))
            
            # 添加操作提示
            controls_text = font.render("左键射击 | R换弹 | F互动 | E背包", True, COLORS["white"])
            screen.blit(controls_text, (screen_width//2 - controls_text.get_width()//2, screen_height - 30))
            
            if self.player.reloading and self.state in [GameState.PLAYING, GameState.EXTRACTING]:
                reload_progress = self.player.last_reload_progress
                pygame.draw.rect(screen, (80, 80, 80), 
                               (screen_width//2 - 150, 50, 300, 20), border_radius=10)
                pygame.draw.rect(screen, (0, 150, 255), 
                               (screen_width//2 - 150, 50, 300 * reload_progress, 20), border_radius=10)
                reload_text = large_font.render("换弹中...", True, COLORS["white"])
                screen.blit(reload_text, (screen_width//2 - reload_text.get_width()//2, 15))
            
            if self.container_open and not self.container_open.is_open:
                prompt = large_font.render(f"按F打开{self.container_open.name}", True, COLORS["white"])
                screen.blit(prompt, (screen_width//2 - prompt.get_width()//2, screen_height - 120))
            
            if self.inventory_open:
                overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                screen.blit(overlay, (0, 0))
                
                self.draw_grid_ui(
                    50, 100, screen_width//2 - 100, screen_height - 200,
                    5, 5, self.player.inventory, "背包"
                )
                
                # 添加背包操作提示
                backpack_tip = font.render("右键放回物品", True, COLORS["white"])
                screen.blit(backpack_tip, (50, screen_height - 80))
                
                if self.container_open and self.container_open.is_open:
                    self.draw_grid_ui(
                        screen_width//2 + 50, 100, screen_width//2 - 100, screen_height - 200,
                        5, 5, self.container_open.items, self.container_open.name
                    )
                    
                    # 添加容器操作提示
                    container_tip = font.render("左键拾取物品到背包", True, COLORS["white"])
                    screen.blit(container_tip, (screen_width//2 + 50, screen_height - 80))
            
            if self.state == GameState.EXTRACTING:
                remaining = max(0, self.extraction_time - (time.time() - self.extraction_start))
                timer_bg = pygame.Surface((300, 60), pygame.SRCALPHA)
                timer_bg.fill((0, 0, 0, 150))
                screen.blit(timer_bg, (screen_width//2 - 150, 20))
                
                extract_text = large_font.render("撤离中", True, COLORS["green"])
                time_text = large_font.render(f"{remaining:.1f}秒", True, COLORS["white"])
                
                screen.blit(extract_text, (screen_width//2 - extract_text.get_width()//2, 25))
                screen.blit(time_text, (screen_width//2 - time_text.get_width()//2, 60))
        
        elif self.state == GameState.DEAD:
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((50, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            
            fail_text = large_font.render("任务失败", True, COLORS["red"])
            reason_text = font.render("你已被敌人击毙", True, (200, 200, 200))
            prompt = large_font.render("按V键返回主菜单", True, COLORS["white"])
            value_text = large_font.render(f"带出物资价值: ¥0", True, COLORS["money"])
            
            screen.blit(fail_text, (screen_width//2 - fail_text.get_width()//2, screen_height//2 - 80))
            screen.blit(reason_text, (screen_width//2 - reason_text.get_width()//2, screen_height//2 - 30))
            screen.blit(value_text, (screen_width//2 - value_text.get_width()//2, screen_height//2 + 10))
            screen.blit(prompt, (screen_width//2 - prompt.get_width()//2, screen_height//2 + 80))
        
        elif self.state == GameState.SUCCESS:
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 50, 0, 200))
            screen.blit(overlay, (0, 0))
            
            success_text = large_font.render("任务完成", True, COLORS["green"])
            reward_text = font.render("成功撤离！", True, (200, 255, 200))
            prompt = large_font.render("按V键返回主菜单", True, COLORS["white"])
            value_text = large_font.render(f"带出物资价值: ¥{self.extracted_value:,}", True, COLORS["money"])
            coins_text = large_font.render(f"获得方块币: ¥{self.extracted_value:,}", True, COLORS["money"])
            
            screen.blit(success_text, (screen_width//2 - success_text.get_width()//2, screen_height//2 - 120))
            screen.blit(reward_text, (screen_width//2 - reward_text.get_width()//2, screen_height//2 - 70))
            screen.blit(value_text, (screen_width//2 - value_text.get_width()//2, screen_height//2 - 20))
            screen.blit(coins_text, (screen_width//2 - coins_text.get_width()//2, screen_height//2 + 30))
            screen.blit(prompt, (screen_width//2 - prompt.get_width()//2, screen_height//2 + 100))
        
        pygame.display.flip()
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            clock.tick(60)
        
        # 游戏循环结束后保存哈弗币
        save_havoc_coins(self.havoc_coins)
        pygame.quit()

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        print(f"游戏崩溃: {str(e)}")
        pygame.quit()
        raise

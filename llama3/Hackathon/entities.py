# entities.py
# ──────────────────────────────────────────────────────────────────────────────
import pygame
import random

class Tile(pygame.sprite.Sprite):
    def __init__(self, image, x, y, passable):
        super().__init__()
        self.image    = image
        self.rect     = image.get_rect(topleft=(x, y))
        self.passable = passable

class Player(pygame.sprite.Sprite):
    def __init__(self, image, pos, maze_cols=None, maze_rows=None, tile_size=None):
        super().__init__()
        self.image      = image
        self.rect       = image.get_rect(topleft=pos)
        self.base_speed = 4
        self.speed      = self.base_speed
        self.maze_cols  = maze_cols
        self.maze_rows  = maze_rows
        self.tile_size  = tile_size

    def update(self, walls):
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.speed
        dy = (keys[pygame.K_DOWN]  - keys[pygame.K_UP])   * self.speed
        if dx: self._move(dx, 0, walls)
        if dy: self._move(0, dy, walls)

    def _move(self, dx, dy, walls):
        # Calculate new position
        new_x = self.rect.x + dx
        new_y = self.rect.y + dy
        # Boundary checks
        if self.maze_cols is not None and self.maze_rows is not None and self.tile_size is not None:
            min_x = 0
            min_y = 0
            max_x = (self.maze_cols - 1) * self.tile_size
            max_y = (self.maze_rows - 1) * self.tile_size
            # Only move if within bounds (player must stay fully inside the maze)
            if not (min_x <= new_x < max_x and min_y <= self.rect.y < max_y):
                dx = 0
            if not (min_y <= new_y < max_y and min_x <= self.rect.x < max_x):
                dy = 0
        self.rect.x += dx
        if pygame.sprite.spritecollideany(self, walls):
            self.rect.x -= dx
        self.rect.y += dy
        if pygame.sprite.spritecollideany(self, walls):
            self.rect.y -= dy

class Oxygen(pygame.sprite.Sprite):
    def __init__(self, image, pos):
        super().__init__()
        self.image = image
        self.rect  = image.get_rect(center=pos)

class Germ(pygame.sprite.Sprite):
    def __init__(self, image, pos):
        super().__init__()
        self.image     = image
        self.rect      = image.get_rect(topleft=pos)
        self.direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)]) # random initial direction
        self.speed     = 2
        self.change_dir_timer = 0
        self.change_dir_interval = random.randint(30, 90) # frames until next direction change

    def update(self, walls):
        # Move in current direction
        dx, dy = self.direction
        self.rect.x += dx * self.speed
        self.rect.y += dy * self.speed
        collided = pygame.sprite.spritecollideany(self, walls)
        if collided:
            # If hit wall, pick a new random direction
            self.rect.x -= dx * self.speed
            self.rect.y -= dy * self.speed
            self.direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
            self.change_dir_timer = 0
            self.change_dir_interval = random.randint(30, 90)
        else:
            # Occasionally change direction randomly
            self.change_dir_timer += 1
            if self.change_dir_timer >= self.change_dir_interval:
                self.direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
                self.change_dir_timer = 0
                self.change_dir_interval = random.randint(30, 90)

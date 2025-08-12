# maze.py
# ──────────────────────────────────────────────────────────────────────────────
import random

class Maze:
    """Generate a perfect maze using recursive backtracker."""
    def __init__(self, cols, rows):
        # ensure odd dimensions so corridors line up
        self.cols = cols if cols % 2 == 1 else cols + 1
        self.rows = rows if rows % 2 == 1 else rows + 1
        # 1 = wall, 0 = floor
        self.grid = [[1 for _ in range(self.cols)] for _ in range(self.rows)]
        self._carve(1, 1)
        # enforce outer walls
        for x in range(self.cols):
            self.grid[0][x] = self.grid[self.rows - 1][x] = 1
        for y in range(self.rows):
            self.grid[y][0] = self.grid[y][self.cols - 1] = 1
        # Add extra intersections to reduce dead ends
        self._add_intersections()

    def _carve(self, cx, cy):
        self.grid[cy][cx] = 0
        dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if (1 <= nx < self.cols - 1 and 1 <= ny < self.rows - 1
                    and self.grid[ny][nx] == 1):
                # remove wall between
                self.grid[cy + dy // 2][cx + dx // 2] = 0
                self._carve(nx, ny)

    def _add_intersections(self):
        """Randomly open up walls to create more intersections."""
        for y in range(2, self.rows - 2, 2):
            for x in range(2, self.cols - 2, 2):
                if self.grid[y][x] == 0:
                    # Check for dead ends (only one open neighbor)
                    open_neighbors = 0
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        if self.grid[y+dy][x+dx] == 0:
                            open_neighbors += 1
                    if open_neighbors <= 1 and random.random() < 0.5:
                        # Randomly open a wall to create an intersection
                        dirs = [(-1,0),(1,0),(0,-1),(0,1)]
                        random.shuffle(dirs)
                        for dx, dy in dirs:
                            nx, ny = x + dx, y + dy
                            if self.grid[ny][nx] == 1:
                                self.grid[ny][nx] = 0
                                break

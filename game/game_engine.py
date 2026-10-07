import pygame
import time
import json
from collections import deque
from pathlib import Path
from game.maze import generate_maze, CELL
from game.player import Player

FPS = 60
BG = (240, 235, 220)
WALL_COLOR = (40, 40, 60)
EXIT_COLOR = (80, 200, 80)
PATH_COLOR = (255, 210, 70)
FOG_COLOR = (0, 0, 0, 210)
FOG_RADIUS = CELL * 3
LEADERBOARD_FILE = Path(__file__).with_name("leaderboard.json")
DIFFICULTIES = {
    "Easy": (10, 8),
    "Medium": (15, 13),
    "Hard": (20, 18),
}
MAX_WIDTH = 15 * CELL
MAX_HEIGHT = 13 * CELL + 60

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((MAX_WIDTH, MAX_HEIGHT))
        pygame.display.set_caption("Maze Runner")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 22)
        self.big_font = pygame.font.SysFont("monospace", 36, bold=True)
        self.leaderboard = self.load_leaderboard()
        self.difficulty = None
        self.cols = 0
        self.rows = 0
        self.width = MAX_WIDTH
        self.height = MAX_HEIGHT

    def load_leaderboard(self):
        try:
            with LEADERBOARD_FILE.open("r", encoding="utf-8") as file:
                scores = json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

        if not isinstance(scores, list):
            return []
        return sorted(
            (score for score in scores if isinstance(score, (int, float))),
        )[:5]

    def save_score(self):
        self.leaderboard.append(self.elapsed)
        self.leaderboard.sort()
        self.leaderboard = self.leaderboard[:5]
        with LEADERBOARD_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.leaderboard, file, indent=2)

    def reset(self):
        self.walls = generate_maze(self.cols, self.rows)
        self.player = Player(0, 0)
        self.exit_rect = pygame.Rect((self.cols-1)*CELL+5, (self.rows-1)*CELL+5, CELL-10, CELL-10)
        self.start_time = time.time()
        self.elapsed = 0
        self.won = False
        self.path = None

    def select_difficulty(self, name):
        self.difficulty = name
        self.cols, self.rows = DIFFICULTIES[name]
        self.width = self.cols * CELL
        self.height = self.rows * CELL + 60
        self.reset()

    def find_shortest_path(self):
        start = (0, 0)
        exit_cell = (self.rows - 1, self.cols - 1)
        queue = deque([start])
        visited = {start}
        parents = {start: None}
        directions = [(-1, 0, 0), (1, 0, 1), (0, 1, 2), (0, -1, 3)]

        while queue:
            cell = queue.popleft()
            if cell == exit_cell:
                break

            r, c = cell
            for dr, dc, wall_dir in directions:
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < self.rows
                    and 0 <= nc < self.cols
                    and not self.walls[r][c][wall_dir]
                    and (nr, nc) not in visited
                ):
                    visited.add((nr, nc))
                    parents[(nr, nc)] = cell
                    queue.append((nr, nc))

        if exit_cell not in parents:
            return []

        path = []
        cell = exit_cell
        while cell is not None:
            path.append(cell)
            cell = parents[cell]
        path.reverse()
        return path

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if self.difficulty is None:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for name, button in self.difficulty_buttons():
                        if button.collidepoint(event.pos):
                            self.select_difficulty(name)
                            break
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.difficulty = None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                if self.path is None:
                    self.path = self.find_shortest_path()
                else:
                    self.path = None
        return True

    def update(self):
        if self.difficulty is None:
            return
        if self.won:
            return
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.walls, self.rows, self.cols)
        self.elapsed = time.time() - self.start_time
        if self.player.rect.colliderect(self.exit_rect):
            self.won = True
            self.save_score()

    def draw_maze(self):
        wall_w = 3
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = c*CELL, r*CELL
                w = self.walls[r][c]
                if w[0]: pygame.draw.line(self.screen, WALL_COLOR, (x,y), (x+CELL,y), wall_w)
                if w[1]: pygame.draw.line(self.screen, WALL_COLOR, (x,y+CELL), (x+CELL,y+CELL), wall_w)
                if w[2]: pygame.draw.line(self.screen, WALL_COLOR, (x+CELL,y), (x+CELL,y+CELL), wall_w)
                if w[3]: pygame.draw.line(self.screen, WALL_COLOR, (x,y), (x,y+CELL), wall_w)

    def difficulty_buttons(self):
        button_width, button_height = 240, 60
        x = (MAX_WIDTH - button_width) // 2
        return [
            (name, pygame.Rect(x, 220 + index * 90, button_width, button_height))
            for index, name in enumerate(DIFFICULTIES)
        ]

    def draw_difficulty_screen(self):
        self.screen.fill(BG)
        title = self.big_font.render("Select Difficulty", True, (30, 30, 50))
        self.screen.blit(title, (MAX_WIDTH // 2 - title.get_width() // 2, 100))
        for name, button in self.difficulty_buttons():
            pygame.draw.rect(self.screen, (60, 120, 220), button, border_radius=8)
            label = self.font.render(name, True, (255, 255, 255))
            self.screen.blit(
                label,
                (button.centerx - label.get_width() // 2, button.centery - label.get_height() // 2),
            )
        pygame.display.flip()

    def draw(self):
        if self.difficulty is None:
            self.draw_difficulty_screen()
            return
        self.screen.fill(BG)
        if self.path:
            for r, c in self.path:
                path_rect = pygame.Rect(c * CELL, r * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, PATH_COLOR, path_rect)
        self.draw_maze()
        pygame.draw.rect(self.screen, EXIT_COLOR, self.exit_rect, border_radius=4)
        ex_label = self.font.render("EXIT", True, (20,80,20))
        self.screen.blit(ex_label, (self.exit_rect.x+2, self.exit_rect.y+4))

        fog = pygame.Surface((self.width, self.rows * CELL), pygame.SRCALPHA)
        fog.fill(FOG_COLOR)
        clear = pygame.Surface((self.width, self.rows * CELL), pygame.SRCALPHA)
        clear.fill((255, 255, 255, 255))
        pygame.draw.circle(
            clear,
            (0, 0, 0, 0),
            self.player.rect.center,
            FOG_RADIUS,
        )
        fog.blit(clear, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(fog, (0, 0))
        self.player.draw(self.screen)

        hud = pygame.Rect(0, self.rows*CELL, self.width, 60)
        pygame.draw.rect(self.screen, (30,30,50), hud)
        time_surf = self.font.render(f"Time: {self.elapsed:.1f}s   R = New Maze", True, (200,200,200))
        self.screen.blit(time_surf, (10, self.rows*CELL+18))

        if self.won:
            overlay = pygame.Surface((self.width, self.rows*CELL), pygame.SRCALPHA)
            overlay.fill((0,0,0,120))
            self.screen.blit(overlay, (0,0))
            msg = self.big_font.render(f"Solved in {self.elapsed:.1f}s!", True, (80,240,80))
            sub = self.font.render("Press R for a new maze", True, (200,200,200))
            self.screen.blit(msg, (self.width//2 - msg.get_width()//2, self.rows*CELL//2 - 30))
            self.screen.blit(sub, (self.width//2 - sub.get_width()//2, self.rows*CELL//2 + 20))
            title = self.font.render("Leaderboard", True, (240, 220, 100))
            self.screen.blit(title, (self.width//2 - title.get_width()//2, self.rows*CELL//2 + 60))
            for index, score in enumerate(self.leaderboard):
                entry = self.font.render(f"{index + 1}. {score:.1f}s", True, (220,220,220))
                self.screen.blit(entry, (self.width//2 - entry.get_width()//2, self.rows*CELL//2 + 88 + index * 24))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

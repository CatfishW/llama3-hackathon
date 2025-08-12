# main.py
# ──────────────────────────────────────────────────────────────────────────────
import pygame, sys, os, json
from ui import ScreenManager, MainMenu, GameScreen, LeaderboardScreen, GameOverScreen

# where to store scores
ROOT_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
LEAD_FILE   = os.path.join(ROOT_DIR, "data", "leaderboard.json")
os.makedirs(os.path.dirname(LEAD_FILE), exist_ok=True)

def load_leaderboard():
    if not os.path.exists(LEAD_FILE):
        return []
    with open(LEAD_FILE, "r") as f:
        return json.load(f)

def save_score(name, score, germs):
    lb = load_leaderboard()
    lb.append({"name": name, "score": score, "germs": germs})
    lb = sorted(lb, key=lambda e: e["score"], reverse=True)[:10]
    with open(LEAD_FILE, "w") as f:
        json.dump(lb, f, indent=2)

def main():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("Red Blood Cell Maze")
    clock  = pygame.time.Clock()

    manager = ScreenManager()
    manager.add("menu",       MainMenu(manager))
    manager.add("game",       GameScreen(manager))
    from ui import RLGameScreen
    manager.add("rl_game",    RLGameScreen(manager))
    manager.add("leaderboard",LeaderboardScreen(manager, load_leaderboard))
    manager.add("game_over",  GameOverScreen(manager, save_score))
    manager.set("menu")

    while True:
        dt = clock.tick(60)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            manager.handle(ev)

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()

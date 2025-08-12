# ui.py
import textwrap
# ──────────────────────────────────────────────────────────────────────────────
import pygame, os, random, threading, json
import paho.mqtt.client as mqtt
from maze import Maze
from entities import Tile, Player, Oxygen, Germ
from rl_agent import DQNAgent
from rl_env import MazeEnv

# helper to load/scale or fallback to a colored rect
def load_image(path, size, fallback_color):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (size, size))
    except Exception:
        surf = pygame.Surface((size, size))
        surf.fill(fallback_color)
        return surf

class Button:
    def __init__(self, rect, text, callback, font):
        self.rect     = pygame.Rect(rect)
        self.text     = text
        self.callback = callback
        self.font     = font

    def draw(self, surf):
        pygame.draw.rect(surf, (50, 50, 50), self.rect)
        pygame.draw.rect(surf, (200,200,200), self.rect, 2)
        txt = self.font.render(self.text, True, (255,255,255))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
            self.callback()

class InputBox:
    def __init__(self, x, y, w, h, font, text=""):
        self.rect       = pygame.Rect(x, y, w, h)
        self.font       = font
        self.color_inactive = pygame.Color('gray50')
        self.color_active   = pygame.Color('dodgerblue2')
        self.color      = self.color_inactive
        self.text       = text
        self.txt_surf   = font.render(text, True, (255,255,255))
        self.active     = False

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            # toggle focus
            self.active = self.rect.collidepoint(ev.pos)
            self.color  = self.color_active if self.active else self.color_inactive
        if ev.type == pygame.KEYDOWN and self.active:
            if ev.key == pygame.K_RETURN:
                self.active = False
                self.color  = self.color_inactive
            elif ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += ev.unicode
            self.txt_surf = self.font.render(self.text, True, (255,255,255))

    def draw(self, surf):
        surf.blit(self.txt_surf, (self.rect.x+5, self.rect.y+5))
        pygame.draw.rect(surf, self.color, self.rect, 2)

    def get_text(self):
        return self.text

class Screen:
    def handle(self, ev): pass
    def update(self, dt): pass
    def draw(self, surf): pass

class MainMenu(Screen):
    def __init__(self, manager):
        self.manager = manager
        self.font    = pygame.font.SysFont(None, 32)
        midx, midy   = 320, 240
        bw, bh       = 200, 50

        # Germ count input
        self.germ_input = InputBox(midx+120, midy-35, 60, 40, self.font, text="5")
        self.germ_label = self.font.render("Germs:", True, (255,255,255))

        # Buttons
        self.buttons = [
            Button((midx-bw//2, midy-60, bw, bh), "Start Game", self.start_game, self.font),
            Button((midx-bw//2, midy+60, bw, bh), "RL Play", self.start_rl, self.font),
            Button((midx-bw//2, midy    , bw, bh), "Leaderboard", lambda: manager.set("leaderboard"), self.font),
            Button((midx-bw//2, midy+120, bw, bh), "Quit", lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)), self.font),
        ]

    def start_game(self):
        try:
            cnt = max(1, int(self.germ_input.get_text()))
        except:
            cnt = 5
        gs = self.manager.screens["game"]
        gs.start_new(germ_count=cnt)
        self.manager.set("game")

    def start_rl(self):
        try:
            cnt = max(1, int(self.germ_input.get_text()))
        except:
            cnt = 5
        rl_screen = self.manager.screens["rl_game"]
        rl_screen.start_new(germ_count=cnt, model_path="maze_dqn.pth")
        self.manager.set("rl_game")

    def handle(self, ev):
        self.germ_input.handle(ev)
        for b in self.buttons:
            b.handle(ev)

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((20,20,20))
        title = self.font.render("Red Blood Cell Maze", True, (255,100,100))
        surf.blit(title, title.get_rect(center=(320,100)))
        # germ input
        midy_minus_30 = 240 - 35
        surf.blit(self.germ_label, (320, midy_minus_30))
        self.germ_input.draw(surf)
        for b in self.buttons:
            b.draw(surf)

class MazeLAMHintReceiver:
    def __init__(self, session_id):
        self.session_id       = session_id
        self.hint             = ""
        self.path             = []    # new: path from LAM
        self.break_wall       = None  # new: wall to break
        self.breaks_remaining = 0     # new: breaks left

        self.client = mqtt.Client(client_id=f"maze-hint-{session_id}")
        self.client.username_pw_set("TangClinic", "Tang123")
        self.client.on_message = self.on_message
        self.client.connect("47.89.252.2", 1883, 60)
        print(f"[DEBUG] MQTT client connected for LAM session {session_id}")
        self.client.subscribe(f"maze/hint/{session_id}")
        threading.Thread(target=self.client.loop_forever, daemon=True).start()

    def on_message(self, client, userdata, msg):
        print(f"[DEBUG] MQTT message received on topic {msg.topic}: {msg.payload}")
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            print("[DEBUG] Failed to decode MQTT message payload")
            return
        self.hint             = data.get("hint", "")
        self.path             = data.get("path", [])
        self.break_wall       = tuple(data["break_wall"]) if "break_wall" in data else None
        self.breaks_remaining = data.get("breaks_remaining", self.breaks_remaining)

class GameScreen(Screen):
    def __init__(self, manager):
        self.manager      = manager
        self.font         = pygame.font.SysFont(None, 24)
        self.TILE_SIZE    = 32
        self.SCREEN_W     = 640
        self.SCREEN_H     = 480
        # asset paths
        a_dir           = os.path.join(os.path.dirname(__file__), "assets")
        self.paths      = {
            "wall":   os.path.join(a_dir, "tile_wall.png"),
            "floor":  os.path.join(a_dir, "tile_floor.png"),
            "player": os.path.join(a_dir, "red_blood_cell.png"),
            "oxy":    os.path.join(a_dir, "oxygen.png"),
            "germ":   os.path.join(a_dir, "germ.png"),
            "exit":   os.path.join(a_dir, "vessel.png"),
        }
        # preload images
        self.images = {
            k: load_image(p, self.TILE_SIZE if k!="oxy" else self.TILE_SIZE//2,
                         {"wall":(100,0,0),"floor":(200,50,50),
                          "player":(255,0,0),"oxy":(0,255,255),
                          "germ":(0,255,0),"exit":(50,50,200)}[k])
            for k, p in self.paths.items()
        }
        self.lam_hint_receiver = None
        self.lam_session_id    = None
        self._last_sent_player_pos = None  # Track last sent position
        self._last_sent_time = 0           # Track last sent time (ms)

        # LAM UI panel and toggle
        self.small = pygame.font.SysFont(None, 18)
        self.lam_panel = LAMUIPanel(self.small, x=self.SCREEN_W - 220, y=10, w=210, h=100)
        self.show_lam = True

    def start_new(self, germ_count=5):
        # generate
        cols = self.SCREEN_W // self.TILE_SIZE
        rows = self.SCREEN_H // self.TILE_SIZE
        #self.maze = Maze(cols, rows)
        self.maze = Maze(21,15)
        # sprite groups
        self.walls      = pygame.sprite.Group()
        self.floors     = pygame.sprite.Group()
        self.oxygens    = pygame.sprite.Group()
        self.germs      = pygame.sprite.Group()
        self.all_sprites= pygame.sprite.Group()

        # flatten floor cells for random placement
        floor_cells = []
        for y in range(rows):
            for x in range(cols):
                px, py = x*self.TILE_SIZE, y*self.TILE_SIZE
                if self.maze.grid[y][x] == 1:
                    t = Tile(self.images["wall"], px, py, passable=False)
                    self.walls.add(t); self.all_sprites.add(t)
                else:
                    t = Tile(self.images["floor"], px, py, passable=True)
                    self.floors.add(t); self.all_sprites.add(t)
                    floor_cells.append((x,y))

        # start & exit
        start = (1, 1)
        end   = (cols-2, rows-2)

        # Ensure start and its adjacent cells are passable
        self.maze.grid[start[1]][start[0]] = 0
        if start[1]+1 < len(self.maze.grid):
            self.maze.grid[start[1]+1][start[0]] = 0
        if start[0]+1 < len(self.maze.grid[0]):
            self.maze.grid[start[1]][start[0]+1] = 0
        if start[0]-1 >= 0:
            self.maze.grid[start[1]][start[0]-1] = 0
        if start[1]-1 >= 0:
            self.maze.grid[start[1]-1][start[0]] = 0

        # place player
        px, py = start[0]*self.TILE_SIZE, start[1]*self.TILE_SIZE
        self.player = Player(
            self.images["player"],
            (px, py),
            maze_cols=cols,
            maze_rows=rows,
            tile_size=self.TILE_SIZE
        )
        self.all_sprites.add(self.player)

        # place exit
        ex, ey = end
        self.exit_tile = Tile(self.images["exit"], ex*self.TILE_SIZE, ey*self.TILE_SIZE, passable=True)
        self.all_sprites.add(self.exit_tile)

        # oxygen pellets (~10% of floors)
        avail = [c for c in floor_cells if c not in (start, end)]
        ox_count = max(10, int(len(avail)*0.1))
        for x,y in random.sample(avail, min(ox_count, len(avail))):
            oxy = Oxygen(self.images["oxy"],
                         (x*self.TILE_SIZE + self.TILE_SIZE//2,
                          y*self.TILE_SIZE + self.TILE_SIZE//2))
            self.oxygens.add(oxy); self.all_sprites.add(oxy)

        # germs
        remaining = [c for c in avail if c not in [(x,y) for x,y in random.sample(avail,0)]]
        for x,y in random.sample(avail, min(germ_count, len(avail))):
            g = Germ(self.images["germ"], (x*self.TILE_SIZE, y*self.TILE_SIZE))
            self.germs.add(g); self.all_sprites.add(g)
        self.germ_count = germ_count

        # reset stats
        self.oxygen_count = 0
        self.start_ticks  = pygame.time.get_ticks()
        self.game_over    = False
        self.win          = False
        self._handled     = False

        # Setup LAM session and hint receiver
        import uuid
        self.lam_session_id   = f"maze-{uuid.uuid4().hex[:8]}"
        self.lam_hint_receiver = MazeLAMHintReceiver(self.lam_session_id)
        # Send initial state to LAM
        self.send_lam_state()

    def send_lam_state(self):
        player_pos = (self.player.rect.x // self.TILE_SIZE,
                      self.player.rect.y // self.TILE_SIZE)
        now = pygame.time.get_ticks()
        # Throttle: send if position changed and at least 500ms passed, or always every 10s
        min_interval = 10000  # ms
        max_interval = 30000  # ms
        last_time = getattr(self, '_last_sent_time', 0)
        last_pos = getattr(self, '_last_sent_player_pos', None)
        time_since = now - last_time
        should_send = False
        if player_pos != last_pos and time_since >= min_interval:
            should_send = True
        elif time_since >= max_interval:
            should_send = True
        if not should_send:
            return
        self._last_sent_player_pos = player_pos
        self._last_sent_time = now
        client = mqtt.Client()
        client.username_pw_set("TangClinic", "Tang123")
        client.connect("47.89.252.2", 1883, 60)
        print(f"[DEBUG] MQTT client connected for sending state (session {self.lam_session_id})")
        exit_pos   = (self.exit_tile.rect.x // self.TILE_SIZE,
                      self.exit_tile.rect.y // self.TILE_SIZE)
        state = {
            "sessionId":    self.lam_session_id,
            "player_pos":   player_pos,
            "exit_pos":     exit_pos,
            "visible_map":  self.maze.grid
        }
        client.publish("maze/state", json.dumps(state))
        print(f"[DEBUG] Published state to LAM: {state}")
        client.disconnect()

    def handle(self, ev):
        # all input in Player.update()
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_h:
            self.show_lam = not self.show_lam

    def update(self, dt):
        if not self.game_over:
            self.player.update(self.walls)
            for g in self.germs:
                g.speed = 2 + self.oxygen_count//5
                g.update(self.walls)

            # collect oxygen
            cols = pygame.sprite.spritecollide(self.player, self.oxygens, True)
            self.oxygen_count += len(cols)

            # hit?
            if pygame.sprite.spritecollideany(self.player, self.germs):
                self.game_over = True

            # reached exit?
            if self.player.rect.colliderect(self.exit_tile.rect):
                self.win = True
                self.game_over = True

        elif not self._handled:
            # finish and switch
            elapsed = (pygame.time.get_ticks() - self.start_ticks)/1000
            score   = self.oxygen_count*100 - int(elapsed*5)
            self.manager.set("game_over")
            self.manager.active.setup(score, self.win, self.germ_count)
            self._handled = True

        # After player moves, send state to LAM only if moved
        self.send_lam_state()

        # APPLY LAM ACTIONS
        self.apply_lam_actions()

    def apply_lam_actions(self):
        """Enact break_wall, cache path & breaks_remaining."""
        lam = self.lam_hint_receiver
        # Check break_wall format before using
        if lam.break_wall is not None:
            if isinstance(lam.break_wall, (tuple, list)) and len(lam.break_wall) == 2:
                self.break_wall_at(lam.break_wall)
            else:
                print(f"[WARN] Invalid break_wall format from LAM: {lam.break_wall}")
            lam.break_wall = None
        self.current_path   = lam.path
        self.current_breaks = lam.breaks_remaining

    def break_wall_at(self, coord):
        """Remove a wall tile at grid coord and add a floor tile."""
        # Defensive: check coord format
        if not (isinstance(coord, (tuple, list)) and len(coord) == 2):
            print(f"[WARN] break_wall_at called with invalid coord: {coord}")
            return
        x, y = coord
        self.maze.grid[y][x] = 0
        for sprite in list(self.walls):
            if sprite.rect.topleft == (x*self.TILE_SIZE, y*self.TILE_SIZE):
                self.walls.remove(sprite)
                self.all_sprites.remove(sprite)
                break
        floor_tile = Tile(
            self.images["floor"],
            x*self.TILE_SIZE, y*self.TILE_SIZE,
            passable=True
        )
        self.floors.add(floor_tile)
        self.all_sprites.add(floor_tile)

    def draw(self, surf):
        surf.fill((0,0,0))

        # 1) path-tile overlay
        if self.show_lam and hasattr(self, 'current_path'):
            for (x, y) in self.current_path:
                rect = pygame.Rect(x*self.TILE_SIZE, y*self.TILE_SIZE,
                                   self.TILE_SIZE, self.TILE_SIZE)
                overlay = pygame.Surface((self.TILE_SIZE, self.TILE_SIZE), pygame.SRCALPHA)
                overlay.fill((255, 255, 0, 80))
                surf.blit(overlay, rect.topleft)

        # 2) draw all game sprites (walls, floor, player, etc.)
        self.all_sprites.draw(surf)

        # 3) path line with arrowheads
        if self.show_lam and hasattr(self, 'current_path') and len(self.current_path) > 1:
            pts = [(
                x*self.TILE_SIZE + self.TILE_SIZE//2,
                y*self.TILE_SIZE + self.TILE_SIZE//2
            ) for x, y in self.current_path]
            pygame.draw.lines(surf, (255,230,0), False, pts, width=4)

            # draw a little arrow at the next step
            sx, sy = pts[0]
            ex, ey = pts[1]
            # compute a simple arrowhead
            angle = pygame.math.Vector2(ex-sx, ey-sy).angle_to((1,0))
            arrow = pygame.transform.rotate(pygame.Surface((10,4), pygame.SRCALPHA), -angle)
            pygame.draw.polygon(arrow, (255,230,0), [(0,0),(10,2),(0,4)])
            surf.blit(arrow, ((sx+ex)/2 - 5, (sy+ey)/2 - 2))

        # 4) draw HUD (score, O₂, etc.)
        elapsed = (pygame.time.get_ticks() - self.start_ticks)/1000
        score   = self.oxygen_count*100 - int(elapsed*5)
        hud     = self.font.render(
            f"O₂:{self.oxygen_count} Time:{elapsed:.1f}s Score:{score}",
            True, (255,255,255)
        )
        surf.blit(hud, (10,10))

        # 5) LAM panel
        if self.show_lam:
            self.lam_panel.draw(
                surf,
                hint=getattr(self.lam_hint_receiver, 'hint',''),
                breaks=getattr(self, 'current_breaks', 0),
                path=getattr(self, 'current_path', [])
            )
class LAMUIPanel:
    def __init__(self, font, x, y, w, h):
        self.font   = font
        self.rect   = pygame.Rect(x, y, w, h)
        self.bg     = pygame.Surface((w, h), pygame.SRCALPHA)
        self.bg.fill((20, 20, 20, 200))   # semi‑transparent
        self.padding = 8

    def draw(self, surf, hint, breaks, path):
        # background
        surf.blit(self.bg, self.rect.topleft)

        # wrap hint text
        lines = textwrap.wrap(hint or "No hint", width=25)
        y = self.rect.y + self.padding
        for line in lines:
            txt = self.font.render(line, True, (255, 230, 0))
            surf.blit(txt, (self.rect.x + self.padding, y))
            y += txt.get_height() + 2

        # breaks remaining
        br = self.font.render(f"Breaks: {breaks}", True, (255, 230, 0))
        surf.blit(br, (self.rect.x + self.padding, y))

        # optionally show next step of path
        if path:
            next_step = path[0]
            step_txt = self.font.render(f"Next → {next_step}", True, (200,200,200))
            surf.blit(step_txt, (self.rect.x + self.padding, y + br.get_height() + 4))

class LeaderboardScreen(Screen):
    def __init__(self, manager, load_func):
        self.manager   = manager
        self.load_func = load_func
        self.font      = pygame.font.SysFont(None, 32)
        self.small     = pygame.font.SysFont(None, 24)
        self.back_btn  = Button((10, 430, 100, 40), "Back", lambda: manager.set("menu"), self.font)
        self.scores    = []

    def handle(self, ev):
        self.back_btn.handle(ev)

    def update(self, dt):
        self.scores = self.load_func()

    def draw(self, surf):
        surf.fill((0,0,0))
        title = self.font.render("Leaderboard", True, (255,255,0))
        surf.blit(title, (260, 20))
        for i, entry in enumerate(self.scores):
            txt = self.small.render(f"{i+1}. {entry['name']} — {entry['score']}", True, (255,255,255))
            surf.blit(txt, (200, 80 + i*30))
        self.back_btn.draw(surf)

class GameOverScreen(Screen):
    def __init__(self, manager, save_func):
        self.manager    = manager
        self.save_func  = save_func
        self.font       = pygame.font.SysFont(None, 32)
        self.small      = pygame.font.SysFont(None, 24)
        self.input_box  = InputBox(270, 220, 200, 40, self.small)
        self.submit_btn = Button((270, 280, 200, 40), "Submit Score", self.on_submit, self.font)
        self.try_btn    = Button((140, 340, 150, 40), "Try Again",    self.on_try,    self.font)
        self.lead_btn   = Button((495, 340, 150, 40), "Leaderboard",  self.on_lead,   self.font)
        self.quit_btn   = Button((320, 400, 150, 40), "Quit to Menu", self.on_quit,   self.font)
        self.score      = 0
        self.win        = False
        self.submitted  = False
        self.germ_count = 0

    def setup(self, score, win, germ_count):
        self.score      = score
        self.win        = win
        self.submitted  = False
        self.input_box.text     = ""
        self.input_box.txt_surf = self.small.render("", True, (255,255,255))
        self.germ_count = germ_count

    def handle(self, ev):
        if not self.submitted:
            self.input_box.handle(ev)
            self.submit_btn.handle(ev)
        self.try_btn.handle(ev)
        self.lead_btn.handle(ev)
        self.quit_btn.handle(ev)

    def on_submit(self):
        name = self.input_box.get_text().strip() or "Anon"
        self.save_func(name, self.score, self.germ_count)
        self.submitted = True

    def on_try(self):
        gs = self.manager.screens["game"]
        gs.start_new(germ_count=self.germ_count)
        self.manager.set("game")

    def on_lead(self):
        self.manager.set("leaderboard")

    def on_quit(self):
        self.manager.set("menu")

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((0,0,0))
        msg = "You Win!" if self.win else "Game Over!"
        over = self.font.render(msg, True, (255,0,0))
        surf.blit(over, over.get_rect(center=(320,100)))
        scr = self.small.render(f"Your Score: {self.score}", True, (255,255,255))
        surf.blit(scr, (260,150))
        if not self.submitted:
            prompt = self.small.render("Enter Name:", True, (255,255,255))
            surf.blit(prompt, (260,190))
            self.input_box.draw(surf)
            self.submit_btn.draw(surf)
        else:
            done = self.small.render("Score Submitted!", True, (0,255,0))
            surf.blit(done, (280,250))
        self.try_btn.draw(surf)
        self.lead_btn.draw(surf)
        self.quit_btn.draw(surf)

class ScreenManager:
    """Simple screen stack."""
    def __init__(self):
        self.screens = {}
        self.active  = None

    def add(self, name, screen):
        self.screens[name] = screen

    def set(self, name):
        self.active = self.screens[name]

    def handle(self, ev):
        if self.active: self.active.handle(ev)

    def update(self, dt):
        if self.active: self.active.update(dt)

    def draw(self, surf):
        if self.active: self.active.draw(surf)
        if self.active: self.active.draw(surf)

class RLGameScreen(GameScreen):
    def __init__(self, manager):
        super().__init__(manager)
        self.agent = None
        self.env   = None

    def start_new(self, germ_count=5, model_path="maze_dqn.pth"):
        super().start_new(germ_count=germ_count)
        cols = self.SCREEN_W // self.TILE_SIZE
        rows = self.SCREEN_H // self.TILE_SIZE
        cols,rows = 21, 15  # fixed for RL
        self.env = MazeEnv(cols=cols, rows=rows, germ_count=germ_count)
        obs_dim = self.env.observation_space.shape[0]
        act_dim = self.env.action_space.n
        self.agent = DQNAgent(obs_dim, act_dim)
        self.agent.load(model_path)
        self.last_obs = self.env.reset()

    def update(self, dt):
        if not self.game_over:
            action = self.agent.select_action(self.last_obs, eval=True)
            obs, reward, done, _ = self.env.step(action)
            self.last_obs = obs
            dx, dy = {0:(0,-1),1:(0,1),2:(-1,0),3:(1,0)}[action]
            self.player._move(dx*self.player.speed, dy*self.player.speed, self.walls)
            for g in self.germs:
                g.speed = 2 + self.oxygen_count//5
                g.update(self.walls)
            cols = pygame.sprite.spritecollide(self.player, self.oxygens, True)
            self.oxygen_count += len(cols)
            if pygame.sprite.spritecollideany(self.player, self.germs):
                self.game_over = True
            if self.player.rect.colliderect(self.exit_tile.rect):
                self.win = True
                self.game_over = True
        super().update(dt)

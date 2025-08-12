# rl_env.py
import gym
import numpy as np
from maze import Maze

class MazeEnv(gym.Env):
    """
    Gym wrapper for your Maze + simple static germs/oxygen.
    Observation: [flattened grid (0=floor,1=wall),
                  player_x, player_y,
                  exit_x, exit_y,
                  oxygen_map (0/1)]
    Action space: 0=Up,1=Down,2=Left,3=Right
    Reward: +1 per oxygen, +10 for exit, -1 for death, -0.01 per step
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, cols=21, rows=15, germ_count=5, oxy_pct=0.1, max_steps=1000):
        super().__init__()
        self.cols, self.rows = cols, rows
        self.germ_count = germ_count
        self.oxy_pct    = oxy_pct
        self.max_steps  = max_steps

        # Action & observation spaces
        self.action_space = gym.spaces.Discrete(4)
        obs_dim = cols*rows + 4 + cols*rows  # grid + coords + oxy map
        self.observation_space = gym.spaces.Box(
            low=0, high=1, shape=(obs_dim,), dtype=np.float32
        )

        self.reset()

    def reset(self):
        # regenerate maze
        self.maze = Maze(self.cols, self.rows)
        # start & exit
        self.player = [1,1]
        self.exit   = [self.cols-2, self.rows-2]
        self.maze.grid[1][1] = 0
        self.maze.grid[self.exit[1]][self.exit[0]] = 0

        # place oxygen pellets (~oxy_pct of floors)
        floor = [(x,y) for y in range(self.rows)
                         for x in range(self.cols)
                         if self.maze.grid[y][x]==0
                         and (x,y) not in [tuple(self.player), tuple(self.exit)]]
        np.random.shuffle(floor)
        ox_count = max(1, int(len(floor)*self.oxy_pct))
        self.oxygens = set(floor[:ox_count])

        # place static germs (you can extend to moving germs)
        self.germs = set(floor[ox_count:ox_count+self.germ_count])

        self.steps = 0
        self.done  = False
        return self._get_obs()

    def _get_obs(self):
        flat = np.array(self.maze.grid).flatten()
        coords = np.array(self.player + self.exit)
        ox_map = np.zeros(self.cols*self.rows, dtype=np.float32)
        for (x,y) in self.oxygens:
            ox_map[y*self.cols + x] = 1.0
        return np.concatenate([flat, coords/np.array([self.cols,self.rows]*2), ox_map])

    def step(self, action):
        if self.done:
            return self._get_obs(), 0.0, True, {}

        self.steps += 1
        dx, dy = {0:(0,-1),1:(0,1),2:(-1,0),3:(1,0)}[action]
        nx, ny = self.player[0]+dx, self.player[1]+dy
        # wall collision
        if 0 <= nx < self.cols and 0 <= ny < self.rows and self.maze.grid[ny][nx]==0:
            self.player = [nx, ny]

        reward = -0.01
        # collect oxygen
        if tuple(self.player) in self.oxygens:
            reward += 1.0
            self.oxygens.remove(tuple(self.player))

        # germ collision = death
        if tuple(self.player) in self.germs:
            reward -= 1.0
            self.done = True

        # exit
        if self.player == self.exit:
            reward += 10.0
            self.done = True

        if self.steps >= self.max_steps:
            self.done = True

        return self._get_obs(), reward, self.done, {}

    def render(self, mode='human'):
        # optionally hook into your pygame draw code
        pass

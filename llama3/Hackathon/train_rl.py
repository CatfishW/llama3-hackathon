# train_rl.py
import argparse
from rl_env import MazeEnv
from rl_agent import DQNAgent
import numpy as np

def train(args):
    env = MazeEnv(
        cols=args.cols,
        rows=args.rows,
        germ_count=args.germs,
        oxy_pct=args.oxy_pct,
        max_steps=args.max_steps
    )
    agent = DQNAgent(
        input_dim=env.observation_space.shape[0],
        action_dim=env.action_space.n,
        lr=args.lr,
        gamma=args.gamma
    )

    for ep in range(1, args.episodes+1):
        s = env.reset()
        total_r = 0
        done = False
        while not done:
            a = agent.select_action(s)
            s2, r, done, _ = env.step(a)
            agent.store(s,a,r,s2,done)
            agent.update()
            s = s2
            total_r += r

        if ep % args.log_interval == 0:
            print(f"Episode {ep}/{args.episodes} — Return: {total_r:.2f} eps: {agent.epsilon:.3f}")
        if ep % args.save_interval == 0:
            agent.save(args.model_path)

    # final save
    agent.save(args.model_path)
    print("Training complete. Model saved to", args.model_path)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cols", type=int, default=21)
    p.add_argument("--rows", type=int, default=15)
    p.add_argument("--germs", type=int, default=5)
    p.add_argument("--oxy_pct", type=float, default=0.1)
    p.add_argument("--max_steps", type=int, default=1000)
    p.add_argument("--episodes", type=int, default=1000)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--log_interval", type=int, default=50)
    p.add_argument("--save_interval", type=int, default=50)
    p.add_argument("--model_path", type=str, default="maze_dqn.pth")
    args = p.parse_args()
    train(args)

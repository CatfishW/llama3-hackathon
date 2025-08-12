# rl_agent.py
import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim)
        )
    def forward(self, x):
        return self.net(x)

class DQNAgent:
    def __init__(
        self,
        input_dim,
        action_dim,
        lr=1e-3,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.1,
        epsilon_decay=100000,
        buffer_size=100000,
        batch_size=64,
        target_update=1000
    ):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_net      = QNetwork(input_dim, action_dim).to(self.device)
        self.target_net = QNetwork(input_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.optim      = optim.Adam(self.q_net.parameters(), lr=lr)

        self.gamma       = gamma
        self.epsilon     = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_dec = (epsilon_start - epsilon_end) / epsilon_decay
        self.step_count  = 0
        self.target_update = target_update

        self.buffer = deque(maxlen=buffer_size)
        self.batch_size = batch_size

    def select_action(self, state, eval=False):
        self.step_count += 1
        if (not eval) and random.random() < self.epsilon:
            return random.randrange(self.q_net.net[-1].out_features)
        with torch.no_grad():
            st = torch.FloatTensor(state).to(self.device).unsqueeze(0)
            qs = self.q_net(st)
            return int(qs.argmax().item())

    def store(self, s,a,r,s2,done):
        self.buffer.append((s,a,r,s2,done))

    def update(self):
        if len(self.buffer) < self.batch_size:
            return
        batch = random.sample(self.buffer, self.batch_size)
        s,a,r,s2,d = zip(*batch)
        s  = torch.FloatTensor(s).to(self.device)
        a  = torch.LongTensor(a).unsqueeze(1).to(self.device)
        r  = torch.FloatTensor(r).unsqueeze(1).to(self.device)
        s2 = torch.FloatTensor(s2).to(self.device)
        d  = torch.FloatTensor(d).unsqueeze(1).to(self.device)

        q_values    = self.q_net(s).gather(1,a)
        next_q      = self.target_net(s2).max(1,keepdim=True)[0]
        target      = r + self.gamma * next_q * (1-d)
        loss        = nn.functional.mse_loss(q_values, target)

        self.optim.zero_grad()
        loss.backward()
        self.optim.step()

        # epsilon decay
        if self.epsilon > self.epsilon_end:
            self.epsilon -= self.epsilon_dec

        # target network update
        if self.step_count % self.target_update == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())

    def save(self, path):
        torch.save(self.q_net.state_dict(), path)

    def load(self, path):
        self.q_net.load_state_dict(torch.load(path, map_location=self.device))
        self.target_net.load_state_dict(self.q_net.state_dict())

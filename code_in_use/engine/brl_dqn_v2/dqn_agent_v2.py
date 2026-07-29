from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class DQNV2Config:
    state_dim: int
    action_dim: int = 4
    hidden_dim: int = 128
    lr: float = 3.0e-4
    gamma: float = 0.99
    batch_size: int = 128
    buffer_size: int = 100_000
    min_buffer_size: int = 1_000
    target_update_freq: int = 250
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995
    max_grad_norm: float = 1.0


class QNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ReplayBufferV2:
    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done, next_mask):
        self.buffer.append((state, action, reward, next_state, done, next_mask))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones, next_masks = zip(*batch)
        return (
            np.stack(states),
            np.asarray(actions, dtype=np.int64),
            np.asarray(rewards, dtype=np.float32),
            np.stack(next_states),
            np.asarray(dones, dtype=np.float32),
            np.stack(next_masks).astype(bool),
        )

    def __len__(self) -> int:
        return len(self.buffer)


class DQNV2Agent:
    def __init__(self, config: DQNV2Config, device: str = "cpu"):
        self.config = config
        self.device = torch.device(device)
        self.policy_net = QNetwork(config.state_dim, config.action_dim, config.hidden_dim).to(self.device)
        self.target_net = QNetwork(config.state_dim, config.action_dim, config.hidden_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=config.lr)
        self.replay = ReplayBufferV2(config.buffer_size)
        self.epsilon = config.epsilon_start
        self.train_steps = 0

    def _mask_q(self, q: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        masked = q.clone()
        masked[~mask] = -1.0e9
        return masked

    def select_actions_batch(self, states: np.ndarray, masks: np.ndarray, greedy: bool = False) -> np.ndarray:
        masks = np.asarray(masks, dtype=bool)
        with torch.no_grad():
            states_t = torch.as_tensor(states, dtype=torch.float32, device=self.device)
            masks_t = torch.as_tensor(masks, dtype=torch.bool, device=self.device)
            q = self._mask_q(self.policy_net(states_t), masks_t)
            greedy_actions = torch.argmax(q, dim=1).cpu().numpy().astype(np.int64)
        if greedy:
            return greedy_actions
        random_draw = np.random.random(states.shape[0]) < self.epsilon
        random_actions = greedy_actions.copy()
        for i in np.where(random_draw)[0]:
            valid = np.flatnonzero(masks[i])
            if valid.size == 0:
                valid = np.arange(self.config.action_dim)
            random_actions[i] = int(np.random.choice(valid))
        return np.where(random_draw, random_actions, greedy_actions).astype(np.int64)

    def q_values_batch(self, states: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            states_t = torch.as_tensor(states, dtype=torch.float32, device=self.device)
            return self.policy_net(states_t).cpu().numpy().astype(np.float32)

    def store_transition(self, state, action, reward, next_state, done, next_mask):
        self.replay.push(state, action, reward, next_state, done, next_mask)

    def update(self) -> dict[str, float]:
        if len(self.replay) < max(self.config.batch_size, self.config.min_buffer_size):
            return {}
        states, actions, rewards, next_states, dones, next_masks = self.replay.sample(self.config.batch_size)
        states_t = torch.as_tensor(states, dtype=torch.float32, device=self.device)
        actions_t = torch.as_tensor(actions, dtype=torch.int64, device=self.device).unsqueeze(1)
        rewards_t = torch.as_tensor(rewards, dtype=torch.float32, device=self.device)
        next_states_t = torch.as_tensor(next_states, dtype=torch.float32, device=self.device)
        dones_t = torch.as_tensor(dones, dtype=torch.float32, device=self.device)
        next_masks_t = torch.as_tensor(next_masks, dtype=torch.bool, device=self.device)

        q_values = self.policy_net(states_t).gather(1, actions_t).squeeze(1)
        with torch.no_grad():
            next_q_all = self._mask_q(self.target_net(next_states_t), next_masks_t)
            next_q = next_q_all.max(dim=1).values
            target = rewards_t + self.config.gamma * (1.0 - dones_t) * next_q

        loss = F.mse_loss(q_values, target)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.config.max_grad_norm)
        self.optimizer.step()

        self.train_steps += 1
        if self.train_steps % self.config.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        return {"loss": float(loss.item()), "epsilon": float(self.epsilon)}

    def end_episode(self):
        self.epsilon = max(self.config.epsilon_end, self.epsilon * self.config.epsilon_decay)


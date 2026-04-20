import logging
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from datetime import datetime, timezone
from .persistence import load_torch, model_file, save_torch

logger = logging.getLogger(__name__)


class Actor(nn.Module):
    def __init__(self, n_inputs, n_actions):
        super(Actor, self).__init__()
        self.actor = nn.Sequential(
            nn.Linear(n_inputs, 64), nn.ReLU(),
            nn.Linear(64, 64),       nn.ReLU(),
            nn.Linear(64, n_actions),
        )

    def forward(self, x):
        return self.actor(x)


class Critic(nn.Module):
    def __init__(self, n_inputs):
        super(Critic, self).__init__()
        self.critic = nn.Sequential(
            nn.Linear(n_inputs, 64), nn.ReLU(),
            nn.Linear(64, 64),       nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.critic(x)


class PPOObject:
    def __init__(self):
        self.history = {}
        self.actor_model = None
        self.critic_model = None
        self.actor_optimizer = None
        self.critic_optimizer = None
        self.input_size = None
        self.actor_learning_rate = 3e-4
        self.critic_learning_rate = 1e-3
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("ppo", ".pt")
        self.load()

    def ensure_initialized(self, n_inputs):
        if self.actor_model is not None:
            return
        self.input_size = n_inputs
        self.actor_model = Actor(n_inputs, n_actions=2)
        self.critic_model = Critic(n_inputs)
        self.actor_optimizer = optim.Adam(self.actor_model.parameters(), lr=self.actor_learning_rate)
        self.critic_optimizer = optim.Adam(self.critic_model.parameters(), lr=self.critic_learning_rate)

    def record(self, image_id, state, action):
        self.ensure_initialized(len(state))
        self.history[image_id] = (state, action)

    def save(self):
        if self.actor_model is None or self.critic_model is None:
            return
        self.last_updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_torch(
            self.checkpoint_path,
            {
                "input_size":                  self.input_size,
                "actor_learning_rate":         self.actor_learning_rate,
                "critic_learning_rate":        self.critic_learning_rate,
                "update_count":                self.update_count,
                "last_reward":                 self.last_reward,
                "last_updated_at":             self.last_updated_at,
                "actor_state_dict":            self.actor_model.state_dict(),
                "critic_state_dict":           self.critic_model.state_dict(),
                "actor_optimizer_state_dict":  self.actor_optimizer.state_dict(),
                "critic_optimizer_state_dict": self.critic_optimizer.state_dict(),
            },
        )

    def load(self):
        checkpoint = load_torch(self.checkpoint_path)
        if checkpoint is None:
            return
        self.actor_learning_rate  = checkpoint.get("actor_learning_rate",  self.actor_learning_rate)
        self.critic_learning_rate = checkpoint.get("critic_learning_rate", self.critic_learning_rate)
        self.update_count         = checkpoint.get("update_count",         self.update_count)
        self.last_reward          = checkpoint.get("last_reward",          self.last_reward)
        self.last_updated_at      = checkpoint.get("last_updated_at",      self.last_updated_at)
        self.ensure_initialized(checkpoint["input_size"])
        self.actor_model.load_state_dict(checkpoint["actor_state_dict"])
        self.critic_model.load_state_dict(checkpoint["critic_state_dict"])
        self.actor_optimizer.load_state_dict(checkpoint["actor_optimizer_state_dict"])
        self.critic_optimizer.load_state_dict(checkpoint["critic_optimizer_state_dict"])

    def update(self, image_id, reward):
        if image_id not in self.history:
            logger.warning("image_id %s not found in history", image_id)
            return

        state, action = self.history[image_id]
        state_tensor  = torch.from_numpy(np.array(state)).float()
        action_tensor = torch.tensor(action, dtype=torch.long)
        reward_tensor = torch.tensor(float(reward))

        # enable_grad required: image_preprocessing disables gradients globally
        with torch.enable_grad():
            logits    = self.actor_model(state_tensor)
            m         = torch.distributions.Categorical(logits=logits)
            value     = self.critic_model(state_tensor)
            entropy   = m.entropy()
            advantage = (reward_tensor - value.detach()).squeeze()

            actor_loss  = -(m.log_prob(action_tensor) * advantage) - 0.0005 * entropy
            critic_loss = F.mse_loss(value.squeeze(), reward_tensor)

            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()

            self.critic_optimizer.zero_grad()
            critic_loss.backward()
            self.critic_optimizer.step()

        del self.history[image_id]
        self.update_count += 1
        self.last_reward = reward
        self.save()
        logger.debug("PPO updated | image=%s reward=%s", image_id, reward)


ppo_object = PPOObject()

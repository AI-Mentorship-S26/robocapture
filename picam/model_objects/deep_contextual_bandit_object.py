import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime, timezone
from .persistence import load_torch, model_file, save_torch

logger = logging.getLogger(__name__)

STATE_SIZE = 1287
ACTION_SIZE = 2


class QNetwork(nn.Module):
    def __init__(self, state_size, n_actions):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, 64), nn.ReLU(),
            nn.Linear(64, 32),         nn.ReLU(),
            nn.Linear(32, n_actions),
        )

    def forward(self, x):
        return self.net(x)


class DeepContextualBanditObject:
    def __init__(self):
        self.history = {}
        self.state_size = STATE_SIZE
        self.n_actions = ACTION_SIZE
        self.epsilon = 0.5
        self.epsilon_decay = 0.999
        self.epsilon_min = 0.05
        self.learning_rate = 0.001
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("deep_contextual_bandit", ".pt")
        self.network = QNetwork(self.state_size, self.n_actions)
        self.optimizer = optim.Adam(self.network.parameters(), lr=self.learning_rate)
        self.loss_fn = nn.MSELoss()
        self.load()

    def normalize_state(self, state):
        state_array = np.array(state)
        metrics   = state_array[:7]
        embedding = state_array[7:]
        metrics_norm   = (metrics   - np.mean(metrics))   / (np.std(metrics)   + 1e-8)
        embedding_norm = (embedding - np.mean(embedding)) / (np.std(embedding) + 1e-8)
        return np.concatenate([metrics_norm, embedding_norm])

    def predict(self, state):
        state_tensor = torch.FloatTensor(self.normalize_state(state)).unsqueeze(0)
        with torch.no_grad():
            q_values = self.network(state_tensor)
        return q_values.squeeze().numpy()

    def choose_action(self, state):
        q_values = self.predict(state)
        if np.random.random() < self.epsilon:
            return np.random.randint(0, 2)
        return int(np.argmax(q_values))

    def record(self, image_id, state, action):
        self.history[image_id] = (state, action)

    def save(self):
        self.last_updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_torch(
            self.checkpoint_path,
            {
                "state_size":          self.state_size,
                "n_actions":           self.n_actions,
                "learning_rate":       self.learning_rate,
                "epsilon":             self.epsilon,
                "epsilon_decay":       self.epsilon_decay,
                "epsilon_min":         self.epsilon_min,
                "update_count":        self.update_count,
                "last_reward":         self.last_reward,
                "last_updated_at":     self.last_updated_at,
                "network_state_dict":  self.network.state_dict(),
                "optimizer_state_dict":self.optimizer.state_dict(),
            },
        )

    def load(self):
        checkpoint = load_torch(self.checkpoint_path)
        if checkpoint is None:
            return
        self.state_size    = checkpoint.get("state_size",    self.state_size)
        self.n_actions     = checkpoint.get("n_actions",     self.n_actions)
        self.learning_rate = checkpoint.get("learning_rate", self.learning_rate)
        self.epsilon       = checkpoint.get("epsilon",       self.epsilon)
        self.epsilon_decay = checkpoint.get("epsilon_decay", self.epsilon_decay)
        self.epsilon_min   = checkpoint.get("epsilon_min",   self.epsilon_min)
        self.update_count  = checkpoint.get("update_count",  self.update_count)
        self.last_reward   = checkpoint.get("last_reward",   self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)
        self.network = QNetwork(self.state_size, self.n_actions)
        self.optimizer = optim.Adam(self.network.parameters(), lr=self.learning_rate)
        self.network.load_state_dict(checkpoint["network_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    def update(self, image_id, reward):
        if image_id not in self.history:
            logger.warning("image_id %s not found in history", image_id)
            return

        state, action = self.history[image_id]
        state_tensor = torch.FloatTensor(self.normalize_state(state)).unsqueeze(0)

        q_values = self.network(state_tensor)
        target = q_values.detach().clone()
        target[0][action] = float(reward)

        self.optimizer.zero_grad()
        loss = self.loss_fn(q_values, target)
        loss.backward()
        self.optimizer.step()

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.update_count += 1
        self.last_reward = reward
        del self.history[image_id]
        self.save()
        logger.debug(
            "DCB updated | image=%s action=%d reward=%s loss=%.4f epsilon=%.4f",
            image_id, action, reward, loss.item(), self.epsilon,
        )


<<<<<<< Updated upstream
# Single instance
deep_contextual_bandit_object = DeepContextualBanditObject()
=======
deep_contextual_bandit_object = DeepContextualBanditObject()
>>>>>>> Stashed changes

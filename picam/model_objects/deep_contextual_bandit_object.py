import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime

from .persistence import load_torch, model_file, save_torch


STATE_SIZE = 1287
ACTION_SIZE = 2

class QNetwork(nn.Module):
    """Small neural network to approximate Q values"""
    def __init__(self, state_size, n_actions):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, n_actions)
        )

    def forward(self, x):
        return self.net(x)


class DeepContextualBanditObject:
    def __init__(self):
        self.history = {}  # {image_id: (state, action)}

        self.state_size = STATE_SIZE
        self.n_actions = ACTION_SIZE
        self.epsilon = 0.5          # start with high exploration
        self.epsilon_decay = 0.999  # decay slowly
        self.epsilon_min = 0.05     # never go below 5% exploration
        self.learning_rate = 0.001
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("deep_contextual_bandit", ".pt")

        # Neural network to approximate Q values
        self.network = QNetwork(self.state_size, self.n_actions)
        self.optimizer = optim.Adam(self.network.parameters(), lr=self.learning_rate)
        self.loss_fn = nn.MSELoss()
        self.load()

    def normalize_state(self, state):
        """Normalize metrics and embedding separately"""
        state_array = np.array(state)
        metrics = state_array[:7]
        embedding = state_array[7:]

        metrics_norm = (metrics - np.mean(metrics)) / (np.std(metrics) + 1e-8)
        embedding_norm = (embedding - np.mean(embedding)) / (np.std(embedding) + 1e-8)

        return np.concatenate([metrics_norm, embedding_norm])

    def predict(self, state):
        """Predict Q values for each action using neural network"""
        state_array = self.normalize_state(state)
        state_tensor = torch.FloatTensor(state_array).unsqueeze(0)

        with torch.no_grad():
            q_values = self.network(state_tensor)

        return q_values.squeeze().numpy()

    def choose_action(self, state):
        """Epsilon-greedy action selection"""
        q_values = self.predict(state)

        print(f"Q values: {q_values}")
        print(f"Epsilon: {self.epsilon:.4f}")

        # Epsilon-greedy
        x = np.random.random()
        print("EPSILON VALUE IN EPSILON-GREEDY:", x)

        if x < self.epsilon:
            chosenValue = np.random.randint(0, 2)
            print(f"ok we are doing random (explore), value is {chosenValue}")
        else:
            chosenValue = int(np.argmax(q_values))
            print(f"ok we are doing exploit, value is {chosenValue}")
        return chosenValue

    def record(self, image_id, state, action):
        """Store state/action for this image"""
        self.history[image_id] = (state, action)

    def save(self):
        self.last_updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        save_torch(
            self.checkpoint_path,
            {
                "state_size": self.state_size,
                "n_actions": self.n_actions,
                "learning_rate": self.learning_rate,
                "epsilon": self.epsilon,
                "epsilon_decay": self.epsilon_decay,
                "epsilon_min": self.epsilon_min,
                "update_count": self.update_count,
                "last_reward": self.last_reward,
                "last_updated_at": self.last_updated_at,
                "network_state_dict": self.network.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
            },
        )

    def load(self):
        checkpoint = load_torch(self.checkpoint_path)
        if checkpoint is None:
            return

        checkpoint_state_size = checkpoint.get("state_size", self.state_size)
        checkpoint_n_actions = checkpoint.get("n_actions", self.n_actions)

        self.state_size = checkpoint_state_size
        self.n_actions = checkpoint_n_actions
        self.learning_rate = checkpoint.get("learning_rate", self.learning_rate)
        self.epsilon = checkpoint.get("epsilon", self.epsilon)
        self.epsilon_decay = checkpoint.get("epsilon_decay", self.epsilon_decay)
        self.epsilon_min = checkpoint.get("epsilon_min", self.epsilon_min)
        self.update_count = checkpoint.get("update_count", self.update_count)
        self.last_reward = checkpoint.get("last_reward", self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)

        self.network = QNetwork(self.state_size, self.n_actions)
        self.optimizer = optim.Adam(self.network.parameters(), lr=self.learning_rate)
        self.network.load_state_dict(checkpoint["network_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    def update(self, image_id, reward):
        """Update neural network when reward/punishment comes back"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return

        state, action = self.history[image_id]
        state_array = self.normalize_state(state)
        state_tensor = torch.FloatTensor(state_array).unsqueeze(0)

        # Get current Q value predictions
        q_values = self.network(state_tensor)

        # Build target using detached q_values, then update the action taken
        target = q_values.detach().clone()
        target[0][action] = float(reward)

        # Backpropagate — q_values still has grad, target is detached
        self.optimizer.zero_grad()
        loss = self.loss_fn(q_values, target)
        loss.backward()
        self.optimizer.step()

        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.update_count += 1
        self.last_reward = reward
        del self.history[image_id]
        self.save()

        print(f"Updated network for action {action} with reward {reward}")
        print(f"Loss: {loss.item():.4f} | Epsilon: {self.epsilon:.4f}")


# Single instance
deep_contextual_bandit_object = DeepContextualBanditObject()

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

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
        
        self.state_size = 1287
        self.n_actions = 2
        self.epsilon = 0.5          # start with high exploration
        self.epsilon_decay = 0.999  # decay slowly
        self.epsilon_min = 0.05     # never go below 5% exploration
        self.learning_rate = 0.001

        # Neural network to approximate Q values
        self.network = QNetwork(self.state_size, self.n_actions)
        self.optimizer = optim.Adam(self.network.parameters(), lr=self.learning_rate)
        self.loss_fn = nn.MSELoss()

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
        if np.random.random() < self.epsilon:
            return np.random.randint(0, 2)
        else:
            return int(np.argmax(q_values))

    def record(self, image_id, state, action):
        """Store state/action for this image"""
        self.history[image_id] = (state, action)

    def update(self, image_id, reward):
        """Update neural network when reward/punishment comes back"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return

        state, action = self.history[image_id]
        state_array = self.normalize_state(state)
        state_tensor = torch.FloatTensor(state_array).unsqueeze(0)

        # Forward pass with gradients enabled
        self.network.train()
        self.optimizer.zero_grad()
        
        q_values = self.network(state_tensor)
        
        # Only compute loss for the action that was taken
        predicted = q_values[0][action]
        target = torch.tensor(float(reward))
        
        # Simple MSE loss on just the action taken
        loss = (predicted - target) ** 2
        loss.backward()
        self.optimizer.step()
        
        self.network.eval()

        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        print(f"Updated network for action {action} with reward {reward}")
        print(f"Loss: {loss.item():.4f} | Epsilon: {self.epsilon:.4f}")
        
# Single instance
deep_contextual_bandit_object = DeepContextualBanditObject()
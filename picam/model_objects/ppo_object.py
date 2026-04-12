import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from datetime import datetime


class Actor(nn.Module):
    def __init__(self, n_inputs, n_actions):
        super(Actor, self).__init__()
        
        self.actor = nn.Sequential(
            nn.Linear(n_inputs, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, n_actions),
        )
    
    def forward(self, x):
        return self.actor(x)


class Critic(nn.Module):
    def __init__(self, n_inputs):
        super(Critic, self).__init__()
        
        self.critic = nn.Sequential(
            nn.Linear(n_inputs, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
    
    def forward(self, x):
        return self.critic(x)


class PPOObject:
    def __init__(self):
        self.history = {}  # {image_id: (state, action)}
        
        self.actor_model = None
        self.critic_model = None
        self.actor_optimizer = None
        self.critic_optimizer = None
    
    def record(self, image_id, state, action):
        """Called by run_ppo() to store state/action for this image"""
        
        # Initialize networks on first call
        if self.actor_model is None:
            n_inputs = len(state)
            self.actor_model = Actor(n_inputs, n_actions=2)
            self.critic_model = Critic(n_inputs)
            self.actor_optimizer = optim.Adam(self.actor_model.parameters(), lr=3e-4)
            self.critic_optimizer = optim.Adam(self.critic_model.parameters(), lr=1e-3)
        
        self.history[image_id] = (state, action)
    
    def update(self, image_id, reward):
        """Called by update_ppo() when reward/punishment comes back from frontend"""
        
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state, action = self.history[image_id]
        
        # Convert to tensors
        state_tensor = torch.from_numpy(np.array(state)).float()
        action_tensor = torch.tensor(action)
        
        # Forward pass through both networks
        logits = self.actor_model(state_tensor)
        m = torch.distributions.Categorical(logits=logits)
        value = self.critic_model(state_tensor)
        
        # Compute entropy for exploration bonus
        entropy = m.entropy()
        
        # Policy gradient update
        # Advantage = reward - baseline (value estimate)
        advantage = reward - value.detach()
        
        # Actor loss: maximize log_prob(action) * advantage
        actor_loss = -m.log_prob(action_tensor) * advantage - 0.0005 * entropy
        
        # Critic loss: minimize (value - reward)^2
        critic_loss = F.mse_loss(value.squeeze(), torch.tensor(float(reward)))
        
        # Update actor
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()
        
        # Update critic
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        print(f"Updating model with reward {reward} for image {image_id}")


# Single instance — this is the model's brain
ppo_object = PPOObject()

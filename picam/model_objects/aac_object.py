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
            nn.Linear(n_inputs, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, n_actions),
        )
 
    def forward(self, x):
        return self.actor(x)


class Critic(nn.Module):
    def __init__(self, n_inputs):
        super(Critic, self).__init__()
 
        self.critic = nn.Sequential(
            nn.Linear(n_inputs, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
 
    def forward(self, x):
        return self.critic(x)


class SARSAObject:  # rename per model e.g. DQNObject, PPOObject etc.
    def __init__(self):
        self.history = {} 
        
        self.actor_model = None
        self.critic_model = None
        self.actor_optimizer = None
        self.critic_optimizer = None
    
    def record(self, image_id, state, action):

        if self.actor_model is None:
            n_inputs = len(state)
            self.actor_model      = Actor(n_inputs, n_actions=2)
            self.critic_model     = Critic(n_inputs)
            self.actor_optimizer  = optim.Adam(self.actor_model.parameters(), lr=6e-5)
            self.critic_optimizer = optim.Adam(self.critic_model.parameters(), lr=6e-5)

        self.history[image_id] = (state, action)
    
    def update(self, image_id, reward):
        """Called by update_sarsa() from pi_server when reward/punishment comes back from frontend"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state, action = self.history[image_id]
        

        state_tensor = torch.from_numpy(np.array(state)).float()
        action = torch.tensor(action)
 
        logits = self.actor_model(state_tensor)
 
        m = torch.distributions.Categorical(logits=logits)
 
        value = self.critic_model(state_tensor)
 
        entropy = m.entropy()

        reward_with_bonus = reward + (0.0005 * entropy.detach())
 
        td_target = reward_with_bonus
        advantage = td_target - value
 
        actor_loss = -m.log_prob(action) * advantage.detach() - (0.0005 * entropy)
        critic_loss = F.mse_loss(value.squeeze(), td_target.squeeze().detach())
 
        self.actor_optimizer.zero_grad()
        self.critic_optimizer.zero_grad()
 
        actor_loss.backward()
        self.actor_optimizer.step()
 
        critic_loss.backward()
        self.critic_optimizer.step()
        
        print(f"Updating model with reward {reward} for image {image_id}")

# Single instance — this is the model's brain
sarsa_object = SARSAObject()  # rename per model

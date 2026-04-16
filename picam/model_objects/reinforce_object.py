import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from datetime import datetime

from .persistence import load_torch, model_file, save_torch

STATE_SIZE = 1287


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


class ReinforceObject:
    def __init__(self):
        self.history = {}  # {image_id: (state, action, log_prob)}
        self.actor_model = None
        self.optimizer = None
        self.gamma = 0.99  # discount factor
        self.learning_rate = 1e-4
        self.input_size = None
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("reinforce", ".pt")

        self.ensure_initialized(STATE_SIZE)
        self.load()

    def ensure_initialized(self, n_inputs):
        if self.actor_model is not None:
            return

        self.input_size = n_inputs
        self.actor_model = Actor(n_inputs, n_actions=2)
        self.optimizer = optim.Adam(self.actor_model.parameters(), lr=self.learning_rate)
    
    def record(self, image_id, state, action):
        """Called by run_reinforce() from pi_server to store state/action for this image"""
        self.ensure_initialized(len(state))

        # Store the action and state for later update
        self.history[image_id] = {
            'state': state,
            'action': action
        }

    def save(self):
        if self.actor_model is None:
            return

        self.last_updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        save_torch(
            self.checkpoint_path,
            {
                "input_size": self.input_size,
                "learning_rate": self.learning_rate,
                "gamma": self.gamma,
                "update_count": self.update_count,
                "last_reward": self.last_reward,
                "last_updated_at": self.last_updated_at,
                "actor_state_dict": self.actor_model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
            },
        )

    def load(self):
        checkpoint = load_torch(self.checkpoint_path)
        if checkpoint is None:
            return

        self.learning_rate = checkpoint.get("learning_rate", self.learning_rate)
        self.gamma = checkpoint.get("gamma", self.gamma)
        self.update_count = checkpoint.get("update_count", self.update_count)
        self.last_reward = checkpoint.get("last_reward", self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)
        self.ensure_initialized(checkpoint["input_size"])
        self.actor_model.load_state_dict(checkpoint["actor_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    
    def update(self, image_id, reward):
        """Called by update_reinforce() when reward/punishment comes back from frontend"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state = self.history[image_id]['state']
        action = self.history[image_id]['action']
        
        # Convert to tensors
        state_tensor = torch.from_numpy(np.array(state)).float()
        action_tensor = torch.tensor(action, dtype=torch.long)
        
        # Forward pass through actor
        logits = self.actor_model(state_tensor)
        m = torch.distributions.Categorical(logits=logits)
        log_prob = m.log_prob(action_tensor)
        
        # REINFORCE policy gradient: -log_prob * reward
        policy_loss = -log_prob * reward
        
        # Update actor
        self.optimizer.zero_grad()
        policy_loss.backward()
        self.optimizer.step()

        self.update_count += 1
        self.last_reward = reward
        
        # Clean up history
        del self.history[image_id]
        self.save()
        
        print(f"REINFORCE update: image_id={image_id}, reward={reward}, loss={policy_loss.item():.4f}")


# Single instance — this is the model's brain
reinforce_object = ReinforceObject()

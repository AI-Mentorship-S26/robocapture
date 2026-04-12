import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from datetime import datetime

class SARSAObject:  # rename per model e.g. DQNObject, PPOObject etc.
    def __init__(self):
        self.history = {}  # {image_id: (state, action, log_prob)}
        self.actor_model = None
        self.optimizer = None
        self.gamma = 0.99  # discount factor
        self.learning_rate = 1e-4
    
    def record(self, image_id, state, action):
        """Called by run_reinforce() from pi_server to store state/action for this image"""
        if self.actor_model is None:
            n_inputs = len(state)
            self.actor_model = Actor(n_inputs, n_actions=2)
            self.optimizer = optim.Adam(self.actor_model.parameters(), lr=self.learning_rate)
        
        # Store the action and state for later update
        self.history[image_id] = {
            'state': state,
            'action': action
        }
    
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
        
        # Clean up history
        del self.history[image_id]
        
        print(f"REINFORCE update: image_id={image_id}, reward={reward}, loss={policy_loss.item():.4f}")


# Single instance — this is the model's brain
sarsa_object = SARSAObject()  # rename per model

reinforce_object = REINFORCEObject()

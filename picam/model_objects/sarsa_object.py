import numpy as np
from datetime import datetime

class SARSAObject:  # rename per model e.g. DQNObject, PPOObject etc.
    def __init__(self):
        self.history = {}  # {image_id: (state, action)}
        
        #add model-specific parameters below
        # e.g. for SARSA:
        # self.q_table = {}
        # self.learning_rate = 0.1
        # self.discount_factor = 0.9
        # self.epsilon = 0.1
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.1

    def get_state_key(self, state):
        # Convert list of floats to tuple so it can be used as dict key
        # We round to 2 decimal places to avoid too many unique states
        return tuple(round(x, 2) for x in state)

    def get_q_values(self, state_key):
        #if state never seen before, initialize Q values to 0
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0, 0.0]
        return self.q_table[state_key]
    
    def choose_action(self, state):
        #epsilon-greedy
        if np.random.random() < self.epsilon:
            return np.random.randint(0,2)
        else:
            state_key = self.get_state_key(state)
            q_values = self.get_q_values(state_key)
            return int(np.argmax(q_values)) # returns action with highest Q value
    
    def record(self, image_id, state, action):
        """Called by run_sarsa() from pi_server to store state/action for this image"""
        self.history[image_id] = (state, action)
    
    def update(self, image_id, reward):
        """Called by update_sarsa() from pi_server when reward/punishment comes back from frontend"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state, action = self.history[image_id]
        
        #implement model-specific update logic here
        # e.g. update Q-table, replay buffer, etc.
        state_key = self.get_state_key(state)
        q_values = self.get_q_values(state_key)

        # SARSA update formula:
        # Q(s,a) = Q(s,a) + alpha * (reward + gamma * Q(s',a') - Q(s,a))
        # Since we don't have next state/action yet (reward comes asynchronously),
        # we simplify: treat reward as the full target (so, discount_factor is 0)
        current_q = q_values[action]
        q_values[action] = current_q + self.learning_rate * (reward - current_q)

        print(f"Updating model with reward {reward} for image {image_id}")

# Single instance — this is the model's brain
sarsa_object = SARSAObject()  # rename per model
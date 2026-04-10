from datetime import datetime

class REINFORCEObject:  # rename per model e.g. DQNObject, PPOObject etc.
    def __init__(self):
        self.history = {}  # {image_id: (state, action)}
        
        # TODO: add model-specific parameters below
        # e.g. for SARSA:
        # self.q_table = {}
        # self.learning_rate = 0.1
        # self.discount_factor = 0.9
        # self.epsilon = 0.1
    
    def record(self, image_id, state, action):
        """Called by run_sarsa() from pi_server to store state/action for this image"""
        self.history[image_id] = (state, action)
    
    def update(self, image_id, reward):
        """Called by update_sarsa() from pi_server when reward/punishment comes back from frontend"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state, action = self.history[image_id]
        
        # TODO: implement model-specific update logic here
        # e.g. update Q-table, replay buffer, etc.
        print(f"Updating model with reward {reward} for image {image_id}")

# Single instance — this is the model's brain
reinforce_object = REINFORCEObject()  # rename per model
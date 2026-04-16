import numpy as np
from datetime import datetime
from .persistence import load_pickle, model_file, save_pickle

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
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("sarsa", ".pkl")
        self.load()

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

    def save(self):
        self.last_updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        save_pickle(
            self.checkpoint_path,
            {
                "q_table": self.q_table,
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
                "update_count": self.update_count,
                "last_reward": self.last_reward,
                "last_updated_at": self.last_updated_at,
            },
        )

    def load(self):
        checkpoint = load_pickle(self.checkpoint_path)
        if checkpoint is None:
            return

        self.q_table = checkpoint.get("q_table", self.q_table)
        self.learning_rate = checkpoint.get("learning_rate", self.learning_rate)
        self.discount_factor = checkpoint.get("discount_factor", self.discount_factor)
        self.epsilon = checkpoint.get("epsilon", self.epsilon)
        self.update_count = checkpoint.get("update_count", self.update_count)
        self.last_reward = checkpoint.get("last_reward", self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)
    
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
        self.update_count += 1
        self.last_reward = reward
        del self.history[image_id]
        self.save()

        print(f"Updating model with reward {reward} for image {image_id}")
        # DEBUG
        print(f"image_id: {image_id}")
        print(f"action taken: {action}")
        print(f"reward received: {reward}")
        print(f"Q values before: {current_q:.4f}")
        print(f"Q values after: {q_values[action]:.4f}")
        print(f"Full Q table: {sarsa_object.q_table}")

# Single instance — this is the model's brain
sarsa_object = SARSAObject()  # rename per model

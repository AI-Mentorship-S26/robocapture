import numpy as np
from datetime import datetime

class CONTEXTUALBANDITObject:  # rename per model e.g. DQNObject, PPOObject etc.
    def __init__(self):
        self.history = {}  # {image_id: (state, action)}
        
        self.state_size = 1287
        self.n_actions = 2
        self.learning_rate = 0.00001
        self.epsilon = 0.5  # start with high exploration
        self.epsilon_decay = 0.999  # decay epsilon over time
        self.epsilon_min = 0.05  # never go below 5% exploration

        # One weight vector per action — maps state to expected reward
        # Shape: (n_actions, state_size) = (2, 1287)
        self.weights = np.zeros((self.n_actions, self.state_size))

    def normalize_state(self, state):
        state_array = np.array(state)
        # Normalize only the first 7 features (metrics) separately from embedding
        metrics = state_array[:7]
        embedding = state_array[7:]
        
        # Normalize metrics
        metrics_norm = (metrics - np.mean(metrics)) / (np.std(metrics) + 1e-8)
        
        # Normalize embedding separately
        embedding_norm = (embedding - np.mean(embedding)) / (np.std(embedding) + 1e-8)
        
        return np.concatenate([metrics_norm, embedding_norm])

    def predict(self, state):
        """Predict expected reward for each action given state"""
        state_array = self.normalize_state(state)
        # Dot product of weights with state = predicted reward for each action
        return self.weights @ state_array  # returns [predicted_reward_for_0, predicted_reward_for_1]
    
    def choose_action(self, state):
        """Epsilon-greedy action selection"""
        # Always send if never seen anything like this before
        predictions = self.predict(state)

        print(f"Predictions: {predictions}")  # add this
        print(f"Epsilon: {self.epsilon}")     # add this

        if np.all(predictions == 0.0):
            return 1
        
        # Epsilon-greedy
        if np.random.random() < self.epsilon:
            return np.random.randint(0, 2)
        else:
            return int(np.argmax(predictions))
    
    def record(self, image_id, state, action):
        """Called by run_sarsa() from pi_server to store state/action for this image"""
        self.history[image_id] = (state, action)
    
    def update(self, image_id, reward):
        """Update weights when reward/punishment comes back"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state, action = self.history[image_id]
        state_array = self.normalize_state(state)
        
        # Calculate prediction error
        predicted_reward = self.weights[action] @ state_array
        error = reward - predicted_reward
        
        # Update weights for the action that was taken
        self.weights[action] += self.learning_rate * error * state_array
        
        # Give a small signal to the other action in the opposite direction
        other_action = 1 - action
        self.weights[other_action] -= self.learning_rate * 0.1 * error * state_array
                
        # Decay epsilon — explore less over time as model gets more confident
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        
        print(f"Updated weights for action {action} with reward {reward}")
        print(f"Prediction error: {error:.4f} | Epsilon: {self.epsilon:.4f}")

# Single instance — this is the model's brain
contextual_bandit_object = CONTEXTUALBANDITObject()  # rename per model
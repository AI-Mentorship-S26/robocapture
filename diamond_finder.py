import random
import numpy as np

class DiamondFinder:
    def __init__(self, num_caves, epsilon=0.1):
        self.num_caves = num_caves
        self.epsilon = epsilon
        
        # Memory: How many times we went to each cave
        self.attempts = np.zeros(num_caves)
        # Memory: The average diamonds found per cave
        self.estimates = np.zeros(num_caves)

    def choose_where_to_mine(self):
        # 10% of the time, explore a random cave
        if random.random() < self.epsilon:
            return random.randint(0, self.num_caves - 1)
        else:
            # 90% of the time, go to the best cave we've found so far
            return np.argmax(self.estimates)

    def learn(self, cave_index, reward):
        self.attempts[cave_index] += 1
        n = self.attempts[cave_index]
        old_estimate = self.estimates[cave_index]
        
        # The update formula: New Estimate = Old + (Error / Count)
        self.estimates[cave_index] = old_estimate + (reward - old_estimate) / n
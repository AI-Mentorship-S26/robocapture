import random

"""
RL Models for RoboCapture
Each function receives the CNN embedding (list of 1280 floats) as state
and must return either 0 (don't send) or 1 (send).
"""

#temporary placeholder - randomly decides 0 (don't send) or 1 (send)
def run_random(state):
    return random.randint(0, 1)


# Replace raise NotImplementedError with your model's inference logic
# Your model should take the embedding as input and return 0 or 1

def run_sarsa(state):
    raise NotImplementedError("SARSA not implemented yet")

def run_dqn(state):
    raise NotImplementedError("DQN not implemented yet")

def run_ppo(state):
    raise NotImplementedError("PPO not implemented yet")

def run_reinforce(state):
    raise NotImplementedError("REINFORCE not implemented yet")

def run_aac(state):
    raise NotImplementedError("AAC not implemented yet")

def run_tiny_sac(state):
    raise NotImplementedError("Tiny SAC not implemented yet")
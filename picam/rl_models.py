import random
from datetime import datetime
from model_objects.deep_contextual_bandit_object import deep_contextual_bandit_object
from model_objects.contextual_bandit_object import contextual_bandit_object
from model_objects.sarsa_object import sarsa_object
from model_objects.dqn_object import dqn_object
from model_objects.ppo_object import ppo_object
from model_objects.reinforce_object import reinforce_object
from model_objects.aac_object import aac_object
from model_objects.tiny_sac_object import tiny_sac_object

import torch
import numpy as np

"""
RL Models for RoboCapture
Each model has 2 functions:
- run_X(image_id, state): takes image_id and state (1287 floats), returns 0 or 1
- update_X(image_id, reward): takes image_id and reward/punishment, updates model

State structure (1287 values):
- [0] change_percentage
- [1] brightness
- [2] saturation
- [3] sharpness
- [4] edge_count
- [5] mean_frequency
- [6] embedding_magnitude
- [7:] embedding (1280 floats from MobileNetV2)
"""

#temporary placeholder - randomly decides 0 (don't send) or 1 (send)
def run_random(image_id, state):
    return random.randint(0, 1)
def update_random(image_id, state):
    pass
def nav_score_random(image_id, state):
    return None  # stub

# DEEP CONTEXTUAL BANDIT
def run_deep_contextual_bandit(image_id, state):
    action = deep_contextual_bandit_object.choose_action(state)
    deep_contextual_bandit_object.record(image_id, state, action)
    return action

def update_deep_contextual_bandit(image_id, reward):
    deep_contextual_bandit_object.update(image_id, reward)

def nav_score_deep_contextual_bandit(image_id, state):
    q_values = deep_contextual_bandit_object.predict(state)
    # softmax to convert Q values to probabilities
    exp_q = np.exp(q_values - np.max(q_values))
    probs = exp_q / exp_q.sum()
    action = int(np.argmax(q_values))  # exploit best action
    deep_contextual_bandit_object.record(image_id, state, action)
    return float(probs[1])  # probability of send (action 1)


# CONTEXTUAL BANDITS
def run_contextual_bandit(image_id, state):
    action = contextual_bandit_object.choose_action(state)
    contextual_bandit_object.record(image_id, state, action)
    return action

def update_contextual_bandit(image_id, reward):
    contextual_bandit_object.update(image_id, reward)
def nav_score_contextual_bandit(image_id, state):
    return None  # stub
  
# SARSA
def run_sarsa(image_id, state):
    action = sarsa_object.choose_action(state)
    sarsa_object.record(image_id, state, action)
    return action

def update_sarsa(image_id, reward):
    sarsa_object.update(image_id, reward)

def nav_score_sarsa(image_id, state):
 
    state_key = sarsa_object.get_state_key(state)
    q = sarsa_object.get_q_values(state_key)              # [q0, q1]
    exp_q = np.exp(np.array(q) - np.max(q))              # numerically stable
    probs = exp_q / exp_q.sum()
    # Record using the greedy action so reward updates are consistent
    action = int(np.argmax(q))
    sarsa_object.record(image_id, state, action)
    return float(probs[1])


# DQN
def run_dqn(image_id, state):
    action = dqn_object.choose_action(state)
    dqn_object.record(image_id, state, action)
    return action

def update_dqn(image_id, reward):
    dqn_object.update(image_id, reward)

def nav_score_dqn(image_id, state):
    return None  # stub

# PPO
PPO_EPSILON = 0.5  # explore randomly 50% of the time

def run_ppo(image_id, state):
    ppo_object.ensure_initialized(len(state))  # lazy init without double-record

    if random.random() < PPO_EPSILON:
        action = random.randint(0, 1)
    else:
        state_tensor = torch.from_numpy(np.array(state)).float()
        with torch.no_grad():
            logits = ppo_object.actor_model(state_tensor)
        m = torch.distributions.Categorical(logits=logits)
        action = m.sample().item()

    ppo_object.record(image_id, state, action)
    return action

def update_ppo(image_id, reward):
    ppo_object.update(image_id, reward)    

def nav_score_ppo(image_id, state):
    return None  # stub

# REINFORCE
def run_reinforce(image_id, state):
    if reinforce_object.actor_model is None:
        reinforce_object.record(image_id, state, 0)
        return 0
    
    state_tensor = torch.from_numpy(np.array(state)).float()
    logits = reinforce_object.actor_model(state_tensor)
    m = torch.distributions.Categorical(logits=logits)
    action = m.sample().item()
    
    reinforce_object.record(image_id, state, action)
    return action

def update_reinforce(image_id, reward):
    reinforce_object.update(image_id, reward)

def nav_score_reinforce(image_id, state):
    return None  # stub

# AAC
def run_aac(image_id, state):
    if aac_object.actor_model is None:
        aac_object.record(image_id, state, 0)
<<<<<<< Updated upstream
        return 0  # add this

        
    logits = aac_object.actor_model(state_tensor)
=======
        return 0

    state_tensor = torch.from_numpy(np.array(state)).float()
    with torch.no_grad():
        logits = aac_object.actor_model(state_tensor)
>>>>>>> Stashed changes
    m = torch.distributions.Categorical(logits=logits)
    action = m.sample().item()

    aac_object.record(image_id, state, action)
    return action

def update_aac(image_id, reward):
    aac_object.update(image_id, reward)
def nav_score_aac(image_id, state):

    if aac_object.actor_model is None:
        return None
    state_tensor = torch.from_numpy(np.array(state)).float()
    with torch.no_grad():
        logits = aac_object.actor_model(state_tensor)
        probs  = torch.softmax(logits, dim=0)
        action = torch.distributions.Categorical(logits=logits).sample().item()
    aac_object.record(image_id, state, action)
    return float(probs[1].item())


# Tiny SAC
def run_tiny_sac(image_id, state):
    # TODO: implement inference logic
    action = random.randint(0, 1) #placeholder until implemented
    tiny_sac_object.record(image_id, state, action)
    return action

def update_tiny_sac(image_id, reward):
    tiny_sac_object.update(image_id, reward)

def nav_score_tiny_sac(image_id, state):
    return None  # stub
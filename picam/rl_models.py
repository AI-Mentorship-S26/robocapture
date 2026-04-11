import random
from datetime import datetime
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


# CONTEXTUAL BANDITS
def run_contextual_bandit(image_id, state):
    action = contextual_bandit_object.choose_action(state)
    contextual_bandit_object.record(image_id, state, action)
    return action

def update_contextual_bandit(image_id, reward):
    contextual_bandit_object.update(image_id, reward)

  
# SARSA
def run_sarsa(image_id, state):
    action = sarsa_object.choose_action(state)
    sarsa_object.record(image_id, state, action)
    return action

def update_sarsa(image_id, reward):
    sarsa_object.update(image_id, reward)


# DQN
def run_dqn(image_id, state):
    action = dqn_object.choose_action(state)
    dqn_object.record(image_id, state, action)
    return action

def update_dqn(image_id, reward):
    dqn_object.update(image_id, reward)


# PPO
def run_ppo(image_id, state):
    state_tensor = torch.from_numpy(np.array(state)).float()
    logits = ppo_object.actor_model(state_tensor)
    m = torch.distributions.Categorical(logits=logits)
    action = m.sample().item()
    
    ppo_object.record(image_id, state, action)
    return action

def update_ppo(image_id, reward): 
    ppo_object.update(image_id, reward)


# REINFORCE
def run_reinforce(image_id, state):
    # TODO: implement inference logic
    action = random.randint(0, 1) #placeholder until implemented
    reinforce_object.record(image_id, state, action)
    return action

def update_reinforce(image_id, reward):
    reinforce_object.update(image_id, reward)


# AAC
def run_aac(image_id, state):

    state_tensor = torch.from_numpy(np.array(state)).float()

    if aac_object.actor_model is None:
        aac_object.record(image_id, state, 0)
        
    logits = aac_object.actor_model(state_tensor)
    m = torch.distributions.Categorical(logits=logits)
    action = m.sample().item()
    
    aac_object.record(image_id, state, action)
    return action

def update_aac(image_id, reward):
    aac_object.update(image_id, reward)


# Tiny SAC
def run_tiny_sac(image_id, state):
    # TODO: implement inference logic
    action = random.randint(0, 1) #placeholder until implemented
    tiny_sac_object.record(image_id, state, action)
    return action

def update_tiny_sac(image_id, reward):
    tiny_sac_object.update(image_id, reward)

import gymnasium as gym
import numpy as np
import random

env = gym.make("CliffWalking-v1")

alpha = 0.1
gamma = 0.9
epsilon = 0.1
episodes = 500
episodeRewards = []

nStates = env.observation_space.n
nActions = env.action_space.n 
Q = np.zeros((nStates, nActions))

def chooseAction(state):
    if random.random() < epsilon:
        return env.action_space.sample()
    else:
        return np.argmax(Q[state])
    
for episode in range(episodes):

    if episode % 100 == 0:
        env = gym.make("CliffWalking-v1", render_mode = "human")
    else:
        env = gym.make("CliffWalking-v1")

    state, info = env.reset()
    action = chooseAction(state)
    totalReward = 0
    done = False

    while not done:
        next_state, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        next_action = chooseAction(next_state)
        totalReward += reward

        Q[state][action] = Q[state][action] + alpha * (reward + (gamma * Q[next_state][next_action]) - Q[state][action])

        state = next_state
        action = next_action

    episodeRewards.append(totalReward)

env.close()

print("-------")
print(episodes, "times completed")
print("-------")
print("Q Table:")
print(Q)
print("-------")
print("First 10 episodes' rewards:")
print(episodeRewards[:10])
print()
print("Last 10 episodes' rewards:")
print(episodeRewards[-10:])
print("-------")

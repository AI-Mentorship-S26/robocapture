import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

import gymnasium as gym

class Actor(nn.Module):
    def __init__(self, n_inputs, n_actions):
        super(Actor, self).__init__()
        
        self.actor = nn.Sequential(
            nn.Linear(n_inputs, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, n_actions),
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        return self.actor(x)

class Critic(nn.Module):
    def __init__(self, n_inputs):
        super(Critic, self).__init__()

        self.critic = nn.Sequential(
            nn.Linear(n_inputs, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, x):
        return self.critic(x)
        
    
env_train = gym.make("LunarLander-v3")
env_viz = gym.make("LunarLander-v3", render_mode="human")

actor_model = Actor(8, 4)
critic_model = Critic(8)
actor_optimizer = optim.Adam(actor_model.parameters(), lr=1e-3)
critic_optimizer = optim.Adam(critic_model.parameters(), lr=5e-3)

    
state, info = env_train.reset()
state, info = env_viz.reset()

for episode in range(10000):

    env = env_viz if episode % 100 == 0 else env_train

    state, info = env.reset()
    done = False
    episode_reward = 0

    while not done:
        state_tensor = torch.from_numpy(state).float()
        probs = actor_model(state_tensor)

        m = torch.distributions.Categorical(probs)
        action = m.sample()

        value = critic_model(state_tensor)

        next_state, reward, terminated, truncated, _ = env.step(action.item())
        done = terminated or truncated

        next_state_tensor = torch.from_numpy(next_state).float()
        next_state_value = critic_model(next_state_tensor)

        td_target = reward + (0.99 * next_state_value * (1 - int(done)))
        advantage = td_target - value


        actor_loss = -m.log_prob(action) * advantage.detach()
        critic_loss = F.mse_loss(value, td_target.detach())


        actor_optimizer.zero_grad()
        critic_optimizer.zero_grad()


        actor_loss.backward()
        actor_optimizer.step()

        critic_loss.backward()
        critic_optimizer.step()
        
        episode_reward += reward
        state = next_state

    if episode % 25 == 0:
        print(f"Episode {episode:5d} | Reward: {episode_reward:.1f}")

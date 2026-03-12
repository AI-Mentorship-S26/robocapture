import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

import gymnasium as gym

class ActorCritic(nn.Module):
    def __init__(self, n_inputs, n_actions):
        super(ActorCritic, self).__init__()
        
        self.shared = nn.Sequential(
            nn.Linear(n_inputs, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 128), 
            nn.ReLU()
        )
        
        self.actor = nn.Linear(128, n_actions)
        
        self.critic = nn.Linear(128, 1)

    def forward(self, x):
        features = self.shared(x)
        
        action_probs = F.softmax(self.actor(features), dim=-1)
        
        state_value = self.critic(features)
        
        return action_probs, state_value
    
env_train = gym.make("LunarLander-v3")
env_viz = gym.make("LunarLander-v3", render_mode="human")

ac_model = ActorCritic(8, 4)

optimizer = optim.Adam(ac_model.parameters(), lr=1e-5)
    
state, info = env_train.reset()
state, info = env_viz.reset()


for episode in range(1000):

    if episode % 10 == 0:
        env = env_viz
    else:
        env = env_train

    state, info = env.reset()
    done = False

    while not done:

        state_tensor = torch.from_numpy(state).float()

        probs, state_value = ac_model(state_tensor)

        m = torch.distributions.Categorical(probs)
        action = m.sample()

        next_state, reward, terminated, truncated, _ = env.step(action.item())
        done = terminated or truncated

        next_state_tensor = torch.from_numpy(next_state).float()
        _, next_state_value = ac_model(next_state_tensor)

        if done:
            next_state_value = torch.tensor([0.0])

        #discount value 0.99
        target = reward + 0.99 * next_state_value
        advantage = target - state_value

        actor_loss = -m.log_prob(action) * advantage.detach()

        critic_loss = F.mse_loss(state_value, target.detach())

        total_loss = actor_loss + critic_loss

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        state = next_state


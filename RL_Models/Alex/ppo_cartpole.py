import numpy as np
import torch
from torch.distributions import Categorical
import gymnasium as gym
import imageio

# Create the CartPole environment.
# render_mode="rgb_array" lets us capture frames later to make a GIF.
env = gym.make('CartPole-v1', render_mode="rgb_array")


# ─────────────────────────────────────────────────────────────────────────────
# ACTOR NETWORK
# ─────────────────────────────────────────────────────────────────────────────
# The actor decides which action to take.
# For CartPole, actions are usually:
#   0 = push cart left
#   1 = push cart right
#
# This network takes the observation/state as input
# and outputs probabilities for each possible action.
actor = torch.nn.Sequential(
    torch.nn.Linear(env.observation_space.shape[0], 32),  # input -> hidden
    torch.nn.ReLU(),
    torch.nn.Linear(32, 32),                              # hidden -> hidden
    torch.nn.ReLU(),
    torch.nn.Linear(32, env.action_space.n),             # hidden -> action logits
    torch.nn.Softmax(dim=-1),                            # convert logits to probabilities
)


# ─────────────────────────────────────────────────────────────────────────────
# CRITIC NETWORK
# ─────────────────────────────────────────────────────────────────────────────
# The critic estimates how good a state is.
# It outputs a single value:
#   higher value = better expected future reward from this state
critic = torch.nn.Sequential(
    torch.nn.Linear(env.observation_space.shape[0], 32),  # input -> hidden
    torch.nn.ReLU(),
    torch.nn.Linear(32, 32),                              # hidden -> hidden
    torch.nn.ReLU(),
    torch.nn.Linear(32, 1),                               # hidden -> value estimate
)


# ─────────────────────────────────────────────────────────────────────────────
# PPO AGENT
# ─────────────────────────────────────────────────────────────────────────────
class CustomPPO:
    def __init__(self, training=True):
        # PPO / RL hyperparameters
        self.gamma = 0.995          # discount factor for future rewards
        self.lam = 0.8              # lambda used in GAE (Generalized Advantage Estimation)
        self.clip = 0.2             # PPO clipping range
        self.w_entropy = 0.0        # entropy bonus weight (0 means no entropy bonus)

        # Use the actor and critic networks defined above
        self.actor = actor
        self.critic = critic

        # Optimizers for each network
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=3e-4)
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=1e-3)

        # Gradient clipping helps keep training stable
        self.grad_norm = 0.5

        # Training options
        self.normalize_avt = True   # normalize advantages before updating
        self.value_clipping = False # whether to use PPO-style value clipping
        self.actor_clipping = True  # whether to use PPO ratio clipping

        self.training = training

        # temp_buffer stores transitions from the current episode
        self.temp_buffer = []

        # buffer stores all finished episodes before a policy update
        self.buffer = []

        # Track episode stats
        self.episode_len = []
        self.episode_win = []   # not really used here, but kept for possible extension

        # PPO usually updates over the same collected data multiple times
        self.n_epoch = 10
        self.batch_size = 64

    def act(self, observation):
        """
        Choose an action from the current policy.

        If training=True, also store useful information about the step
        so PPO can learn from it later.
        """
        with torch.no_grad():
            # Convert NumPy observation into a PyTorch tensor
            observation_tensor = torch.from_numpy(observation)

            # Actor outputs probabilities for each possible action
            action_probas = self.actor(observation_tensor)

            # Create a categorical distribution from those probabilities
            distribution = Categorical(action_probas)

            # Sample an action from the distribution
            action = distribution.sample()

            # During training, save step information for learning later
            if self.training:
                transition = {
                    "observation":       observation_tensor.detach(),             # state
                    "action_probas":     action_probas.detach(),                  # actor output probs
                    "action_log_proba":  distribution.log_prob(action).detach(),  # log prob of chosen action
                    "action":            action.detach(),                         # chosen action
                    "critic":            self.critic(observation_tensor).detach(),# critic value estimate
                }
                self.temp_buffer.append(transition)

        # Return action as a NumPy value for env.step(...)
        return action.numpy()

    def got_reward(self, reward, done):
        """
        Store reward for the most recent transition.

        If the episode is done, compute:
        - GAE advantage
        - TD(lambda) return
        Then move all transitions from temp_buffer into the main buffer.
        """
        last_transition = self.temp_buffer[-1]
        assert "reward" not in last_transition
        last_transition["reward"] = reward

        # Only compute returns/advantages when the full episode finishes
        if done:
            n_steps = len(self.temp_buffer)
            lastgaelam = 0

            # Go backwards through the episode to compute GAE
            for t in reversed(range(n_steps)):
                # For the final step, use last_transition["critic"]
                # Otherwise use the next transition's critic value
                nextvalues = (last_transition["critic"] if t == n_steps - 1
                              else self.temp_buffer[t + 1]["critic"])

                transition = self.temp_buffer[t]

                # TD residual (delta):
                # reward + discounted next value - current value
                delta = transition["reward"] - transition["critic"] + self.gamma * float(nextvalues)

                # GAE recursively accumulates advantage estimates
                transition["gae_avt"] = lastgaelam = delta + self.gamma * self.lam * lastgaelam

                # TD(lambda) target for critic = advantage + baseline value
                transition["td_lam"] = transition["gae_avt"] + transition["critic"]

            # Move completed episode into the main training buffer
            for t in self.temp_buffer:
                self.buffer.append(t)

            # Store episode length for logging
            self.episode_len.append(len(self.temp_buffer))

            # Clear episode buffer for next episode
            self.temp_buffer = []

    def optimize_policy(self, optim_step=None):
        """
        Run PPO updates on all data collected in self.buffer.
        """
        # If an unfinished episode somehow exists, discard it
        if self.temp_buffer:
            self.temp_buffer = []

        # Nothing to train on
        if not self.buffer:
            return

        # Collect all advantages from the buffer
        avantages = torch.tensor([t["gae_avt"] for t in self.buffer])

        # Normalize advantages to improve training stability
        if self.normalize_avt:
            avantages = (avantages - avantages.mean()) / (avantages.std() + 1e-8)

        # Save normalized advantages back into each transition
        for trans, avt in zip(self.buffer, avantages):
            trans["avantage"] = avt

        # PPO trains for several epochs over the same rollout data
        for ep in range(self.n_epoch):
            cumulative_entropy = 0
            cumulative_kl = 0
            cumulative_critic_loss = 0
            cumulative_actor_loss = 0

            # Shuffle data indices for minibatch training
            index_permutation = np.random.permutation(len(self.buffer))
            n_batch = len(self.buffer) // self.batch_size

            for i in range(n_batch):
                # Select one minibatch of indices
                ids = index_permutation[self.batch_size * i : self.batch_size * (i + 1)]

                # Build tensors for this minibatch
                obs              = torch.stack([self.buffer[k]["observation"]      for k in ids])
                critic_target    = torch.stack([self.buffer[k]["td_lam"]           for k in ids])
                critic_old       = torch.tensor([self.buffer[k]["critic"]          for k in ids]).view(-1, 1)
                action_proba_log = torch.stack([self.buffer[k]["action_log_proba"] for k in ids])
                action           = torch.stack([self.buffer[k]["action"]           for k in ids])
                avantages_b      = torch.stack([self.buffer[k]["avantage"]         for k in ids])

                # ── ACTOR UPDATE ───────────────────────────────────────────────
                # Get updated action probabilities from current actor
                new_action_probas = self.actor(obs)
                new_distribution = Categorical(new_action_probas)
                new_action_proba_log = new_distribution.log_prob(action)

                # Entropy encourages randomness/exploration
                entropy = -torch.mean(new_action_proba_log)

                # PPO ratio:
                # new policy probability / old policy probability
                ratios = torch.exp(new_action_proba_log - action_proba_log)

                # Unclipped PPO objective
                surr1 = ratios * avantages_b

                if self.actor_clipping:
                    # Clipped PPO objective limits how much the policy can change
                    surr2 = torch.clamp(ratios, 1 - self.clip, 1 + self.clip) * avantages_b
                    actor_loss = -torch.min(surr1, surr2).mean() - self.w_entropy * entropy
                else:
                    actor_loss = -surr1.mean() - self.w_entropy * entropy

                # Standard gradient update for actor
                self.actor_optimizer.zero_grad()
                actor_loss.backward()

                # Clip gradients for stability
                if self.grad_norm is not None:
                    torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.grad_norm)

                self.actor_optimizer.step()

                # ── CRITIC UPDATE ──────────────────────────────────────────────
                # Critic predicts state values
                values = self.critic(obs)

                if self.value_clipping:
                    # Optional value clipping variant for critic
                    squared_diff = torch.square(values - critic_target)
                    clipped_squared_diff = torch.square(
                        torch.clamp(values, critic_old - self.clip, critic_old + self.clip) - critic_target
                    )
                    critic_loss = torch.max(squared_diff, clipped_squared_diff).mean()
                else:
                    # Standard mean squared error loss
                    critic_loss = torch.nn.functional.mse_loss(values, critic_target)

                # Standard gradient update for critic
                self.critic_optimizer.zero_grad()
                critic_loss.backward()
                self.critic_optimizer.step()

                # Approximate KL divergence to measure policy change
                kl_estimation = ((ratios - 1) - torch.log(ratios)).mean()

                # Accumulate stats for logging
                cumulative_entropy     += entropy.item()
                cumulative_kl          += kl_estimation.item()
                cumulative_actor_loss  += actor_loss.item()
                cumulative_critic_loss += critic_loss.item()

            # Average stats across batches for this epoch
            cumulative_entropy     /= n_batch
            cumulative_kl          /= n_batch
            cumulative_actor_loss  /= n_batch
            cumulative_critic_loss /= n_batch

        # Compute summary stats for this whole optimization step
        mean_total_reward = sum(t["reward"] for t in self.buffer) / len(self.episode_len)
        mean_ep_len       = sum(self.episode_len) / len(self.episode_len)

        # Print training progress
        print(f"Step {optim_step if optim_step is not None else 0}: Reward = {mean_total_reward:.0f}")

        # Clear training buffer after update
        self.buffer = []
        self.episode_len = []
        self.episode_win = []

        return mean_ep_len


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING LOOP
# ─────────────────────────────────────────────────────────────────────────────
agent = CustomPPO()

n_ep = 100  # start by collecting 100 episodes before each PPO update

for optim_step in range(100):
    # Collect rollout data
    for ep in range(n_ep):
        observation, _ = env.reset()
        done = False
        step = 0

        while not done:
            # Choose action from current policy
            action = agent.act(observation)

            # Apply action in environment
            observation, reward, done, *_ = env.step(action)

            # Force stop if episode gets too long
            if not done and step > 2_000:
                done = True

            # Store reward and maybe finish episode bookkeeping
            agent.got_reward(reward, done)
            step += 1

    # Train PPO on the collected rollout
    mean_ep_len = agent.optimize_policy(optim_step)

    # Stop early if the agent has basically solved the environment
    if mean_ep_len >= 2_000:
        break

    # Adjust number of episodes collected next round
    # Shorter episodes -> collect more episodes
    # Longer episodes -> collect fewer episodes
    n_ep = int(1_000 / mean_ep_len) + 1

print("Finished")


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION / GIF CREATION
# ─────────────────────────────────────────────────────────────────────────────
def show_episode(agent, n_episode=1):
    """
    Run trained agent without recording training data,
    capture frames, and save them as a GIF.
    """
    agent.training = False  # disable transition storage during evaluation
    max_episode_len = 2_000
    frames = []

    for _ in range(n_episode):
        obs, _ = env.reset()
        done = False
        steps = 0

        while not done:
            # Agent acts using learned policy
            action = agent.act(obs)

            # Step environment forward
            obs, reward, done, *_ = env.step(action)

            # Save rendered frame for GIF
            frames.append(env.render())

            # Safety stop if episode gets too long
            if steps >= max_episode_len:
                done = True

            steps += 1

    print(f"Captured {len(frames)} frames")

    # Save frames into an animated GIF
    imageio.mimsave("animation.gif", frames, fps=30, loop=0)
    print("Saved to animation.gif")

    # Re-enable training mode in case we want to train again later
    agent.training = True


# Show one episode using the trained agent
show_episode(agent)
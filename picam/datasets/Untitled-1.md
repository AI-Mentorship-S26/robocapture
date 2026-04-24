
Proximal Policy Optimization (PPO) implementation —  The agent learns by trying things in the CartPole environment, getting rewards or penalties, and slowly improving its behavior.

Actor-Critic Architecture
Two separate networks that work together:

Actor — outputs a probability for each action. It doesn't always pick the best-looking action — it randomly samples based on those probabilities, which keeps it exploring.
Critic — outputs a single number: how much total future reward the agent can expect from the current state. It doesn't pick actions — it just judges how good the situation is.

They don't share any weights — completely separate networks.

The act() Method

Feeds the observation into the actor → gets action probabilities
Randomly samples an action from those probabilities
Saves: the state, the action taken, the log probability of that action, and the critic's value estimate

Log probability is saved because PPO needs to compare the old policy to the updated one later




The got_reward() Method
After each step, the reward gets attached to the last saved transition. When the episode ends, it walks backwards through all the steps and computes two things:
GAE (Generalized Advantage Estimation):
delta = reward + gamma * next_value - current_value
advantage = delta + gamma * lambda * previous_advantage

delta is the TD error — how much better or worse the actual reward was compared to what the critic expected
GAE smooths the advantage using lambda — this balances accuracy vs. stability
Advantage > 0 means the action did better than expected; < 0 means worse

TD(λ) Return:
td_lambda = advantage + current_value
This is the number the critic will try to predict next time.

The optimize_policy() Method
This is where the actual learning happens. For each minibatch of saved transitions:
Actor update:
ratio = exp(new_log_prob - old_log_prob)

This ratio measures how much the policy changed since the data was collected
ratio = 1.0 means no change at all
PPO clips the ratio to [0.8, 1.2] — this stops any single update from changing the policy too drastically
The loss is the negative of the clipped objective because we're minimizing a loss but want to maximize reward

Critic update:

Simple mean squared error between the critic's prediction and the actual TD(λ) target
Teaches the critic to make better predictions over time

Advantage normalization:

Before updating, advantages are rescaled to have mean=0 and std=1
Stops episodes with unusually high rewards from having too much influence on the update


Why PPO Over Simpler Methods?
A basic policy gradient can take a huge update step and accidentally destroy a good policy. PPO's clipping acts like a guardrail — it says "only change the policy by this much per step, no matter what."

Training Loop Logic

Collects N episodes, then does one PPO update
n_ep adjusts itself: short episodes → collect more before updating; long episodes → fewer needed
Goal: survive 2,000 steps, which basically counts as solving CartPole

gamma: how much future rewards matter (close to 1 = thinks far ahead)
lam: GAE smoothing - lower = more biased but more stable
clip: max allowed policy change per update
n_epoch: how many passes over the same collected data
batch_size: how many transitions per gradient step






-CartPole is a simulation where a pole balances on a cart — the agent keeps it upright by pushing left or right

-Two networks: the actor picks actions, the critic judges how good the current state is

-The actor outputs probabilities for each action and samples from them — sampling keeps it exploring instead of always doing the same thing

-The critic outputs a single number — its estimate of how much total future reward to expect from here

-Every step, we save the state, action taken, log probability of that action, and the critic's estimate

-Log probability is saved so PPO can compare the old policy to the updated one later

-When an episode ends, we go backwards through all steps and compute the advantage — was each action better or worse than the critic expected?

-We also compute the TD(λ) return — the target value the critic will try to predict next time

-In the update step, PPO computes a ratio between the new and old policy — if it drifts too far from 1, the policy changed too much

-PPO clips that ratio — this is the core idea, it's a guardrail that keeps any single update from being too drastic

-The critic is updated with a simple mean squared error loss between its prediction and the actual return

-We run this update 10 times over the same data using random minibatches each time

-The training loop collects episodes, updates, then adjusts how many episodes to collect based on current performance

-Once the agent survives 2,000 steps, training stops — that's considered solved

CartPole: The simulation environment — a pole on a cart that the agent must keep upright

Agent: The thing doing the learning — it observes the state and decides what to do

Observation/State: The current snapshot of the environment (cart position, pole angle, velocities)

Action: What the agent does — push cart left or push cart right

Reward: A score the environment gives after each action — +1 for every step the pole stays up

Episode: One full run of the simulation from start to when the pole falls

Actor: Neural network that outputs probabilities for each action

Critic: Neural network that estimates how much total future reward to expect from the current state

Policy: The actor's behavior — the rule it uses to decide actions

Value: The critic's output — expected total future reward from a given state

Advantage: How much better or worse an action was compared to what the critic expected

GAE: A method for computing smooth, stable advantage estimates by looking backwards through the episode

TD Error (delta): The difference between the reward actually received and what the critic predicted

TD(λ) Return: The target value the critic tries to learn to predict

Log Probability: The log of how likely the actor was to pick a given action — used to measure policy change

PPO Ratio: New policy probability divided by old policy probability — measures how much the policy changed

Clipping: PPO's guardrail — limits the ratio to a safe range so no single update is too drastic

Epoch: One full pass over the collected data during training

Minibatch: A small random subset of the collected data used for one gradient update

Gradient Clipping: Limits how large the gradient update can be — keeps training stable

Gamma (γ): Discount factor — how much the agent cares about future rewards vs. immediate ones

Lambda (λ): GAE smoothing factor — balances accuracy and stability of advantage estimates

Entropy: A measure of randomness in the policy — higher entropy means more exploration

KL Divergence: A measure of how different the new policy is from the old one

Advantage Normalization: Rescaling advantages to mean=0, std=1 so no single episode dominates the update
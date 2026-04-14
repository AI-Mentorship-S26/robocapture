import torch
import torch.nn as nn
import random
import logging
from datetime import datetime
from collections import deque
from .persistence import load_torch, model_file, save_torch

logger = logging.getLogger(__name__)

STATE_SIZE = 1287   # 7 pipeline features + 1280 MobileNetV2 embedding
ACTION_SIZE = 2     # 0 = don't send, 1 = send


class _QNetwork(nn.Module):
    """Feedforward Q-network: maps state → Q(s, a) for all actions."""

    def __init__(self, state_size: int, action_size: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DQNObject:
    """DQN agent — mirrors the interface of SARSAObject for use with rl_models.py.

    Lifecycle per image:
        1. ``choose_action(state)``  — epsilon-greedy action selection
        2. ``record(image_id, state, action)`` — store for async reward
        3. ``update(image_id, reward)``  — add to replay buffer and train
    """

    def __init__(self, state_size: int = STATE_SIZE, action_size: int = ACTION_SIZE):
        self.state_size = state_size
        self.action_size = action_size

        # Async reward bookkeeping — same pattern as SARSAObject
        self.history: dict = {}  # {image_id: (state, action)}

        # Epsilon-greedy exploration schedule
        self.epsilon: float = 1.0
        self.epsilon_min: float = 0.05
        self.epsilon_decay: float = 0.995

        self.gamma: float = 0.95      # future-reward discount
        self.batch_size: int = 32
        self.learning_rate: float = 1e-3
        self.replay_capacity: int = 5000
        self.update_count: int = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("dqn", ".pt")

        self.memory: deque = deque(maxlen=self.replay_capacity)

        self.model = _QNetwork(state_size, action_size)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.loss_fn = nn.MSELoss()
        self.load()

    # ------------------------------------------------------------------
    # Public interface (matches SARSAObject / pi_server expectations)
    # ------------------------------------------------------------------

    def choose_action(self, state: list) -> int:
        """Epsilon-greedy action selection.

        Parameters
        ----------
        state:
            Raw state list from the preprocessing pipeline (length STATE_SIZE).

        Returns
        -------
        int
            0 (don't send) or 1 (send).
        """
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)

        self.model.eval()
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0)  # (1, STATE_SIZE)
            q_values = self.model(s)                   # (1, ACTION_SIZE)
        return int(torch.argmax(q_values).item())

    def record(self, image_id: str, state: list, action: int) -> None:
        """Store state/action pair so ``update()`` can retrieve it later.

        Called by ``run_dqn()`` in rl_models.py immediately after action selection.
        """
        self.history[image_id] = (state, action)

    def save(self) -> None:
        self.last_updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        save_torch(
            self.checkpoint_path,
            {
                "state_size": self.state_size,
                "action_size": self.action_size,
                "epsilon": self.epsilon,
                "epsilon_min": self.epsilon_min,
                "epsilon_decay": self.epsilon_decay,
                "gamma": self.gamma,
                "batch_size": self.batch_size,
                "learning_rate": self.learning_rate,
                "replay_capacity": self.replay_capacity,
                "update_count": self.update_count,
                "last_reward": self.last_reward,
                "last_updated_at": self.last_updated_at,
                "memory": list(self.memory),
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
            },
        )

    def load(self) -> None:
        checkpoint = load_torch(self.checkpoint_path)
        if checkpoint is None:
            return

        self.state_size = checkpoint.get("state_size", self.state_size)
        self.action_size = checkpoint.get("action_size", self.action_size)
        self.epsilon = checkpoint.get("epsilon", self.epsilon)
        self.epsilon_min = checkpoint.get("epsilon_min", self.epsilon_min)
        self.epsilon_decay = checkpoint.get("epsilon_decay", self.epsilon_decay)
        self.gamma = checkpoint.get("gamma", self.gamma)
        self.batch_size = checkpoint.get("batch_size", self.batch_size)
        self.learning_rate = checkpoint.get("learning_rate", self.learning_rate)
        self.replay_capacity = checkpoint.get("replay_capacity", self.replay_capacity)
        self.update_count = checkpoint.get("update_count", self.update_count)
        self.last_reward = checkpoint.get("last_reward", self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)

        self.memory = deque(checkpoint.get("memory", []), maxlen=self.replay_capacity)
        self.model = _QNetwork(self.state_size, self.action_size)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    def update(self, image_id: str, reward: float) -> None:
        """Receive async reward, add transition to replay buffer, and train.

        Called by ``update_dqn()`` in rl_models.py when feedback arrives from
        the frontend.  Because next_state is not available at reward time, the
        transition is treated as terminal (next Q contribution zeroed out via
        done=True), which is equivalent to a one-step Monte Carlo target.
        """
        if image_id not in self.history:
            logger.warning("image_id %s not found in history", image_id)
            return

        state, action = self.history.pop(image_id)

        # Terminal transition: no next state available asynchronously
        self.memory.append((state, action, reward, None))

        self._replay()
        self.update_count += 1
        self.last_reward = reward
        self.save()
        logger.debug("DQN updated | image=%s reward=%s epsilon=%.4f",
                     image_id, reward, self.epsilon)

    # ------------------------------------------------------------------
    # Internal training
    # ------------------------------------------------------------------

    def _replay(self) -> None:
        """Sample a mini-batch and perform one gradient step."""
        if len(self.memory) < self.batch_size:
            return

        batch = random.sample(self.memory, self.batch_size)

        self.model.train()
        total_loss = torch.tensor(0.0)

        for state, action, reward, next_state in batch:
            s = torch.FloatTensor(state).unsqueeze(0)  # (1, STATE_SIZE)

            if next_state is not None:
                with torch.no_grad():
                    ns = torch.FloatTensor(next_state).unsqueeze(0)
                    best_next_q = torch.max(self.model(ns)).item()
                target_q = reward + self.gamma * best_next_q
            else:
                # Terminal — no future reward
                target_q = reward

            current_qs = self.model(s)                         # (1, ACTION_SIZE)
            target_qs = current_qs.clone().detach()
            target_qs[0][action] = target_q                    # only correct taken action

            loss = self.loss_fn(current_qs, target_qs)
            total_loss = total_loss + loss

        # Single gradient step over accumulated loss
        self.optimizer.zero_grad()
        total_loss.backward()
        self.optimizer.step()

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


# Single instance — imported by rl_models.py
dqn_object = DQNObject()

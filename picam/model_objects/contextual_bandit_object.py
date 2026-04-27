import logging
import numpy as np
from datetime import datetime, timezone
from .persistence import load_pickle, model_file, save_pickle

logger = logging.getLogger(__name__)


class CONTEXTUALBANDITObject:
    def __init__(self):
        self.history = {}
        self.state_size = None          # set lazily on first state seen
        self.n_actions = 2
        self.learning_rate = 0.01       # was 0.00001 — too small for <1000 samples
        self.epsilon = 0.5
        self.epsilon_decay = 0.999
        self.epsilon_min = 0.05
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("contextual_bandit", ".pkl")
        self.weights = None             # initialized lazily
        self.load()

    def _ensure_initialized(self, state_size: int) -> None:
        if self.weights is not None:
            return
        self.state_size = state_size
        self.weights = np.zeros((self.n_actions, self.state_size))

    def normalize_state(self, state):
        state_array = np.array(state)
        if len(state_array) > 7:
            metrics   = state_array[:7]
            embedding = state_array[7:]
            metrics_norm   = (metrics   - np.mean(metrics))   / (np.std(metrics)   + 1e-8)
            embedding_norm = (embedding - np.mean(embedding)) / (np.std(embedding) + 1e-8)
            return np.concatenate([metrics_norm, embedding_norm])
        return (state_array - np.mean(state_array)) / (np.std(state_array) + 1e-8)

    def predict(self, state):
        self._ensure_initialized(len(state))
        return self.weights @ self.normalize_state(state)

    def choose_action(self, state):
        self._ensure_initialized(len(state))
        predictions = self.predict(state)
        if np.all(predictions == 0.0):
            return 1
        if np.random.random() < self.epsilon:
            return np.random.randint(0, 2)
        return int(np.argmax(predictions))

    def record(self, image_id, state, action):
        self._ensure_initialized(len(state))
        self.history[image_id] = (state, action)

    def save(self):
        self.last_updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_pickle(
            self.checkpoint_path,
            {
                "state_size":    self.state_size,
                "n_actions":     self.n_actions,
                "learning_rate": self.learning_rate,
                "epsilon":       self.epsilon,
                "epsilon_decay": self.epsilon_decay,
                "epsilon_min":   self.epsilon_min,
                "update_count":  self.update_count,
                "last_reward":   self.last_reward,
                "last_updated_at": self.last_updated_at,
                "weights":       self.weights,
            },
        )

    def load(self):
        checkpoint = load_pickle(self.checkpoint_path)
        if checkpoint is None:
            return
        self.state_size    = checkpoint.get("state_size",    self.state_size)
        self.n_actions     = checkpoint.get("n_actions",     self.n_actions)
        self.learning_rate = checkpoint.get("learning_rate", self.learning_rate)
        self.epsilon       = checkpoint.get("epsilon",       self.epsilon)
        self.epsilon_decay = checkpoint.get("epsilon_decay", self.epsilon_decay)
        self.epsilon_min   = checkpoint.get("epsilon_min",   self.epsilon_min)
        self.update_count  = checkpoint.get("update_count",  self.update_count)
        self.last_reward   = checkpoint.get("last_reward",   self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)
        self.weights       = checkpoint.get("weights",       self.weights)
        if self.weights is not None:
            self.state_size = self.weights.shape[1]

    def update(self, image_id, reward):
        if image_id not in self.history:
            logger.warning("image_id %s not found in history", image_id)
            return

        state, action = self.history[image_id]
        state_array = self.normalize_state(state)
        predicted_reward = self.weights[action] @ state_array
        error = reward - predicted_reward

        self.weights[action]     += self.learning_rate * error * state_array
        self.weights[1 - action] -= self.learning_rate * 0.1 * error * state_array

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.update_count += 1
        self.last_reward = reward
        del self.history[image_id]
        self.save()
        logger.debug(
            "CB updated | image=%s action=%d reward=%s error=%.4f epsilon=%.4f",
            image_id, action, reward, error, self.epsilon,
        )


contextual_bandit_object = CONTEXTUALBANDITObject()

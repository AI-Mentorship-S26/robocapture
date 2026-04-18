import logging
import numpy as np
from datetime import datetime, timezone
from .persistence import load_pickle, model_file, save_pickle

logger = logging.getLogger(__name__)


class SARSAObject:
    def __init__(self):
        self.history = {}
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.1
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("sarsa", ".pkl")
        self.load()

    def get_state_key(self, state):
        return tuple(round(x, 2) for x in state)

    def get_q_values(self, state_key):
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0, 0.0]
        return self.q_table[state_key]

    def choose_action(self, state):
        if np.random.random() < self.epsilon:
            return np.random.randint(0, 2)
        state_key = self.get_state_key(state)
        return int(np.argmax(self.get_q_values(state_key)))

    def record(self, image_id, state, action):
        self.history[image_id] = (state, action)

    def save(self):
        self.last_updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_pickle(
            self.checkpoint_path,
            {
                "q_table":         self.q_table,
                "learning_rate":   self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon":         self.epsilon,
                "update_count":    self.update_count,
                "last_reward":     self.last_reward,
                "last_updated_at": self.last_updated_at,
            },
        )

    def load(self):
        checkpoint = load_pickle(self.checkpoint_path)
        if checkpoint is None:
            return
        self.q_table         = checkpoint.get("q_table",         self.q_table)
        self.learning_rate   = checkpoint.get("learning_rate",   self.learning_rate)
        self.discount_factor = checkpoint.get("discount_factor", self.discount_factor)
        self.epsilon         = checkpoint.get("epsilon",         self.epsilon)
        self.update_count    = checkpoint.get("update_count",    self.update_count)
        self.last_reward     = checkpoint.get("last_reward",     self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)

    def update(self, image_id, reward):
        if image_id not in self.history:
            logger.warning("image_id %s not found in history", image_id)
            return

        state, action = self.history[image_id]
        state_key = self.get_state_key(state)
        q_values  = self.get_q_values(state_key)

        current_q = q_values[action]
        q_values[action] = current_q + self.learning_rate * (reward - current_q)

        self.update_count += 1
        self.last_reward = reward
        del self.history[image_id]
        self.save()
        logger.debug(
            "SARSA updated | image=%s action=%d reward=%s q: %.4f→%.4f",
            image_id, action, reward, current_q, q_values[action],
        )


sarsa_object = SARSAObject()

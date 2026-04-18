import logging
from datetime import datetime, timezone
from .persistence import load_pickle, model_file, save_pickle

logger = logging.getLogger(__name__)


class TINYSACObject:
    """Placeholder — Tiny SAC not yet implemented. Behaves identically to random."""

    def __init__(self):
        self.history = {}
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("tiny_sac", ".pkl")
        self.load()

    def record(self, image_id, state, action):
        self.history[image_id] = (state, action)

    def save(self):
        self.last_updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_pickle(
            self.checkpoint_path,
            {
                "update_count":    self.update_count,
                "last_reward":     self.last_reward,
                "last_updated_at": self.last_updated_at,
            },
        )

    def load(self):
        checkpoint = load_pickle(self.checkpoint_path)
        if checkpoint is None:
            return
        self.update_count    = checkpoint.get("update_count",    self.update_count)
        self.last_reward     = checkpoint.get("last_reward",     self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)

    def update(self, image_id, reward):
        if image_id not in self.history:
            logger.warning("image_id %s not found in history", image_id)
            return
        del self.history[image_id]
        self.update_count += 1
        self.last_reward = reward
        self.save()
        logger.debug("TinySAC (placeholder) updated | image=%s reward=%s", image_id, reward)


tiny_sac_object = TINYSACObject()

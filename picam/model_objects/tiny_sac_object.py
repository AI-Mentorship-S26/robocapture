from datetime import datetime
from .persistence import load_pickle, model_file, save_pickle

class TINYSACObject:  # rename per model e.g. DQNObject, PPOObject etc.
    def __init__(self):
        self.history = {}  # {image_id: (state, action)}
        self.update_count = 0
        self.last_reward = None
        self.last_updated_at = None
        self.checkpoint_path = model_file("tiny_sac", ".pkl")
        
        # TODO: add model-specific parameters below
        # e.g. for SARSA:
        # self.q_table = {}
        # self.learning_rate = 0.1
        # self.discount_factor = 0.9
        # self.epsilon = 0.1
        self.load()
    
    def record(self, image_id, state, action):
        """Called by run_sarsa() from pi_server to store state/action for this image"""
        self.history[image_id] = (state, action)

    def save(self):
        self.last_updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        save_pickle(
            self.checkpoint_path,
            {
                "update_count": self.update_count,
                "last_reward": self.last_reward,
                "last_updated_at": self.last_updated_at,
                "note": "tiny_sac is still a placeholder model with no trainable parameters yet",
            },
        )

    def load(self):
        checkpoint = load_pickle(self.checkpoint_path)
        if checkpoint is None:
            return

        self.update_count = checkpoint.get("update_count", self.update_count)
        self.last_reward = checkpoint.get("last_reward", self.last_reward)
        self.last_updated_at = checkpoint.get("last_updated_at", self.last_updated_at)
    
    def update(self, image_id, reward):
        """Called by update_sarsa() from pi_server when reward/punishment comes back from frontend"""
        if image_id not in self.history:
            print(f"Warning: image_id {image_id} not found in history")
            return
        
        state, action = self.history[image_id]
        
        # TODO: implement model-specific update logic here
        # e.g. update Q-table, replay buffer, etc.
        del self.history[image_id]
        self.update_count += 1
        self.last_reward = reward
        self.save()
        print(f"Updating model with reward {reward} for image {image_id}")

# Single instance — this is the model's brain
tiny_sac_object = TINYSACObject()  # rename per model

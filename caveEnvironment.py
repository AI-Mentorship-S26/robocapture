import random

class CaveEnvironment: 
    def __init__(self):
        # Hidden probabilities: Lush (50%), Deepslate (70%), Dripstone (90%)
        self.caveNames = ["Lush", "Deepslate", "Dripstone"]
        self.caveProb = [0.5, 0.7, 0.9] 

    def explore_cave(self, cave_index):
        # The RNG (Random Number Generator) logic
        if random.random() < self.caveProb[cave_index]:
            return 1 # Diamond!
        else:
            return 0 # Cobblestone.
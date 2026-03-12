from caveEnvironment import CaveEnvironment
from diamond_finder import DiamondFinder
import numpy as np

# 1. Setup
world = CaveEnvironment()
agent = DiamondFinder(num_caves=3, epsilon=0.1)

print("--- Begin Mining Expedition ---")

# 2. The Execution Loop
for trial in range(1000):
    choice = agent.choose_where_to_mine()
    reward = world.explore_cave(choice)
    agent.learn(choice, reward)

# 3. The Report (How to see if it worked)
print("Expedition Finished!\n")
print(f"Secret Truth (Win Rates): {world.caveProb}")
print(f"Agent's Guesses: {np.round(agent.estimates, 2)}")
print(f"Total times each cave was visited: {agent.attempts}")

best_found = np.argmax(agent.estimates)
print(f"\nSteve decides the best cave is: {world.caveNames[best_found]}")
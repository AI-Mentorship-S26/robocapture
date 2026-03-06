import numpy as np
from random import random, randint, seed


num_arms = 5
num_cycles = 1000
eplison = 0.1

rating_scores = [1, 9, 3, 7, 8]
restaurants_total_reward = [0.0] * num_arms
restaurants_num_visited = [0] * num_arms
restaurants_avg_reward = [0.0] * num_arms
best_score_seen = 0


for i in range(num_cycles):
    random_num = randint(0, 4)

    if random() < eplison:
        chosen_arm = random_num
            
    else:
        chosen_arm = np.argmax(restaurants_avg_reward)
    
    score = rating_scores[chosen_arm]
    restaurants_num_visited[chosen_arm] += 1
    
    
    if score >= best_score_seen: 
        restaurants_total_reward[chosen_arm] += score
        best_score_seen = max(best_score_seen, score)
    else:  
        restaurants_total_reward[chosen_arm] -= 1
    
    
    restaurants_avg_reward[chosen_arm] = restaurants_total_reward[chosen_arm] / restaurants_num_visited[chosen_arm]

print("Number of visits:", restaurants_num_visited)
print("Total rewards:", restaurants_total_reward)
print(f"Average rewards:", [round(reward, 2) for reward in restaurants_avg_reward])
print(f"Best restaurant is: Restaurant {np.argmax(restaurants_avg_reward)} with avg reward of {max(restaurants_avg_reward):.2f}")



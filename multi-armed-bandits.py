import random

# hidden reward chances for each arm
# arm 0-4
# total of 5 arms
true_probs = [0.1, 0.3, 0.8, 0.5, 0.2]

k = len(true_probs)  # number of arms
epsilon = 0.1  # exploration rate. 10% of the time the robot will be curious and try a random machine, 90% of the time it will choose the machine with the highest estimated reward
steps = 2000   # number of times we try

# agent memory
Q = [0] * k  # estimated rewards for each arm. makes a list of 5 zeros: Q[0, 0, 0, 0, 0]
N = [0] * k  # number of times each arm was pulled. makes a list of 5 zeros: N[0, 0, 0, 0, 0]

# function to stimulate pulling an arm. gives a random decimal between 0 and 1. example: 0.37. If the arm probability is 0.8, you get rewarded 80% of the time. So if random number is less than 0.8 you get a reward of 1.
def pull(arm):
    if random.random() < true_probs[arm]:
        return 1  # reward
    else:
        return 0  # no reward
 
# repeats everything inside it 2000 times. the robot picks a machine, gets a reward, and learns again and again.    
for step in range(steps):
    
    # decide explore or exploit. Means: roll a random number, if it's less than 0.1, it'll pick a random arm. 
    if random.random() < epsilon:
        action = random.randrange(k)  # explore: choose a random arm
    # finds the biggest value in Q( the best estimated arm) and picks that arm    
    else:
        action = Q.index(max(Q))  # exploit: choose the best known arm
        
    reward = pull(action)  # get reward from the environment. either get 0 or 1
    
    N[action] += 1  # update count for the chosen arm
    
    # update estimate value (learning step). Q[action] is the robot's guess for that arm. reward is what actually happened (0 or 1). It adjusts Q a little bit 
    Q[action] = Q[action] + (1/N[action]) * (reward - Q[action]) 
    
# print results
print("True probabilities:", true_probs)
print("Times chosen:", N)
print("Estimated values:", Q)
print("Best arm:", Q.index(max(Q)))
import random 
import numpy as np 

class EpsilonGreedy:
    def __init__(self,n_restaurants, epsilon):
        self.n_restaurants = n_restaurants
        self.epsilon = epsilon 
        self.visits = np.zeros(n_restaurants)
        self.satisfaction = np.zeros(n_restaurants)

    def choose_restaurant(self):
        if np.random.random() < self.epsilon:
            return np.random.choice(self.n_restaurants)    #exploring part
        else:
        #checking who got the highest average score (we add 10^-5 in the denominator so that it does not become a n/0 type case )
            return np.argmax(self.satisfaction / (self.visits + 1e-5))   
        
    def update(self,restaurant,score):
        self.visits[restaurant] += 1
        self.satisfaction[restaurant] += score
    
n_restaurants = 3
epsilon = 0.1   #for our case we would need the robot to explore so the value of epsilon should be <=5% 
n_days = 120

true_avg_satisfaction = np.array([8,6,9])
true_stddev_satisfaction = np.array([1,2,1.5])

total_satisfaction_arr = []
for i in range(50): #runs the simulation 50 times
    epsilon_greedy_restaurant = EpsilonGreedy(n_restaurants, epsilon)
    total_satisfaction = 0 
    for j in range(n_days):
        restaurant = epsilon_greedy_restaurant.choose_restaurant()
        score = np.random.normal(loc=true_avg_satisfaction[restaurant], scale=true_stddev_satisfaction[restaurant])
        epsilon_greedy_restaurant.update(restaurant,score)
        total_satisfaction += score
    print("Total satisfaction:",total_satisfaction)
    total_satisfaction_arr.append(total_satisfaction)
print("\n\n\n\n\n")
print(np.mean(total_satisfaction_arr) / n_days)  #shows average rating of all the test cases
print(np.std(total_satisfaction_arr) / n_days)   #shows average deviation for all the test case





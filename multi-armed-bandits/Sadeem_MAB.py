#Multi Armed Bandits Implementation - Sadeem Ziyan
#3/4/2026

import random

class Environment:
    def __init__(self, true_means, noise_std = 1.0):
        self.true_means = true_means
        self.noise_std = noise_std

    def pull(self, arm):
        return (random.gauss(self.true_means[arm], self.noise_std))
    
def epsilonGreedyBandit(true_means, steps, epsilon = 0.1, noise_std = 1.0):

    numOfArms = len(true_means)

    estimatedValues = [0.0] * numOfArms
    count = [0] * numOfArms

    reward = 0
    totalReward = 0

    env = Environment(true_means, noise_std)

    for i in range(steps):
        if (random.random() < epsilon):
            arm = random.randrange(numOfArms)
        else:
            bestValue = max(estimatedValues)
            bestArms = [i for i, v in enumerate(estimatedValues) if v == bestValue]
            arm = random.choice(bestArms)

        count[arm] += 1
        reward = env.pull(arm)
        totalReward += reward

        oldEstimate = estimatedValues[arm]
        newEstimate = oldEstimate + (reward - oldEstimate)/(count[arm])
        estimatedValues[arm] = newEstimate

    trueBestArm = max(range(numOfArms), key = lambda i: true_means[i])
    learnedBestArm = max(range(numOfArms), key = lambda i: estimatedValues[i])

    return {
        "true_values": true_means,
        "learned_values": estimatedValues,
        "true_BestArm": trueBestArm,
        "learned_BestArm": learnedBestArm,
        "times_chosen": count,
        "average_reward": round((totalReward/steps), 3),
    }

if __name__ == "__main__":

    numOfArms = 5
    steps = 5000
    epsilon = 0.1
    noise_std = 1.0

    random.seed(23)
    true_means = [random.uniform(-1, 2) for i in range(numOfArms)]

    results = epsilonGreedyBandit(true_means, steps, epsilon, noise_std)

    print("Multi Armed Bandits")
    print("---------")
    print("True values of the arms: ", [round(x,3) for x in results["true_values"]])
    print("Learned values of the arms: ", [round(x,3) for x in results["learned_values"]])
    print("True best arm: ", results["true_BestArm"])
    print("Learned best arm: ", results["learned_BestArm"])
    print("No. of times each arm was tested: ", results["times_chosen"])
    print("Average Reward at the end: ", results["average_reward"])
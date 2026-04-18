import numpy as np
import pandas as pd
import json
import logging
import rl_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS = ["ppo", "dqn", "sarsa", "reinforce", "aac"]

def compute_alignment_reward(model_action, dataset_label):
    """Return +1 if model action matches label, else -1"""
    correct_action = 1 if dataset_label == "reward" else 0
    return 1.0 if model_action == correct_action else -1.0

def train_all_models(csv_path, num_epochs=1):
    """Train all models on the dataset"""
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} samples\n")
    
    results = []
    
    for model_name in MODELS:
        logger.info(f"Training {model_name.upper()}...")
        correct = 0
        total = len(df) * num_epochs
        
        try:
            for epoch in range(num_epochs):
                for idx, row in df.iterrows():
                    try:
                        state = np.array(json.loads(row['state']), dtype=np.float32)
                        label = row['label']
                        
                        # Get model's action
                        image_id = f"{model_name}_epoch{epoch}_idx{idx}"
                        run_func = getattr(rl_models, f'run_{model_name}')
                        action = run_func(image_id, state.tolist())
                        
                        # Compute alignment reward
                        reward = compute_alignment_reward(action, label)
                        
                        # Update model (this saves automatically)
                        update_func = getattr(rl_models, f'update_{model_name}')
                        update_func(image_id, reward)
                        
                        if reward > 0:
                            correct += 1
                    
                    except Exception as e:
                        logger.warning(f"  Sample {idx} failed: {e}")
                        continue
            
            accuracy = correct / total if total > 0 else 0
            logger.info(f"  ✓ {model_name}: {accuracy:.2%} accuracy ({correct}/{total})\n")
            results.append({"model": model_name, "accuracy": accuracy, "correct": correct, "total": total})
        
        except Exception as e:
            logger.error(f"  ✗ {model_name} training failed: {e}\n")
            results.append({"model": model_name, "error": str(e)})
    
    # Print summary
    logger.info("="*50)
    logger.info("TRAINING SUMMARY")
    logger.info("="*50)
    for result in results:
        if "error" in result:
            logger.info(f"{result['model']:15s} | ERROR: {result['error']}")
        else:
            logger.info(f"{result['model']:15s} | {result['accuracy']:.2%} ({result['correct']}/{result['total']})")
    logger.info("="*50)
    
    return results

if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "dataset.csv"
    train_all_models(csv_file)
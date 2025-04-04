import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# Load the provided CSV file
file_path = "newskillspine.csv"
df = pd.read_csv(file_path)

# Extract relevant columns
df = df[["Sequence", "Human Code", "Full Statement", "Item Type"]].dropna()

# Identify Developmental Progressions
developmental_df = df[df["Item Type"] == "Developmental Progression"].copy()

# Generate a "Difficulty Rank" based on sequence (simplified approach)
developmental_df["Difficulty Rank"] = developmental_df.groupby("Human Code").cumcount() + 1

# Simulate Expert Ratings (Placeholder for real data)
np.random.seed(42)
developmental_df["Expert Ratings"] = [np.random.choice([0, 1], size=5).tolist() for _ in range(len(developmental_df))]

# Compute Content Validity Ratio (CVR)
def compute_cvr(ratings):
    N = len(ratings)
    Ne = sum(ratings)
    return (Ne - (N / 2)) / (N / 2)

developmental_df["CVR"] = developmental_df["Expert Ratings"].apply(compute_cvr)

# Compute Transition Gaps
developmental_df["Transition Gap"] = developmental_df.groupby("Human Code")["Difficulty Rank"].diff().fillna(0)

# Compute Progression Coherence Score using Spearman's correlation
coherence_scores = {}
for code, group in developmental_df.groupby("Human Code"):
    if len(group) > 1:
        expected_order = np.arange(len(group))  # Expected order
        actual_order = group["Difficulty Rank"].values
        spearman_corr, _ = spearmanr(expected_order, actual_order)
        coherence_scores[code] = spearman_corr
    else:
        coherence_scores[code] = 1  # If only one item, coherence is perfect

developmental_df["Progression Coherence"] = developmental_df["Human Code"].map(coherence_scores)

# Compute Overall Progression Score
developmental_df["Overall Progression Score"] = (
    0.4 * developmental_df["CVR"] + 0.3 * (1 - developmental_df["Transition Gap"].abs()) + 
    0.3 * developmental_df["Progression Coherence"]
)

# Select relevant output columns
result_df = developmental_df[["Sequence", "Human Code", "Full Statement", "CVR", "Transition Gap", "Progression Coherence", "Overall Progression Score"]]

# Save results to a new file
output_path = "progression_analysis_results.csv"
result_df.to_csv(output_path, index=False)

# Display the result using standard print
print("\nProgression Analysis Results:")
print(result_df)  # This will work in any Python environment

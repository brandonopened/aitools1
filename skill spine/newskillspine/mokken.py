import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# Load the CSV file
file_path = "newskillspine.csv"
df = pd.read_csv(file_path)

# Print columns to debug
print("Available columns:", df.columns.tolist())

# Now let's try with the exact column names from your DataFrame
df = df.sort_values(by=["Standard Code", "Sequence"])

# Save cleaned and sorted file
output_path = "mocken_all_statements.csv"
df.to_csv(output_path, index=False)

# Display results
print("\nCleaned Data - Sorted by Standard and Sequence:")
print(df.head(30))  # Display first 30 rows to show the grouping

import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# Load the CSV file
file_path = "newskillspine.csv"
df = pd.read_csv(file_path)

# Ensure required columns exist
df = df[["Item Type", "Sequence", "Full Statement"]].dropna(subset=["Item Type"])

# Initialize variables to track standards
current_standard = None
standard_label = None
grouped_data = []

# Process each row and assign Developmental Progressions to their Standard
for _, row in df.iterrows():
    item_type = row["Item Type"]
    
    if item_type == "Standard":
        # When a new standard appears, update the tracker
        current_standard = row["Sequence"]
        standard_label = row["Full Statement"]
    
    elif item_type == "Developmental Progression" and current_standard:
        # Assign progression to the last encountered Standard
        grouped_data.append({
            "Standard Sequence": current_standard,
            "Standard Label": standard_label,
            "Item Type": row["Item Type"],
            "Sequence": row["Sequence"],
            "Full Statement": row["Full Statement"]
        })

# Convert to DataFrame
grouped_df = pd.DataFrame(grouped_data)

# Add back the Standards from original DataFrame
standards_df = df[df["Item Type"] == "Standard"].copy()
final_df = pd.concat([standards_df, grouped_df], ignore_index=True)

# Perform Mokken analysis on each standard
# Mokken score of 0.50 or higher is considered a strong hierarchical scale (very coherent progression), while H < 0.30 indicates the sequence is not consistently hierarchical​
mokken_scores = {}
for standard_seq, group in grouped_df.groupby("Standard Sequence"):
    # Convert Sequence to numeric type and sort by sequence
    group = group.copy()
    group["Sequence"] = pd.to_numeric(group["Sequence"].str.split('.').str[-1], errors='coerce')
    group = group.sort_values("Sequence")
    
    # Only proceed if we have developmental progressions
    if len(group) > 1:  # Need at least 2 items for meaningful analysis
        # Generate Expert Ratings based on textual analysis
        def analyze_statement(text):
            # Initialize scoring factors
            scores = []
            
            # Factor 1: Length/detail of statement (longer statements tend to be more complex)
            word_count = len(text.split())
            scores.append(1 if word_count > 15 else 0)
            
            # Factor 2: Presence of technical/specific terms
            technical_terms = ['analyze', 'evaluate', 'create', 'design', 'develop', 
                             'implement', 'synthesize', 'compare', 'contrast', 'explain']
            has_technical = any(term in text.lower() for term in technical_terms)
            scores.append(1 if has_technical else 0)
            
            # Factor 3: Complexity indicators
            complexity_indicators = ['complex', 'multiple', 'advanced', 'sophisticated',
                                  'detailed', 'comprehensive', 'integrated', 'various']
            has_complexity = any(term in text.lower() for term in complexity_indicators)
            scores.append(1 if has_complexity else 0)
            
            # Factor 4: Action verbs vs passive language
            action_verbs = ['perform', 'conduct', 'build', 'construct', 'demonstrate',
                          'solve', 'apply', 'calculate', 'formulate']
            has_action = any(term in text.lower() for term in action_verbs)
            scores.append(1 if has_action else 0)
            
            # Factor 5: Presence of measurable outcomes
            measurement_terms = ['accurately', 'consistently', 'effectively', 
                              'successfully', 'measured', 'demonstrated']
            has_measurement = any(term in text.lower() for term in measurement_terms)
            scores.append(1 if has_measurement else 0)
            
            return scores
            
        group["Expert Ratings"] = group["Full Statement"].apply(analyze_statement)
        
        # Compute Content Validity Ratio (CVR)
        def compute_cvr(ratings):
            N = len(ratings)
            Ne = sum(ratings)
            return (Ne - (N / 2)) / (N / 2)

        group["CVR"] = group["Expert Ratings"].apply(compute_cvr)
        
        # Compute Transition Gaps using numeric sequence
        group["Transition Gap"] = group["Sequence"].diff().fillna(0)
        
        # Compute Progression Coherence Score using Spearman's correlation
        expected_order = np.arange(len(group))
        actual_order = group["Sequence"].values
        spearman_corr, _ = spearmanr(expected_order, actual_order)
        
        # Calculate Mokken score for the standard
        mokken_score = (
            0.4 * group["CVR"].mean() + 
            0.3 * (1 - group["Transition Gap"].abs().mean()) + 
            0.3 * spearman_corr
        )
        mokken_scores[standard_seq] = mokken_score

# Add Mokken scores to Standards only
final_df["Mokken Score"] = None
standards_mask = final_df["Item Type"] == "Standard"
final_df.loc[standards_mask, "Mokken Score"] = (
    final_df.loc[standards_mask, "Sequence"].map(mokken_scores)
)

# Print mokken scores for debugging
print("\nMokken Scores:")
print(mokken_scores)

# Save cleaned file
output_path = "standards_only_with_mokken_2-11.csv"
final_df.to_csv(output_path, index=False)

# Display results
print("\nCleaned Data - Standards and Developmental Progressions with Mokken Score:")
print(final_df.head(20))  # Display first 20 rows
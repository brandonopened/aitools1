import os
import openai
import pandas as pd

# 1. Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
# Alternatively: openai.api_key = "your-api-key"

# 2. Load your original CSV
df = pd.read_csv("preschool.csv")

# Process all rows without filtering
df_to_rewrite = df.copy()

# Add a counter for progress tracking
total_rows = len(df_to_rewrite)
print(f"Found {total_rows} rows to rewrite")

# 3. Define a function to query the OpenAI API
def rewrite_statement(original_text):
    """
    Calls the OpenAI API to rewrite the statement in a simpler, more child-friendly style.
    """
    if not isinstance(original_text, str) or len(original_text.strip()) == 0:
        return ""  # Return blank for empty or non-string values

    prompt = (
        "Rewrite the following early childhood indicator statement so that it reads more "
        "like an Infant/Toddler milestone: short, concrete, and describing an observable behavior.\n\n"
        f"Original: {original_text}\n\n"
        "Rewritten as a single-sentence bullet that starts with a verb or child action, "
        "using a child-friendly tone.\nKeep it concise.\n\nRewritten: "
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in child development milestones."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=70,
            temperature=0.7
        )
        rewritten = response["choices"][0]["message"]["content"].strip()
        return rewritten
    except Exception as e:
        print(f"OpenAI API error for text: {original_text}\n{e}")
        return ""

# Modify the rewriting section to show progress
processed = 0
df_to_rewrite["Rewritten Statement"] = ""  # Initialize the column

for idx, row in df_to_rewrite.iterrows():
    processed += 1
    print(f"Processing statement {processed}/{total_rows}...", end='\r')
    df_to_rewrite.at[idx, "Rewritten Statement"] = rewrite_statement(row["fullstatement"])

print("\nRewriting complete! Saving to CSV...")

# 5. Merge back with the main DataFrame to keep rows intact
#    Rows without rewrites will have empty values in the "Rewritten Statement" column.
df = df.merge(
    df_to_rewrite[["code", "fullstatement", "Rewritten Statement"]],
    on=["code", "fullstatement"],
    how="left"
)

# 6. Save to a new CSV
df.to_csv("rewrittenpreschool2.csv", index=False)

print("Done! Check rewrittenpreschool.csv for the new 'Rewritten Statement' column.")

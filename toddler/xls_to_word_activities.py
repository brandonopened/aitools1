import pandas as pd
from docx import Document
from docx.shared import Pt
from openai import OpenAI
import os

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Load spreadsheet data
def load_spreadsheet(filename):
    data = pd.read_excel(filename, sheet_name=None)
    return data

# Generate activity using OpenAI
def generate_activity(section_type, activity_summary, theme):
    # Create tailored prompts based on section type
    section_prompts = {
        'Language': f"""
        Create an engaging language development activity for toddlers based on the theme "{theme}".
        Activity summary: "{activity_summary}"
        
        Focus on:
        - Vocabulary building
        - Simple sentence structures
        - Interactive communication
        - Age-appropriate language concepts
        
        Provide clear, step-by-step instructions for teachers to implement this activity.
        """,
        
        'Math': f"""
        Design a fun math activity for toddlers based on the theme "{theme}".
        Activity summary: "{activity_summary}"
        
        Focus on:
        - Basic counting
        - Shape recognition
        - Simple patterns
        - Hands-on exploration
        
        Provide clear, step-by-step instructions for teachers to implement this activity.
        """,
        
        'Science': f"""
        Create an engaging science exploration activity for toddlers based on the theme "{theme}".
        Activity summary: "{activity_summary}"
        
        Focus on:
        - Sensory exploration
        - Simple cause and effect
        - Observation skills
        - Natural curiosity
        
        Provide clear, step-by-step instructions for teachers to implement this activity.
        """,
        
        'Art': f"""
        Design a creative art activity for toddlers based on the theme "{theme}".
        Activity summary: "{activity_summary}"
        
        Focus on:
        - Process over product
        - Sensory experiences
        - Fine motor development
        - Creative expression
        
        Provide clear, step-by-step instructions for teachers to implement this activity.
        """,
        
        'Music': f"""
        Create a musical activity for toddlers based on the theme "{theme}".
        Activity summary: "{activity_summary}"
        
        Focus on:
        - Rhythm and movement
        - Simple songs
        - Sound exploration
        - Group participation
        
        Provide clear, step-by-step instructions for teachers to implement this activity.
        """,
        
        'default': f"""
        Create an engaging activity for toddlers based on the theme "{theme}".
        Activity summary: "{activity_summary}"
        
        Focus on:
        - Age-appropriate engagement
        - Skill development
        - Fun and learning
        - Social interaction
        
        Provide clear, step-by-step instructions for teachers to implement this activity.
        """
    }
    
    # Select appropriate prompt based on section type
    prompt = section_prompts.get(section_type, section_prompts['default'])

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=300,
        temperature=0.8
    )

    return response.choices[0].message.content.strip()

# Create a structured Word document
def create_document(activities_dict, output_filename):
    doc = Document()

    # Title
    doc.add_heading('Toddler Weekly Activity Plan', 0)

    # Add activities to document
    for theme, sections in activities_dict.items():
        doc.add_heading(theme, level=1)
        for section, activity_text in sections.items():
            doc.add_heading(section, level=2)
            para = doc.add_paragraph(activity_text)
            para.style.font.size = Pt(12)
        doc.add_page_break()

    doc.save(output_filename)
    print(f"Document saved to {output_filename}")

# Main logic
def main(spreadsheet_filename, output_doc_filename):
    spreadsheet_data = load_spreadsheet(spreadsheet_filename)
    print("\n=== Loading Spreadsheet ===")
    print("Spreadsheet loaded successfully.")

    # Select first sheet for simplicity (modify as needed)
    sheet_name = list(spreadsheet_data.keys())[0]
    df = spreadsheet_data[sheet_name]
    
    # Get the theme name from the first column
    theme_name = df.iloc[0, 0]
    print(f"\n=== Processing Theme ===")
    print(f"Theme: {theme_name}")
    
    # Create activities dictionary with theme structure
    activities_dict = {theme_name: {}}
    
    # Process each row that contains activity information
    current_section = None
    for idx, row in df.iterrows():
        if pd.isna(row.iloc[0]):
            continue
            
        # Check if this is a section header
        if row.iloc[0] in ['Language', 'Math', 'Science', 'Art', 'Music']:
            current_section = row.iloc[0]
            print(f"\n=== Processing {current_section} Section ===")
            continue
            
        # If we have a current section and activity text, generate the activity
        if current_section and not pd.isna(row.iloc[0]):
            activity_summary = row.iloc[0]
            print(f"\nGenerating activity for {current_section}:")
            print(f"Activity Title: {activity_summary}")
            activity_text = generate_activity(current_section, activity_summary, theme_name)
            activities_dict[theme_name][f"{current_section} - {activity_summary}"] = activity_text
            print("✓ Activity generated successfully")

    print("\n=== Creating Document ===")
    create_document(activities_dict, output_doc_filename)
    print(f"Document saved to {output_doc_filename}")

if __name__ == "__main__":
    spreadsheet_filename = 'Toddler _ Themes_for Brandon.xlsx'
    output_doc_filename = 'Generated_Weekly_Activities.docx'

    main(spreadsheet_filename, output_doc_filename)

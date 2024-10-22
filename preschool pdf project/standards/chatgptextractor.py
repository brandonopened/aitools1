import PyPDF2
import pandas as pd

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
    return text

# Function to parse the extracted text into structured data
def parse_standards(text):
    lines = text.split('\n')
    
    # Lists to store the structured data
    human_coding_scheme = []
    full_statement = []
    standard_type = []
    smart_level = []

    # Initialize variables to track the current area, sub-area, and focus area
    current_area = ''
    current_sub_area = ''
    current_focus_area = ''
    current_level = ''
    
    for line in lines:
        line = line.strip()
        
        if "AREA" in line:
            current_area = line
        elif "DEVELOPMENTAL INDICATORS" in line:
            current_sub_area = line
        elif line and line[0].isdigit():
            # This identifies a standard or indicator
            parts = line.split(" ")
            code = parts[0]
            statement = " ".join(parts[1:])
            human_coding_scheme.append(current_area)
            full_statement.append(statement)
            standard_type.append('Developmental Indicator')
            smart_level.append(code)
        elif line.startswith("·"):
            # This is an indicator under a sub-area
            statement = line.replace("·", "").strip()
            human_coding_scheme.append(current_area)
            full_statement.append(statement)
            standard_type.append('Indicator')
            smart_level.append('')

    # Creating a pandas DataFrame
    df = pd.DataFrame({
        'Human Coding Scheme': human_coding_scheme,
        'Full Statement': full_statement,
        'Type': standard_type,
        'Smart Level': smart_level
    })
    
    return df

# Function to save the dataframe to a CSV file
def save_to_csv(df, output_file):
    df.to_csv(output_file, index=False)

# Example usage:
pdf_path = 'va.pdf'
output_csv = 'standards_outputchatgpt.csv'

# Extract text from the PDF
pdf_text = extract_text_from_pdf(pdf_path)

# Parse the text into a structured DataFrame
df_standards = parse_standards(pdf_text)

# Save the DataFrame to a CSV file
save_to_csv(df_standards, output_csv)

print(f"Standards have been extracted and saved to {output_csv}")

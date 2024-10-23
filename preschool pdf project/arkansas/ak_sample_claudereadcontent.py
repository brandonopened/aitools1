import os
import csv
import base64
from io import StringIO
from anthropic import Anthropic

CLAUDE_PROMPT = """
You are a precise data processor specialized in converting educational development standards from images to structured CSV format. You will be shown an image that uses a developmental timeline format with:

A main heading at the top (in a colored banner)
A coded section number and title below it (e.g., "SE1.2 Interacts with peers" but could be different codes/titles)
Age ranges displayed with icons (typically showing progression from birth to 60 months)
Text descriptions in angled boxes showing developmental indicators for each age range
Labels or notes on the right side of the diagram

Process this image into a CSV format with these exact columns:

code: The alphanumeric identifier (main section code and subsections)
statement: The actual text content
type: One of these categories:

"Domain of Development & Learning" (for main heading)
"Domain Component" (for main coded sections)
"Learning Goal" (for specific numbered goals)
"Indicator" (for the descriptive boxes in age ranges)

notes: Any categorization shown on the right side of the image

Follow these rules:

Start with the main domain heading
Include the domain component (coded section)
Include the specific learning goal
For each age range indicator:

List the age range on a separate row
Include each text box as a separate indicator entry
Preserve the exact wording from the image

Maintain hierarchical structure through the coding system
Use empty cells where no value exists (marked by commas in CSV)
Put age ranges in Birth-18m, 9-36m, 19-36m, 37-60m format before their indicators

Important: Format your response ONLY as CSV data with no other text or explanation.

Example:
code,statement,type,notes
SE,Social and Emotional Development,Domain of Development & Learning,
SE1.,Relationships with Others,Domain Component,
SE1.2,Interacts with peers,Learning Goal,
,Birth-18m,,
,"[exact text from box]",Indicator,[right-side category if present]"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_claude_response(response_text):
    # Find where the CSV data starts
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]
    
    # Look for the CSV content
    csv_content = []
    for line in lines:
        if ',' in line:  # Simple check for CSV-like content
            csv_content.append(line)
    
    if not csv_content:
        return []

    # Use StringIO to create a file-like object from the CSV content
    csv_file = StringIO('\n'.join(csv_content))
    reader = csv.reader(csv_file)
    
    # Skip the header row
    next(reader)
    
    # Convert rows to dictionaries with correct field names
    parsed_data = []
    for row in reader:
        if len(row) >= 4:  # Ensure we have enough columns
            parsed_row = {
                'code': row[0],
                'statement': row[1],
                'type': row[2],
                'notes': row[3] if len(row) > 3 else ''
            }
            parsed_data.append(parsed_row)
    
    return parsed_data

def process_images_with_claude(image_folder, output_csv):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if not client.api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set")
        return

    all_data = []

    for filename in os.listdir(image_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            try:
                image_path = os.path.join(image_folder, filename)
                base64_image = encode_image(image_path)
                print(f"Processing image: {filename}")

                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": CLAUDE_PROMPT
                            }
                        ]
                    }
                ]

                response = client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1500,
                    messages=messages
                )

                if response.content:
                    print(f"Processing response for {filename}")
                    parsed_data = parse_claude_response(response.content[0].text)
                    
                    if parsed_data:
                        # Add filename to each row
                        for row in parsed_data:
                            row['filename'] = filename
                        all_data.extend(parsed_data)
                        print(f"Successfully processed {filename}: {len(parsed_data)} rows")
                    else:
                        print(f"No CSV data extracted from {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue

    if all_data:
        # Define columns including filename
        fieldnames = ['filename', 'code', 'statement', 'type', 'notes']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
        print(f"Total rows processed: {len(all_data)}")
    else:
        print("No data to export")

def main():
    image_folder = 'sample'
    output_csv = 'aksampleoutput.csv'

    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
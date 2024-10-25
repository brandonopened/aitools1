import os
import csv
import base64
from io import StringIO
from anthropic import Anthropic

CLAUDE_PROMPT = """You are a precise data processor specialized in converting educational development standards from images to structured CSV format. You will be shown an image that uses a developmental timeline format.

Process this image into CSV format with these exact columns:
code,statement,type,notes

Rules for each field:

1. CODE:
- Main domain code (e.g., "SE" for Social and Emotional)
- Component code (e.g., "SE1.")
- Goal code (e.g., "SE1.1")
- Leave empty for age ranges and indicators

2. STATEMENT:
- Capture complete text, don't truncate
- Include full text from boxes
- Include age ranges as separate entries (e.g., "Birth-8m", "9-18m", etc.)
- Preserve exact wording
- If text wraps across lines, combine into single line

3. TYPE:
Must be one of:
- "Domain of Development & Learning" (main heading)
- "Domain Component" (main coded sections)
- "Learning Goal" (specific numbered goals)
- "Indicator" (for descriptive boxes)
- Empty for age range rows

4. NOTES:
- Include categories shown on right side of diagram
- Leave empty if no category is shown
- Preserve exact capitalization of notes

Output Format:
- Start with domain header
- Follow with component
- Include learning goal
- List each age range as separate row
- Include all indicators under their age range
- Use quotes around fields containing commas
- Maintain exact order from top to bottom, left to right

Example:
code,statement,type,notes
SE,Social and Emotional Development,Domain of Development & Learning,
SE1.,Relationships with Others,Domain Component,
SE1.1,Forms trusting relationships with nurturing adults,Learning Goal,
,Birth-8m,,
,"[complete indicator text]",Indicator,INTERACTIONS
,9-18m,,
,"[complete indicator text]",Indicator,ATTACHMENT

Important:
- Preserve ALL text exactly as written
- Don't truncate or abbreviate content
- Include every age range even if empty
- Maintain hierarchical structure
- Capture all notes from right side

Format response ONLY as CSV data with no other text or explanation."""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_claude_response(response_text):
    # Find where the CSV data starts
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]
    
    # Look for the CSV content
    csv_content = []
    current_line = []
    in_quotes = False
    
    # First, properly join wrapped lines that are part of the same field
    for line in lines:
        # Skip lines until we find the header
        if not csv_content and not line.startswith('code,'):
            continue
            
        # Handle header line
        if line.startswith('code,'):
            csv_content.append(line)
            continue
            
        # Handle content lines
        if '"' in line:
            quotes_count = line.count('"')
            if quotes_count % 2 == 1:  # Odd number of quotes
                if in_quotes:
                    current_line.append(line)
                    csv_content.append(' '.join(current_line))
                    current_line = []
                    in_quotes = False
                else:
                    current_line = [line]
                    in_quotes = True
            else:
                if current_line:
                    current_line.append(line)
                    csv_content.append(' '.join(current_line))
                    current_line = []
                else:
                    csv_content.append(line)
        else:
            if in_quotes:
                current_line.append(line)
            else:
                csv_content.append(line)
    
    # Handle any remaining content
    if current_line:
        csv_content.append(' '.join(current_line))
    
    # Parse the CSV content
    csv_file = StringIO('\n'.join(csv_content))
    reader = csv.reader(csv_file)
    
    # Skip the header row
    header = next(reader)
    
    # Convert rows to dictionaries with correct field names
    parsed_data = []
    current_code = ''
    current_type = ''
    
    for row in reader:
        if len(row) >= 1:
            # Preserve code and type for hierarchy
            if row[0]:  # If there's a code, update current code
                current_code = row[0]
                if len(row) > 2:
                    current_type = row[2]
            
            # Create the parsed row
            parsed_row = {
                'code': row[0] if row[0] else '',
                'statement': row[1] if len(row) > 1 else '',
                'type': row[2] if len(row) > 2 else '',
                'notes': row[3] if len(row) > 3 else ''
            }
            
            # Ensure Indicator type for descriptor boxes
            if (not parsed_row['type'] and parsed_row['statement'] and 
                not any(age in parsed_row['statement'] for age in ['Birth-', '9-', '19-', '37-', '49-'])):
                parsed_row['type'] = 'Indicator'
            
            # Add to parsed data if there's meaningful content
            if parsed_row['statement'] or parsed_row['code']:
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
                print("Full error:")
                import traceback
                print(traceback.format_exc())
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
    output_csv = 'aksampleoutput1.csv'

    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
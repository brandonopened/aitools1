import os
import csv
import base64
from anthropic import Anthropic

CLAUDE_PROMPT = """
Analyze the image and extract information about early childhood development standards. Structure the information into a spreadsheet format with the following columns: statement, type, role, and smartlevel.

The information follows a hierarchical structure:
1. Domain (smartlevel 1.0)
2. Standard (smartlevel 1.x)
3. Age Range (smartlevel 1.x.y)
4. Examples/Actions (smartlevel 1.x.y.z)

Rules for extraction:
1. The 'statement' column should contain the exact text
2. The 'type' column should be: 'domain', 'standard', 'age_range', 'baby_might', or 'teacher_can'
3. The 'role' column should be either 'baby' or 'teacher' for examples/actions, empty for others
4. The 'smartlevel' column uses hierarchical numbering (1, 1.1, 1.1.1, etc.)

For two-column formats:
- Extract baby actions from "THE BABY MIGHT FOR EXAMPLE" column
- Extract teacher actions from "THE TEACHER CAN" column
- Maintain parallel relationships between baby and teacher actions
"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_claude_response(response_text):
    csv_data = response_text.split('\n\n')[-1]
    parsed_data = []
    
    for row in csv.reader(csv_data.splitlines()):
        if len(row) == 4:  # Ensure we have all columns
            parsed_data.append({
                'statement': row[0].strip(),
                'type': row[1].strip(),
                'role': row[2].strip(),
                'smartlevel': row[3].strip()
            })
    
    return parsed_data

def process_images_with_claude(image_folder, output_csv):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if not client.api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set")
        return

    all_data = []
    
    # Read existing data if output CSV exists
    if os.path.exists(output_csv):
        with open(output_csv, 'r', newline='', encoding='utf-8') as input_file:
            reader = csv.DictReader(input_file)
            all_data = list(reader)

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
                    parsed_data = parse_claude_response(response.content[0].text)
                    
                    if parsed_data:
                        for item in parsed_data:
                            item['filename'] = filename
                        all_data.extend(parsed_data)
                        print(f"Processed {filename}")
                    else:
                        print(f"Failed to parse structured data for {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    if all_data:
        keys = ['filename', 'statement', 'type', 'role', 'smartlevel']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")

def main():
    image_folder = 'missing'
    output_csv = 'ok_missingoutput.csv'
    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
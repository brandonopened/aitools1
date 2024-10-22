import os
import csv
import base64
from anthropic import Anthropic

CLAUDE_PROMPT = """
Analyze the image and extract information about early childhood development standards. Structure the information into a spreadsheet format with the following columns: statement, type, and smartlevel.

The information follows a hierarchical structure:
1. Content Area (smartlevel 1)
2. Domain (smartlevel 1.x)
3. Anchor Standard (smartlevel 1.x.x)
4. Age ranges (labels, smartlevel 1.x.x.x)
5. Performance standards (smartlevel 1.x.x.x.x)

Rules for extraction:
1. The 'statement' column should contain the exact text of each item.
2. The 'type' column should categorize each statement as 'Content Area', 'Domain', 'Anchor Standard', 'label', or 'performance standards'.
3. The 'smartlevel' column should use a hierarchical numbering system (e.g., 1, 1.1, 1.1.1, 1.1.1.1, 1.1.1.1.1).
4. Age ranges are considered 'label' type and should be assigned appropriate smartlevels.
5. Performance standards are typically sentence-long descriptions under each age range.
6. Ensure that every row has all three columns filled: statement, type, and smartlevel.
7. Do not create orphan statements. Each statement must have a corresponding type and smartlevel.
8. Maintain consistent column structure throughout the output.
9. ONLY EXTRACT THE EXACT TEXT. Do not summarize or add on to it. 

Extract the information and present it in a CSV format, with each row representing a single item. Ensure that the hierarchy and relationships between items are accurately reflected in the smartlevel numbering.

Please provide the extracted data in CSV format, using commas as separators and enclosing any fields containing commas in double quotes. Ensure each row has exactly three columns.
"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_claude_response(response_text):
    # Split the response to get only the CSV data
    csv_data = response_text.split('\n\n')[-1]
    
    # Parse the CSV data
    parsed_data = []
    for row in csv.reader(csv_data.splitlines()):
        if len(row) == 3:  # Ensure we have statement, type, and smartlevel
            parsed_data.append({
                'statement': row[0].strip(),
                'type': row[1].strip(),
                'smartlevel': row[2].strip()
            })
        else:
            print(f"Skipping malformed row: {row}")
    
    return parsed_data

def process_images_with_claude(image_folder, output_csv):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if not client.api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set")
        return

    all_data = []

    # Check if output CSV exists and read existing data
    if os.path.exists(output_csv):
        with open(output_csv, 'r', newline='', encoding='utf-8') as input_file:
            reader = csv.DictReader(input_file)
            all_data = list(reader)

    for filename in os.listdir(image_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            try:
                image_path = os.path.join(image_folder, filename)
                
                # Encode the image
                base64_image = encode_image(image_path)
                
                print(f"Processing image: {filename}")

                # Prepare the messages with the image and prompt
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
                    print(f"Claude's response for {filename}:")
                    print(response.content[0].text)
                    print("---")

                    parsed_data = parse_claude_response(response.content[0].text)
                    
                    if parsed_data:
                        for item in parsed_data:
                            item['filename'] = filename
                        all_data.extend(parsed_data)
                        print(f"Processed {filename}")
                        print(f"Extracted data: {parsed_data}")
                        print("---")
                    else:
                        print(f"Failed to parse structured data for {filename}")
                else:
                    print(f"No content in response for {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    if all_data:
        keys = ['filename', 'statement', 'type', 'smartlevel']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    image_folder = 'msstandardsoutput'
    output_csv = 'ms_preprocessedoutput.csv'

    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
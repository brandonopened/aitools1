import os
import csv
import base64
from anthropic import Anthropic

CLAUDE_PROMPT = """
Analyze the image and extract educational standards information. Structure the information into a spreadsheet format with the following columns: statement, type, age_group, and identifier.

The information follows this hierarchical structure:
1. Domain (The main subject area, like 'Approaches to Play and Learning')
2. Goal (The broad learning objective)
3. Developmental Indicators (Age-specific benchmarks)

Rules for extraction:
1. The 'statement' column should contain the exact text
2. The 'type' column should be one of:
   - 'domain' (main subject area)
   - 'goal' (broad learning objective)
   - 'developmental_indicator' (specific age-related benchmark)
3. The 'age_group' column should contain one of:
   - 'Infants'
   - 'Younger Toddlers'
   - 'Older Toddlers'
   - 'Younger Preschoolers'
   - 'Older Preschoolers'
   - '' (empty for domain and goal entries)
4. The 'identifier' column should capture any reference codes (e.g., APL-1a, APL-1b)

Format each entry carefully, maintaining the hierarchical relationships between elements.
Include any definitions or explanatory text boxes as entries with appropriate types.
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
                'age_group': row[2].strip(),
                'identifier': row[3].strip()
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
                        print(f"Successfully processed {filename}")
                    else:
                        print(f"Failed to parse structured data for {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    if all_data:
        keys = ['filename', 'statement', 'type', 'age_group', 'identifier']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")

def main():
    image_folder = 'nc_foundations'
    output_csv = 'nc_foundations.csv'
    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
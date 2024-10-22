import os
import csv
import base64
from anthropic import Anthropic

CLAUDE_PROMPT = """
Please analyze the image and extract the following information:

- Theme or overall topic of the page
- Main heading
- Week number and title (if present)

For each activity section (like Math and Science), provide as much of the following information as possible:

- Activity name
- Standards mentioned
- Main instructional text
- List of materials
- Description of any midweek option
- Reflection prompt
- Tips for dual language learners
- Any 'Did You Know' information

Please structure your response in a way that clearly separates different activities and labels each piece of information. If any information is not present for a particular activity, you can omit it.
"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_claude_response_updated(response_text):
    parsed_data = []
    current_activity = {}
    
    for line in response_text.split('\n'):
        line = line.strip()
        if line.startswith('Activity:'):
            if current_activity:
                parsed_data.append(current_activity)
            current_activity = {'Activity': line.split('Activity:')[1].strip()}
        elif ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key in ['Standards', 'Main_Text', 'Materials', 'Midweek_Option', 'Reflect', 'Dual_Language_Learners', 'Did_You_Know']:
                current_activity[key] = value
    
    if current_activity:
        parsed_data.append(current_activity)
    
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

                    parsed_data = parse_claude_response_updated(response.content[0].text)
                    
                    if parsed_data:
                        for item in parsed_data:
                            item['filename'] = filename
                        all_data.extend(parsed_data)
                        print(f"Processed {filename}")
                        print(f"Extracted data: {parsed_data}")
                        print("---")
                    else:
                        print(f"No structured data extracted for {filename}")

                else:
                    print(f"No content in response for {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    if all_data:
        keys = ['filename', 'Activity', 'Standards', 'Main_Text', 'Materials', 'Midweek_Option', 'Reflect', 'Dual_Language_Learners', 'Did_You_Know']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys, extrasaction='ignore')
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    image_folder = 'output'
    output_csv = '5pagesnewpromptoutput.csv'

    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
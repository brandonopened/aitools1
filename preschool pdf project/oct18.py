import os
import csv
import base64
from anthropic import Anthropic

CLAUDE_PROMPT = """
    Analyze the image and extract information for the following fields:

    1. identifier
    2. program
    3. Week
    4. theme
    5. heading
    6. section_title
    7. title
    8. description
    9. type
    10. standard

    Instructions:
    - Fill in all fields based on the information visible in the image - do not summarize, use text word for word
    - If a field is not explicitly mentioned, use your best judgment to infer the information or leave it blank if inference is not possible.
    - The 'type' field should describe the nature of the content (e.g., text, activity, image, etc.).
    - If More than one row is necessary for the text in the images,create a new row for each major element
    - If the 'standard' field is not visible, leave it blank.
    - Provide the extracted information in a structured format, with each field on a new line.

    Please analyze the image and provide the extracted information in a csv format. """

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
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2500,
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
    image_folder = 'output3'
    output_csv = 'betterclaudeoutput.csv'

    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
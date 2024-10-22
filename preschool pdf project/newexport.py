import os
import base64
import csv
import fitz  # PyMuPDF
from PIL import Image
from anthropic import Anthropic

# New prompt for Claude
CLAUDE_PROMPT = """
Analyze the image and follow these steps:

1. Transcription:
   - Transcribe ALL text visible in the image, preserving the original structure and formatting as much as possible.
   - Include headers, subheaders, bullet points, and any other textual elements.

2. Structured Extraction:
   After transcribing, extract and organize the information into the following structure where applicable:
   
   - Day: [The day number of the lesson, if mentioned]
   - Identifier: [Any unique identifier for the lesson or activity]
   - Program: [The name of the educational program]
   - Week: [The week number or identifier]
   - Theme: [The theme of the lesson or week]
   - Heading: [Main heading or title of the section]
   - Section Title: [Title of a specific section within the lesson]
   - Title: [Title of a specific activity or subsection]
   - Description: [Detailed description of the activity or lesson content]
   - Type: [The type of content, e.g., text, activity, image, etc.]
   - Standard: [Any educational standards mentioned]
   - Materials: [List of materials needed for the activity]
   - Vocabulary: [List of vocabulary words introduced]
   - Special Needs Adaptation: [Any modifications for special needs students]
   - Additional Notes: [Any other relevant information that doesn't fit the above categories]

Please provide your response in the following format:

---FULL TRANSCRIPTION---
[Insert the full transcription here]

---STRUCTURED EXTRACTION---
[Insert the structured extraction here, using the categories mentioned above]

If any category is not applicable or the information is not present, you may omit it from the structured extraction.
"""

def pdf_to_images(pdf_path, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pdf = fitz.open(pdf_path)

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_path = os.path.join(output_folder, f'page_{page_num + 1}.png')
        img.save(img_path)

    pdf.close()
    print(f"Conversion complete. Images saved in {output_folder}")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_claude_response(response_text):
    sections = response_text.split('---STRUCTURED EXTRACTION---')
    
    if len(sections) < 2:
        print("Error: Couldn't find structured extraction in Claude's response")
        return None, None
    
    full_transcription = sections[0].replace('---FULL TRANSCRIPTION---', '').strip()
    structured_extraction = sections[1].strip()
    
    # Parse the structured extraction
    parsed_data = {}
    current_key = None
    for line in structured_extraction.split('\n'):
        line = line.strip()
        if line.endswith(':'):
            current_key = line[:-1].lower().replace(' ', '_')
            parsed_data[current_key] = ''
        elif current_key and line:
            parsed_data[current_key] += line + ' '
    
    # Clean up the parsed data
    for key in parsed_data:
        parsed_data[key] = parsed_data[key].strip()
    
    return full_transcription, parsed_data

def process_images_with_claude(image_folder, output_csv):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if not client.api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set")
        return

    all_data = []

    print(f"Contents of {image_folder}:")
    print(os.listdir(image_folder))
    print("---")

    for filename in os.listdir(image_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            try:
                image_path = os.path.join(image_folder, filename)
                base64_image = encode_image(image_path)
                print(f"Image {filename} encoded successfully")

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

                    full_transcription, parsed_data = parse_claude_response(response.content[0].text)
                    
                    if parsed_data:
                        parsed_data['filename'] = filename
                        parsed_data['full_transcription'] = full_transcription
                        all_data.append(parsed_data)
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
        keys = set()
        for item in all_data:
            keys.update(item.keys())
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=list(keys))
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    pdf_path = '5pages.pdf'
    output_folder = 'output2'
    output_csv = 'newoutput.csv'

    pdf_to_images(pdf_path, output_folder)
    process_images_with_claude(output_folder, output_csv)

if __name__ == "__main__":
    main()
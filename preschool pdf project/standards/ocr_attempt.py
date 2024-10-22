import os
import csv
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from anthropic import Anthropic

# Updated prompt for Claude
CLAUDE_PROMPT = """
Analyze the following text extracted from an image of a lesson plan or developmental indicators chart. Organize the information into a structured format as follows:

Human Coding Scheme:
- Area: [Main area of development or learning]
- Sub Area: [Sub-area within the main area]
- Focus Area: [Specific focus within the sub-area]
- Age Group: [Age range for the developmental indicators]
- Developmental Indicator: [Specific indicator of development]
  - Type: [Type of indicator, e.g., "indicator"]
  - SmartLevel: [Numerical identifier for the indicator]

Please provide your response in the following format:

---STRUCTURED EXTRACTION---
Area: [Area name]
Sub Area: [Sub-area number and name]
Focus Area: [Focus area number and name]

[Age Group 1]:
- Developmental Indicator: [Indicator text]
  Type: [indicator type]
  SmartLevel: [numerical identifier]

[Age Group 2]:
- Developmental Indicator: [Indicator text]
  Type: [indicator type]
  SmartLevel: [numerical identifier]

[Continue for all age groups and indicators]

If any category is not applicable or the information is not present, you may omit it from the structured extraction.

Here's the text to analyze:

{text}
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

def extract_text_from_image(image_path):
    return pytesseract.image_to_string(Image.open(image_path))

def parse_claude_response(response_text):
    structured_extraction = response_text.split('---STRUCTURED EXTRACTION---')[1].strip()
    
    # Parse the structured extraction
    parsed_data = {
        'Area': '',
        'Sub Area': '',
        'Focus Area': '',
        'Age Groups': []
    }
    current_age_group = None
    
    for line in structured_extraction.split('\n'):
        line = line.strip()
        if line.startswith('Area:'):
            parsed_data['Area'] = line.split(':', 1)[1].strip()
        elif line.startswith('Sub Area:'):
            parsed_data['Sub Area'] = line.split(':', 1)[1].strip()
        elif line.startswith('Focus Area:'):
            parsed_data['Focus Area'] = line.split(':', 1)[1].strip()
        elif line.endswith(':'):
            current_age_group = {'Age Group': line[:-1], 'Indicators': []}
            parsed_data['Age Groups'].append(current_age_group)
        elif line.startswith('- Developmental Indicator:'):
            indicator = {'text': line.split(':', 1)[1].strip()}
            current_age_group['Indicators'].append(indicator)
        elif line.startswith('Type:'):
            indicator['type'] = line.split(':', 1)[1].strip()
        elif line.startswith('SmartLevel:'):
            indicator['smartlevel'] = line.split(':', 1)[1].strip()
    
    return parsed_data

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
                
                # Extract text using OCR
                extracted_text = extract_text_from_image(image_path)
                print(f"Text extracted from {filename}")

                # Prepare the prompt with the extracted text
                prompt = CLAUDE_PROMPT.format(text=extracted_text)

                messages = [
                    {
                        "role": "user",
                        "content": prompt
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
                        parsed_data['filename'] = filename
                        parsed_data['full_text'] = extracted_text
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
        # Flatten the nested structure for CSV output
        flattened_data = []
        for item in all_data:
            base_row = {
                'filename': item['filename'],
                'Area': item['Area'],
                'Sub Area': item['Sub Area'],
                'Focus Area': item['Focus Area']
            }
            for age_group in item['Age Groups']:
                for indicator in age_group['Indicators']:
                    row = base_row.copy()
                    row['Age Group'] = age_group['Age Group']
                    row['Developmental Indicator'] = indicator['text']
                    row['Type'] = indicator.get('type', '')
                    row['SmartLevel'] = indicator.get('smartlevel', '')
                    flattened_data.append(row)
        
        keys = set()
        for item in flattened_data:
            keys.update(item.keys())
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=list(keys))
            dict_writer.writeheader()
            dict_writer.writerows(flattened_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    pdf_path = 'va.pdf'
    output_folder = 'standardsoutput'
    output_csv = 'va_output.csv'

    pdf_to_images(pdf_path, output_folder)
    process_images_with_claude(output_folder, output_csv)

if __name__ == "__main__":
    main()
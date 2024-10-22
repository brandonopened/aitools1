import os
import base64
import csv
import json
import requests
import fitz  # PyMuPDF
from PIL import Image

def pdf_to_images(pdf_path, output_folder):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Open the PDF file
    pdf = fitz.open(pdf_path)

    # Iterate through each page
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        
        # Render page to an image
        pix = page.get_pixmap()
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save the image
        img_path = os.path.join(output_folder, f'page_{page_num + 1}.png')
        img.save(img_path)

    pdf.close()
    print(f"Conversion complete. Images saved in {output_folder}")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_table(response_text):
    required_fields = [
        'identifier', 'program', 'Week', 'theme', 'force theme', 'heading',
        'section_title', 'title', 'description', 'type', 'standard'
    ]
    data = {field: '' for field in required_fields}
    
    # Try to parse as markdown table
    lines = response_text.strip().split('\n')
    if len(lines) > 2 and '|' in lines[0]:
        headers = [header.strip() for header in lines[0].split('|') if header.strip()]
        for line in lines[1:]:
            if '|' not in line:
                continue
            values = [value.strip() for value in line.split('|') if value.strip()]
            if len(values) == len(headers):
                for header, value in zip(headers, values):
                    if header.lower() in data:
                        data[header.lower()] = value
    else:
        # If not a table, try to extract key-value pairs
        for line in lines:
            for field in required_fields:
                if field.lower() in line.lower():
                    value = line.split(':', 1)[-1].strip()
                    data[field] = value
                    break
    
    return data

def process_images_with_ollama(image_folder, output_csv):
    url = "http://localhost:11434/api/generate"
    headers = {
        "Content-Type": "application/json"
    }

    prompt = """
    You will be given text describing early childhood development standards. Your task is to extract and structure this information into a spreadsheet format with the following columns: statement, type, and smartlevel.

The text follows a hierarchical structure:
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

Extract the information and present it in a CSV format, with each row representing a single item. Ensure that the hierarchy and relationships between items are accurately reflected in the smartlevel numbering.

Here's the text to process:

{text}

Please provide the extracted data in CSV format, using commas as separators and enclosing any fields containing commas in double quotes.
"""
    """

    all_data = []
    required_fields = [
        'identifier', 'program', 'Week', 'theme', 'force theme', 'heading',
        'section_title', 'title', 'description', 'type', 'standard'
    ]

    for filename in os.listdir(image_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(image_folder, filename)
            base64_image = encode_image(image_path)

            data = {
                "model": "llava",  # You may need to adjust this based on the available models
                "prompt": f"{prompt}\n\nImage: [base64 encoded image data]",
                "stream": False,
                "images": [base64_image]
            }

            response = requests.post(url, headers=headers, data=json.dumps(data))

            if response.status_code == 200:
                response_data = json.loads(response.text)
                table_data = parse_table(response_data["response"])
                
                # Ensure all required fields are present
                for field in required_fields:
                    if field not in table_data:
                        table_data[field] = ''
                
                table_data['filename'] = filename
                all_data.append(table_data)

                print(f"Processed {filename}")
            else:
                print(f"Error processing {filename}:", response.status_code, response.text)

    if all_data:
        keys = required_fields + ['filename']
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    pdf_path = 'msfirstfive.pdf'
    output_folder = 'msoutput'
    output_csv = 'ms_ocr_attempt1.csv'

    pdf_to_images(pdf_path, output_folder)
    process_images_with_ollama(output_folder, output_csv)

if __name__ == "__main__":
    main()
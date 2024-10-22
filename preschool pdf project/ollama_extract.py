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
    try:
        pdf = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return

    # Iterate through each page
    for page_num in range(len(pdf)):
        try:
            page = pdf[page_num]
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_path = os.path.join(output_folder, f'page_{page_num + 1}.png')
            img.save(img_path)
            print(f"Saved image for page {page_num + 1} at {img_path}")
        except Exception as e:
            print(f"Error processing page {page_num + 1}: {e}")

    pdf.close()
    print(f"Conversion complete. Images saved in {output_folder}")

def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def parse_table(response_text):
    required_fields = [
        'identifier', 'program', 'Week', 'theme', 'force theme', 'heading',
        'section_title', 'title', 'description', 'type', 'standard'
    ]
    data = {field: '' for field in required_fields}
    
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
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                if key in data:
                    data[key] = value.strip()

    return data

def process_images_with_ollama(image_folder, output_csv, prompt="", url="", headers=None):
    all_data = []
    required_fields = ['identifier', 'program', 'Week', 'theme', 'force theme', 'heading',
                       'section_title', 'title', 'description', 'type', 'standard']

    for filename in os.listdir(image_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(image_folder, filename)
            base64_image = encode_image(image_path)
            if not base64_image:
                continue

            data = {
                "model": "llava",  # Adjust based on your actual model
                "prompt": f"{prompt}\n\nImage: [base64 encoded image data]",
                "stream": False,
                "images": [base64_image]
            }

            try:
                response = requests.post(url, headers=headers, data=json.dumps(data))
                if response.status_code == 200:
                    response_data = json.loads(response.text)
                    table_data = parse_table(response_data.get("response", ""))
                    
                    for field in required_fields:
                        if field not in table_data:
                            table_data[field] = ''
                    
                    table_data['filename'] = filename
                    all_data.append(table_data)
                    print(f"Processed {filename}")
                else:
                    print(f"Error processing {filename}: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error making API request for {filename}: {e}")

    if all_data:
        keys = required_fields + ['filename']
        try:
            with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
                dict_writer = csv.DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(all_data)
            print(f"Data exported to {output_csv}")
        except Exception as e:
            print(f"Error writing to CSV: {e}")
    else:
        print("No data to export")

def main():
    pdf_path = 'msfirstfive.pdf'
    output_folder = 'msoutput'
    output_csv = 'ms_ocr_attempt2.csv'

    pdf_to_images(pdf_path, output_folder)
    process_images_with_ollama(output_folder, output_csv)

if __name__ == "__main__":
    main()

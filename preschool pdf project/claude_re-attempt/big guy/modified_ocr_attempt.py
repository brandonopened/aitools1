
import os
import csv
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from anthropic import Anthropic

# Updated prompt for Claude
CLAUDE_PROMPT = """
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

def process_images_with_claude(output_folder, output_csv):
    client = Anthropic(api_key="your_anthropic_key")
    all_data = []
    
    # Check if the CSV exists already and if it needs to append data
    write_header = not os.path.exists(output_csv)
    
    for filename in os.listdir(output_folder):
        if filename.endswith(".png"):
            image_path = os.path.join(output_folder, filename)
            
            # Use pytesseract to extract text from the image
            extracted_text = pytesseract.image_to_string(Image.open(image_path))
            
            prompt = CLAUDE_PROMPT.format(text=extracted_text)
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            try:
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
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            
            # Write header only if we're starting a new file
            if write_header:
                dict_writer.writeheader()
                
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    pdf_path = 'ms_standardsonly.pdf'
    output_folder = 'msstandardsoutput'
    output_csv = 'ms_testoutputnew_fixed.csv'

    pdf_to_images(pdf_path, output_folder)
    process_images_with_claude(output_folder, output_csv)

if __name__ == "__main__":
    main()

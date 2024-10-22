import os
import base64
import csv
import fitz  # PyMuPDF
from PIL import Image
from anthropic import Anthropic

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

def parse_response(response_text):
    required_fields = [
<<<<<<< Updated upstream
        'identifier', 'program', 'Week', 'theme', 'force theme', 'heading',
=======
        'identifier', 'program', 'week', 'theme', 'heading',
>>>>>>> Stashed changes
        'section_title', 'title', 'description', 'type', 'standard'
    ]
    data = {field: '' for field in required_fields}
    
    lines = response_text.strip().split('\n')
<<<<<<< Updated upstream
    for line in lines:
        for field in required_fields:
            if line.lower().startswith(f"{field.lower()}:"):
                value = line.split(':', 1)[1].strip()
                data[field] = value
                break
=======
    current_field = None
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            if key in required_fields:
                data[key] = value
                current_field = key
        elif current_field:
            data[current_field] += ' ' + line.strip()
    
    if all(value == '' for value in data.values()):
        for field in required_fields:
            if field.capitalize() in response_text:
                index = response_text.index(field.capitalize())
                end_index = response_text.find('\n', index)
                if end_index == -1:
                    end_index = len(response_text)
                data[field] = response_text[index:end_index].split(':', 1)[-1].strip()
>>>>>>> Stashed changes
    
    return data

def process_images_with_claude(image_folder, output_csv):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if not client.api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set")
        return

    prompt = """
<<<<<<< Updated upstream
    Analyze the provided image of a curriculum page and extract the information into a structured format. For each distinct section or content block in the image:

Generate a unique identifier based on the content type and subject (e.g., PS.MSM.1.PC.abc.materials for preschool, My School and Me, Week 1, Practice Centers, ABC section, materials list).
Identify the program (e.g., Preschool), week number, and theme.
Determine the main heading (e.g., Practice Centers) and section title (e.g., ABC, Fine Motor, Writer's Corner).
Extract the title of each content block (e.g., Materials, Midweek Option, Special Needs Adaptation).
Capture the full description or content for each block.
Categorize the content type (e.g., text, materials, Midweek).
If present, extract any learning standards associated with the content.
Organize this information into a table with the following columns:
identifier, program, Week, theme, force theme (y or n), heading, section_title, title, description, type, standard

Ensure that each distinct piece of information (e.g., materials list, midweek options, special adaptations) is given its own row in the output table. Maintain the hierarchical structure of the information as presented in the original image.
=======
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

    Please analyze the image and provide the extracted information.
>>>>>>> Stashed changes
    """

    all_data = []
    required_fields = [
<<<<<<< Updated upstream
        'identifier', 'program', 'Week', 'theme', 'force theme', 'heading',
        'section_title', 'title', 'description', 'type', 'standard'
    ]
=======
        'identifier', 'program', 'week', 'theme', 'heading',
        'section_title', 'title', 'description', 'type', 'standard'
    ]

    print(f"Contents of {image_folder}:")
    print(os.listdir(image_folder))
    print("---")
>>>>>>> Stashed changes

    for filename in os.listdir(image_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            try:
                image_path = os.path.join(image_folder, filename)
                base64_image = encode_image(image_path)
                print(f"Image {filename} encoded successfully")

<<<<<<< Updated upstream
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
=======
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
                                "text": prompt
>>>>>>> Stashed changes
                            }
                        ]
                    }
                ]

<<<<<<< Updated upstream
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=messages
            )

            data = parse_response(response.content[0].text)
            data['filename'] = filename
            all_data.append(data)
=======
                response = client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1000,
                    messages=messages
                )

                if response.content:
                    print(f"Claude's response for {filename}:")
                    print(response.content[0].text)
                    print("---")
>>>>>>> Stashed changes

                    parsed_data = parse_response(response.content[0].text)
                    parsed_data['filename'] = filename
                    all_data.append(parsed_data)

                    print(f"Processed {filename}")
                    print(f"Extracted data: {parsed_data}")
                    print("---")
                else:
                    print(f"No content in response for {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    if all_data:
        keys = required_fields + ['filename']
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")
    else:
        print("No data to export")

def main():
    pdf_path = '5pages.pdf'
    output_folder = 'output'
<<<<<<< Updated upstream
    output_csv = 'multipageoutput.csv'
=======
    output_csv = 'multioutput.csv'
>>>>>>> Stashed changes

    pdf_to_images(pdf_path, output_folder)
    process_images_with_claude(output_folder, output_csv)

if __name__ == "__main__":
    main()
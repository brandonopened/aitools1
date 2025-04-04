import os
import csv
import base64
import requests
import json

OLLAMA_PROMPT = """
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

def parse_ollama_response(response_text):
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

def call_ollama_api(base64_image, prompt):
    url = "http://localhost:11434/api/generate"  # Default Ollama API endpoint
    
    payload = {
        "model": "llama3-gradient:8b",
        "prompt": prompt,
        "images": [base64_image],
        "stream": False
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json().get('response', '')
    else:
        raise Exception(f"API call failed with status code {response.status_code}: {response.text}")

def process_images_with_ollama(image_folder, output_csv):
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

                # Call Ollama API
                response_text = call_ollama_api(base64_image, OLLAMA_PROMPT)

                if response_text:
                    print(f"Ollama's response for {filename}:")
                    print(response_text)
                    print("---")

                    parsed_data = parse_ollama_response(response_text)
                    
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
    image_folder = 'sample'
    output_csv = 'ollama_output.csv'

    process_images_with_ollama(image_folder, output_csv)

def process_csv(input_csv, output_csv):
    with open(input_csv, mode='r') as infile, open(output_csv, mode='w', newline='') as outfile:
        reader = csv.DictReader(infile)
        # Update fieldnames to include your existing columns plus the levels
        fieldnames = ['abbreviation', 'title', 'category_name', 'subcategory_name', 'tags', 
                     'description', 'is_language', 'is_software', 'keywords', 
                     'Level 1', 'Level 2', 'Level 3', 'Level 4']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        # Process only the first 5 rows
        for i, row in enumerate(reader):
            if i >= 5:  # Stop after processing 5 rows
                break
                
            skill_title = row['title']
            skill_description = row['description']
            try:
                proficiency_levels = generate_skill_descriptions(skill_title, skill_description)
                row.update(proficiency_levels)
            except Exception as e:
                row['Level 1'] = row['Level 2'] = row['Level 3'] = row['Level 4'] = f"Error: {e}"
            
            writer.writerow(row)
            print(f"Processed row {i+1}: {skill_title}")

if __name__ == "__main__":
    main() 
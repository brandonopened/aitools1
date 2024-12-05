import os
import csv
import base64
import re
from anthropic import Anthropic

CLAUDE_PROMPT = """
Analyze the image and extract educational standards information. Structure the information into a spreadsheet format with the following columns: Code, statement, type, SmartLevel

Page Types and Rules:

1. For Developmental Indicator Pages:
   When you see "Goal APL-X:" or similar goal headers:
   - Goal gets type 'goal', Code "Goal APL-X", SmartLevel "1.X"
   - Age group headers get type 'label', empty Code, SmartLevel "1.X.Y" where Y is:
     1: Infants
     2: Younger Toddlers
     3: Older Toddlers
     4: Younger Preschoolers
     5: Older Preschoolers
   - Individual indicators get type 'developmental_indicator', Code as shown (e.g., "APL-1a"), SmartLevel "1.X.Y.Z"

2. For Strategy Pages:
   When you see "Strategies for..." headers:
   - Main header gets type 'domain', empty Code, SmartLevel "1.0"
   - Subject area gets type 'subdomain', empty Code, SmartLevel "1.1"
   - Numbered strategies get type 'strategy', number as Code, SmartLevel "1.1.X"

VERY IMPORTANT:
1. Always extract the exact APL codes that appear in the text (e.g., APL-1a, APL-2b)
2. Maintain proper SmartLevel numbering across sections
3. Include complete text of each item, including examples and parenthetical content
4. Preserve hierarchical relationships between elements

Sample outputs for different page types:

Developmental Indicators:
Goal APL-1,Children show curiosity and express interest in the world around them.,goal,1.1
,Infants,label,1.1.1
APL-1a,Show interest in others...,developmental_indicator,1.1.1.1

Strategy Page:
,Strategies for Infants and Toddlers,domain,1.0
,Curiosity Information-Seeking and Eagerness,subdomain,1.1
1,Provide safe spaces...,strategy,1.1.1
"""

def determine_page_type(text):
    """Helper to determine if page is strategy or developmental indicators"""
    if "Strategies for" in text:
        return "strategy"
    elif re.search(r"Goal [A-Z]+-\d+:", text):
        return "developmental"
    return "unknown"

def extract_goal_number(text):
    """Extract the goal number from APL codes"""
    match = re.search(r"APL-(\d+)", text)
    return int(match.group(1)) if match else None

def parse_claude_response(response_text):
    csv_data = response_text.split('\n\n')[-1]
    parsed_data = []
    current_goal = None
    current_age_group = None
    
    for row in csv.reader(csv_data.splitlines()):
        if len(row) == 4:
            code, statement, type_, smartlevel = [x.strip() for x in row]
            
            # Extract goal number if present
            if type_ == 'goal':
                goal_match = re.search(r"APL-(\d+)", code)
                if goal_match:
                    current_goal = int(goal_match.group(1))
            
            # Update age group tracking
            if type_ == 'label':
                current_age_group = {
                    'Infants': 1,
                    'Younger Toddlers': 2,
                    'Older Toddlers': 3,
                    'Younger Preschoolers': 4,
                    'Older Preschoolers': 5
                }.get(statement)
            
            # Extract APL code if present in statement
            if not code and 'APL-' in statement:
                code_match = re.search(r'APL-\d+[a-z]', statement)
                if code_match:
                    code = code_match.group(0)
            
            # Validate and fix SmartLevel numbering
            if current_goal:
                if type_ == 'goal':
                    smartlevel = f"1.{current_goal}"
                elif type_ == 'label' and current_age_group:
                    smartlevel = f"1.{current_goal}.{current_age_group}"
                elif type_ == 'developmental_indicator' and current_age_group:
                    indicator_num = len([x for x in parsed_data 
                                      if x['type'] == 'developmental_indicator' and 
                                         x.get('current_age_group') == current_age_group])
                    smartlevel = f"1.{current_goal}.{current_age_group}.{indicator_num + 1}"
            
            parsed_data.append({
                'Code': code,
                'statement': statement,
                'type': type_,
                'SmartLevel': smartlevel,
                'current_goal': current_goal,
                'current_age_group': current_age_group
            })
    
    return parsed_data

def process_images_with_claude(image_folder, output_csv):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if not client.api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set")
        return

    all_data = []
    current_goal = None
    current_age_group = None
    
    # Process files in sorted order to maintain sequence
    for filename in sorted(os.listdir(image_folder)):
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
                    max_tokens=2000,
                    messages=messages
                )

                if response.content:
                    parsed_data = parse_claude_response(response.content[0].text)
                    
                    if parsed_data:
                        # Update current goal and age group from previous file if needed
                        if current_goal:
                            parsed_data[0]['current_goal'] = current_goal
                        if current_age_group:
                            parsed_data[0]['current_age_group'] = current_age_group
                        
                        for item in parsed_data:
                            item['filename'] = filename
                            # Update tracking variables for next file
                            if item['current_goal']:
                                current_goal = item['current_goal']
                            if item['current_age_group']:
                                current_age_group = item['current_age_group']
                            
                            # Clean up tracking fields before saving
                            del item['current_goal']
                            del item['current_age_group']
                            
                        all_data.extend(parsed_data)
                        print(f"Successfully processed {filename}")
                    else:
                        print(f"Failed to parse structured data for {filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    if all_data:
        keys = ['filename', 'Code', 'statement', 'type', 'SmartLevel']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        print(f"Data exported to {output_csv}")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    image_folder = 'nc_foundations'
    output_csv = 'nc_foundations.csv'
    process_images_with_claude(image_folder, output_csv)

if __name__ == "__main__":
    main()
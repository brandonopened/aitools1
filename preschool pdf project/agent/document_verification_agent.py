import os
import csv
import base64
from anthropic import Anthropic
from typing import List, Dict

class DocumentVerificationAgent:
    def __init__(self, api_key: str = None):
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        if not self.client.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def verify_content(self, image_path: str, csv_data: List[Dict]) -> List[Dict]:
        """
        Verify CSV data against the original PDF page and suggest corrections
        """
        verification_prompt = """
        Review this CSV content against the image and provide corrections in this exact format:

        DISCREPANCIES:
        - List each issue found, one per line
        
        CORRECTIONS:
        statement,type,smartlevel
        [any corrected entries, one per line]
        
        MISSING:
        statement,type,smartlevel
        [any missing entries, one per line]

        If there are no corrections or missing entries for a section, include the section header but leave it empty.
        Always include all three sections in your response, even if empty.

        CSV content to verify:
        {csv_content}
        """

        # Format CSV content for the prompt
        csv_content = "\n".join([
            f"{row['statement']},{row['type']},{row['smartlevel']}"
            for row in csv_data
        ])

        base64_image = self.encode_image(image_path)
        
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
                        "text": verification_prompt.format(csv_content=csv_content)
                    }
                ]
            }
        ]

        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1500,
            messages=messages
        )

        return self._parse_verification_response(response.content[0].text, csv_data)

    def _parse_verification_response(self, response: str, original_data: List[Dict]) -> List[Dict]:
        """
        Parse Claude's verification response and update the data accordingly
        """
        updated_data = original_data.copy()
        
        # Split response into sections
        sections = response.lower().split('discrepancies:')
        if len(sections) < 2:
            print("Warning: Could not find DISCREPANCIES section")
            return updated_data
            
        main_content = sections[1]
        
        # Extract corrections
        corrections = []
        if 'corrections:' in main_content:
            corrections_section = main_content.split('corrections:')[1].split('missing:')[0]
            for line in corrections_section.strip().split('\n'):
                if ',' in line and not line.startswith('-'):
                    try:
                        statement, type_, smartlevel = [x.strip() for x in line.split(',', 2)]
                        corrections.append({
                            'statement': statement,
                            'type': type_,
                            'smartlevel': smartlevel
                        })
                    except ValueError as e:
                        print(f"Warning: Skipping malformed correction line: {line}")
                        continue

        # Extract missing entries
        missing_entries = []
        if 'missing:' in main_content:
            missing_section = main_content.split('missing:')[1].strip()
            for line in missing_section.split('\n'):
                if ',' in line and not line.startswith('-'):
                    try:
                        statement, type_, smartlevel = [x.strip() for x in line.split(',', 2)]
                        missing_entries.append({
                            'statement': statement,
                            'type': type_,
                            'smartlevel': smartlevel
                        })
                    except ValueError as e:
                        print(f"Warning: Skipping malformed missing line: {line}")
                        continue

        # Apply corrections
        for correction in corrections:
            found = False
            for i, entry in enumerate(updated_data):
                if entry['smartlevel'] == correction['smartlevel']:
                    updated_data[i] = correction
                    found = True
                    break
            if not found:
                print(f"Warning: No matching entry found for correction with smartlevel {correction['smartlevel']}")

        # Add missing entries
        updated_data.extend(missing_entries)

        # Sort by smartlevel
        try:
            updated_data.sort(key=lambda x: [int(n) for n in x['smartlevel'].split('.')])
        except (ValueError, AttributeError) as e:
            print(f"Warning: Error sorting data: {e}")
            # If sorting fails, return unsorted data
            pass

        return updated_data

    def process_document(self, image_folder: str, input_csv: str, output_csv: str):
        """
        Process an entire document, verifying each page against the CSV
        """
        # Read existing CSV data
        try:
            with open(input_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
        except Exception as e:
            print(f"Error reading input CSV {input_csv}: {e}")
            return

        # Group CSV data by filename
        data_by_file = {}
        for row in csv_data:
            filename = row['filename']
            if filename not in data_by_file:
                data_by_file[filename] = []
            data_by_file[filename].append(row)

        # Process each image and verify its content
        verified_data = []
        for filename in os.listdir(image_folder):
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                print(f"Verifying content for {filename}")
                image_path = os.path.join(image_folder, filename)
                
                # Get corresponding CSV data for this image
                page_data = data_by_file.get(filename, [])
                if not page_data:
                    print(f"No CSV data found for {filename}")
                    continue

                try:
                    # Verify and correct the content
                    verified_page_data = self.verify_content(image_path, page_data)
                    for item in verified_page_data:
                        item['filename'] = filename
                    verified_data.extend(verified_page_data)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    continue

        # Write verified data to output CSV
        if verified_data:
            try:
                keys = ['filename', 'statement', 'type', 'smartlevel']
                with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(verified_data)
                print(f"Verified data exported to {output_csv}")
            except Exception as e:
                print(f"Error writing output CSV {output_csv}: {e}")
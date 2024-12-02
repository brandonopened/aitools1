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
        I'll show you a CSV extract of document content and the original image. Please:
        1. Verify the statement text matches exactly
        2. Confirm the hierarchy (smartlevel) is correct
        3. Verify the type classifications are accurate
        4. Check for any missing content
        5. Suggest specific corrections if needed

        CSV content to verify:
        {csv_content}

        Please review the image against this content and provide:
        1. A list of any discrepancies found
        2. Corrected entries in CSV format for any errors
        3. Any missing entries in CSV format
        
        Format the response as:
        DISCREPANCIES:
        - List each issue found
        
        CORRECTIONS:
        statement,type,smartlevel
        [corrected entries]
        
        MISSING:
        statement,type,smartlevel
        [missing entries]
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
        sections = response.split('\n\n')
        updated_data = original_data.copy()
        
        # Find the CORRECTIONS and MISSING sections
        corrections_start = None
        missing_start = None
        
        for i, section in enumerate(sections):
            if section.startswith('CORRECTIONS:'):
                corrections_start = i + 1
            elif section.startswith('MISSING:'):
                missing_start = i + 1

        # Apply corrections
        if corrections_start:
            corrections = []
            i = corrections_start
            while i < len(sections) and not sections[i].startswith('MISSING:'):
                if ',' in sections[i]:
                    statement, type_, smartlevel = sections[i].strip().split(',')
                    corrections.append({
                        'statement': statement,
                        'type': type_,
                        'smartlevel': smartlevel
                    })
                i += 1
            
            # Update existing entries with corrections
            for correction in corrections:
                for i, entry in enumerate(updated_data):
                    if entry['smartlevel'] == correction['smartlevel']:
                        updated_data[i] = correction
                        break

        # Add missing entries
        if missing_start:
            missing_entries = []
            for line in sections[missing_start].split('\n'):
                if ',' in line:
                    statement, type_, smartlevel = line.strip().split(',')
                    missing_entries.append({
                        'statement': statement,
                        'type': type_,
                        'smartlevel': smartlevel
                    })
            updated_data.extend(missing_entries)

        # Sort by smartlevel
        updated_data.sort(key=lambda x: [int(n) for n in x['smartlevel'].split('.')])
        
        return updated_data

    def process_document(self, image_folder: str, input_csv: str, output_csv: str):
        """
        Process an entire document, verifying each page against the CSV
        """
        # Read existing CSV data
        with open(input_csv, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)

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

                # Verify and correct the content
                verified_page_data = self.verify_content(image_path, page_data)
                for item in verified_page_data:
                    item['filename'] = filename
                verified_data.extend(verified_page_data)

        # Write verified data to output CSV
        if verified_data:
            keys = ['filename', 'statement', 'type', 'smartlevel']
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(verified_data)
            print(f"Verified data exported to {output_csv}")
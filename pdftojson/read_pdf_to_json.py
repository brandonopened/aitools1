import json
import re
import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import PyPDF2 # Added import for PDF reading

# --- PDF Text Extraction Function ---
def extract_text_from_pdf(pdf_path):
    """
    Extracts text content from all pages of a PDF file.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        str: The concatenated text content from the PDF.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        Exception: For other potential errors during PDF processing.
    """
    print(f"Attempting to read PDF: {pdf_path}")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Error: The file '{pdf_path}' was not found.")

    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file: # Open in binary read mode
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(reader.pages)
            print(f"Found {num_pages} page(s) in the PDF.")
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += f"--- PAGE {page_num + 1} ---\n\n" # Add page marker
                    text += page_text + "\n\n"
                else:
                    print(f"Warning: Could not extract text from page {page_num + 1}.")
        print("Successfully extracted text from PDF.")
        return text
    except Exception as e:
        print(f"Error reading PDF file '{pdf_path}': {e}")
        raise # Re-raise the exception


# --- LLM Interaction Function (Using Gemini 1.5 Pro) ---
# (This function remains the same as the previous version)
def call_llm_api(prompt):
    """
    Sends the prompt to the Gemini 1.5 Pro API and returns the generated text response.

    Args:
        prompt (str): The prompt string to send to the LLM.

    Returns:
        str: The text content generated by the LLM.

    Raises:
        Exception: If the API call fails or returns an error (including safety blocks).
    """
    # Assumes API key is configured via environment variable GOOGLE_API_KEY
    # or other standard google-cloud-aiplatform authentication methods.
    # If needed: genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    # --- Configuration ---
    model_name = 'gemini-1.5-pro-latest'
    generation_config = {
        "temperature": 0.3, # Lower temperature for more predictable JSON
        "top_p": 1.0,
        "top_k": 32,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain", # Ensure plain text for easier parsing
    }
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    # --- API Call ---
    try:
        print(f"Initializing Gemini model: {model_name}")
        model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings=safety_settings,
            generation_config=generation_config,
        )

        print("Sending request to Gemini API...")
        response = model.generate_content(prompt)
        print("Received response from Gemini API.")

        # --- Response Validation ---
        if not response.candidates:
            reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Unknown"
            raise ValueError(f"API returned no candidates. Prompt possibly blocked for reason: {reason}")

        candidate = response.candidates[0]

        if candidate.finish_reason.name != "STOP":
             raise ValueError(f"API call finished with reason '{candidate.finish_reason.name}', not 'STOP'. Check safety ratings or token limits.")

        if candidate.safety_ratings:
             for rating in candidate.safety_ratings:
                 if rating.probability not in [HarmBlockThreshold.NEGLIGIBLE, HarmBlockThreshold.LOW]:
                     print(f"Warning: Potential safety issue detected for category {rating.category.name} with probability {rating.probability.name}")
                     # Consider raising ValueError here if strict safety is needed

        if hasattr(candidate.content, 'parts') and candidate.content.parts:
             return candidate.content.parts[0].text
        elif hasattr(response, 'text'):
             return response.text
        else:
             raise ValueError("API response structure does not contain expected text content ('parts' or 'text').")

    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        raise


# --- Main Extraction Function ---
# (This function remains the same as the previous version)
def extract_content_to_json(document_text, target_json_schema_example):
    """
    Uses the Gemini 1.5 Pro LLM to extract content from document_text based on the
    structure exemplified by target_json_schema_example.

    Args:
        document_text (str): The full text content from the source document (e.g., PDF).
        target_json_schema_example (str): A string containing the example JSON structure
                                           to guide the LLM.

    Returns:
        str: A JSON string containing the extracted data, or a JSON string with an error message.
    """
    max_doc_length = 900000
    max_schema_length = 50000
    document_snippet = document_text[:max_doc_length]
    schema_snippet = target_json_schema_example[:max_schema_length]

    prompt = f"""
    Analyze the following document text, which is extracted from a curriculum guide (likely a PDF).
    Your task is to extract its content and structure it into a JSON format that strictly adheres
    to the structure, data types, and nesting shown in the example JSON schema provided below.

    Document Text:
    --- START DOCUMENT TEXT ---
    {document_snippet}
    --- END DOCUMENT TEXT ---

    Example JSON Structure (Follow this structure precisely):
    --- START EXAMPLE JSON ---
    {schema_snippet}
    --- END EXAMPLE JSON ---

    Extraction Instructions:
    1.  **Hierarchy:** Identify the hierarchical folder structure (e.g., Program -> Theme -> Week -> Section like 'Math Small Group', 'Read-Alouds', 'STEAM') from the document headings and overall organization. Assign meaningful 'name' attributes. Infer 'parent_id' relationships based on the hierarchy. Use placeholder integer IDs if specific IDs aren't in the text, trying to maintain consistency if possible.
    2.  **Resources:** Within the lowest-level folders, identify individual resources (e.g., 'activity', 'book', 'video', 'document'). Extract metadata like 'id' (infer if needed), 'title', 'type', 'focus_area', 'short_description', 'code', 'link', 'file_url', 'thumbnail_mobile_url', 'thumbnail_web_url'. Use `null` for missing optional fields as shown in the example.
    3.  **Content Blocks:** This is critical. For each resource, meticulously parse the detailed content into the 'content_blocks' array.
        * Identify distinct sections like "PREPARE", "DISCOVER", "DEVELOP", "Materials", "Vocabulary", "Learning Outcomes", "Tips and Preparation", "Inclusive Strategies", "Cultural Responsiveness", "Differentiate Instruction", "Music and Movement", "Activity", "Reflect", etc.
        * Map these sections to the correct 'type' in the `content_blocks` array (e.g., 'day', 'materials', 'general', 'strategies_for_supporting_all_learners', 'teachers_corner', 'labeled_columns', 'midweek_option', 'vocabulary_words'). Use 'general' for standard text blocks with a title.
        * For 'day' type blocks, extract the 'day' number, 'title', and the text content associated with columns like "Prepare", "Discover", "Develop" into the nested 'columns' array.
        * For 'strategies_for_supporting_all_learners' or 'teachers_corner', extract content into the correctly named nested objects (e.g., 'inclusive_strategies', 'multilingual_learners', 'did_you_know', 'tips_strategies').
    4.  **HTML Preservation:** Preserve HTML tags (like <p>, <ul>, <li>, <strong>, <em>, <a>) within the 'text' fields of content blocks exactly as found in the document text or exemplified in the schema. Do not add or remove HTML unless correcting obvious errors.
    5.  **Lists:** Extract lists (e.g., materials, vocabulary words) accurately, often using HTML `<ul><li>...</li></ul>` structure within the 'text' field.
    6.  **Images:** Extract image filenames/paths if they appear within the text content or associated metadata (like `thumbnail_..._url` or inside `content.images` arrays). Ignore bracketed image placeholders like [Image 1].
    7.  **Nested Arrays/Objects:** Accurately replicate all nested structures shown in the example, including 'groups', 'resources', 'content_blocks', 'weekly_schedules', 'framework_items', 'related_items', 'related_by_items', 'provider'. Infer integer IDs where necessary if not present in the text.
    8.  **Strict JSON Output:** The *only* output should be the JSON object itself, starting with `{{` and ending with `}}`. Do NOT include explanations, apologies, markdown formatting (` ```json ... ```), or any text before or after the JSON.
    9.  **Completeness vs. Accuracy:** Prioritize accurately extracting the information *present* in the provided Document Text. Use the Example JSON *only* as a structural guide. Do not invent data or IDs not derivable from the text. If information for a field isn't found, use `null` or omit the field if appropriate according to the example schema.

    Generate the JSON output now:
    """

    try:
        extracted_json_str = call_llm_api(prompt)
        cleaned_json_str = re.sub(r'^```json\s*', '', extracted_json_str, flags=re.IGNORECASE)
        cleaned_json_str = re.sub(r'\s*```$', '', cleaned_json_str)
        cleaned_json_str = cleaned_json_str.strip()

        if not cleaned_json_str:
            print("Error: LLM returned an empty response.")
            return json.dumps({"error": "LLM returned empty response"}, indent=2)

        try:
            parsed_json = json.loads(cleaned_json_str)
            print("LLM output successfully parsed as JSON.")
            return json.dumps(parsed_json, indent=2)
        except json.JSONDecodeError as json_err:
            print(f"Error: LLM output was not valid JSON after cleaning. Error: {json_err}")
            print("Problematic LLM Output Snippet:\n", cleaned_json_str[:500] + "...")
            return json.dumps({
                "error": "LLM generated invalid JSON",
                "details": str(json_err),
                "line": json_err.lineno,
                "column": json_err.colno,
                "llm_output_snippet": cleaned_json_str[:200] + "..."
            }, indent=2)

    except Exception as e:
        print(f"Error during LLM call or processing: {str(e)}")
        return json.dumps({"error": f"Failed during extraction process: {str(e)}"}, indent=2)


# --- Example Usage ---
if __name__ == "__main__":
    # --- Configuration ---
    pdf_filename = "Extracted_Preschool_Pages_wk2.pdf" # Target PDF file
    output_json_filename = "extracted_content_wk2.json" # Where to save the result

    # The example JSON structure provided previously (used as a template)
    # It's important this accurately reflects the desired *output* structure.
    example_json_structure = """
{
  "folders": [
    {
      "id": 18851,
      "name": "DRAFT - Preschool 2024 (native)",
      "parent_id": null,
      "program_id": 111,
      "icon": "folder",
      "abreviation": "DRAFT - Preschool 2024 (native)",
      "order_number": 0,
      "is_legacy": false,
      "short_description": null,
      "clone_status": null,
      "groups": []
    },
    {
      "id": 18867,
      "name": "Theme 1: Marvelous Me",
      "parent_id": 18851,
      "program_id": 111,
      "icon": "folder",
      "abreviation": "Theme 1: Marvelous Me",
      "order_number": 7,
      "is_legacy": false,
      "short_description": null,
      "clone_status": "completed",
      "groups": [
        {
          "id": 224,
          "name": "Theme",
          "program_id": 111,
          "is_active": true,
          "is_guiding_folder": true,
          "order": 2,
          "programs_groups_folders": {
            "folder_id": 18867,
            "program_group_id": 224
          }
        }
      ]
    },
    {
      "id": 18868, # Example ID for Week 1 - LLM should generate appropriate ID for Week 2
      "name": "Week 2", # Target week name
      "parent_id": 18867,
      "program_id": 111,
      "icon": "folder",
      "abreviation": "wk2", # Example, LLM should extract based on PDF text if available
      "order_number": 0, # Example - adjust if needed
      "is_legacy": false,
      "short_description": null,
      "clone_status": null, # Example
      "groups": [],
      "resources": [] # Resources will be nested under appropriate folders
    }
    # ... other folders like Math, Literacy for Week 2 would follow ...
  ]
}
""" # (Keep the full example structure here for the LLM)

    print("\n--- Starting PDF to JSON Extraction Process ---")
    try:
        # 1. Extract text from the specified PDF
        pdf_full_text = extract_text_from_pdf(pdf_filename)

        if pdf_full_text:
            # 2. Call the LLM to process the text and generate JSON
            print(f"\n--- Running Extraction for {pdf_filename} ---")
            resulting_json_str = extract_content_to_json(pdf_full_text, example_json_structure)

            # 3. Save the result (or error message) to a file
            print(f"\n--- Saving result to {output_json_filename} ---")
            with open(output_json_filename, 'w', encoding='utf-8') as f:
                # Check if the result is valid JSON before saving directly
                # If extract_content_to_json returned an error JSON, save that.
                f.write(resulting_json_str)
            print(f"Output saved.")

            # 4. Optionally print a snippet of the result to console
            print("\n--- Result Snippet (or Error) ---")
            try:
                parsed = json.loads(resulting_json_str)
                print(json.dumps(parsed, indent=2)[:1000] + "\n...") # Print first 1000 chars
            except json.JSONDecodeError:
                 print(resulting_json_str) # Print the error string if not valid JSON
            print("---------------------------------")

        else:
            print("Error: No text could be extracted from the PDF.")

    except FileNotFoundError as fnf_error:
        print(fnf_error)
        print("Please ensure the PDF file is in the same directory as the script.")
    except ImportError:
        print("Error: PyPDF2 library not found.")
        print("Please install it using: pip install pypdf2")
    except Exception as general_error:
        print(f"An unexpected error occurred: {general_error}")

    print("\n--- Extraction Process Finished ---")


# main.py
import os
from document_verification_agent import DocumentVerificationAgent

def main():
    # Debug: Check if API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment variables")
        return
    
    # Debug: Print first few characters of API key (for verification)
    print(f"API key found: {api_key[:8]}...")
    
    # Define your folders and files
    image_folder = 'msstandardsoutput'
    input_csv = 'ms_preprocessedoutput.csv'
    output_csv = 'ms_verified_output.csv'
    
    try:
        # Initialize the verification agent with explicit API key
        agent = DocumentVerificationAgent(api_key=api_key)
        
        # Run the verification process
        agent.process_document(
            image_folder=image_folder,
            input_csv=input_csv,
            output_csv=output_csv
        )
        
        print("Verification process completed successfully!")
        
    except Exception as e:
        print(f"Error during verification process: {str(e)}")
        # Print more detailed error information
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
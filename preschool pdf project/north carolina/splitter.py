import PyPDF2
import os

def extract_pdf_pages(input_path, output_path, start_page, end_page):
    # Open the PDF file
    with open(input_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Create a PDF writer object
        writer = PyPDF2.PdfWriter()
        
        # PDF pages are 0-indexed, so we subtract 1 from the page numbers
        for page in range(start_page - 1, min(end_page, len(reader.pages))):
            writer.add_page(reader.pages[page])
        
        # Write the output to a new file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

# Example usage
input_file = 'NC_foundations.pdf'
output_file = 'nceditedfoundations.pdf'
start_page = 40
end_page = 151

# Check if input file exists
if not os.path.exists(input_file):
    print(f"Error: The file {input_file} does not exist.")
else:
    extract_pdf_pages(input_file, output_file, start_page, end_page)
    print(f"Pages {start_page} to {end_page} have been saved to {output_file}")
import PyPDF2

def extract_pages(input_pdf, output_pdf, start_page, end_page):
    with open(input_pdf, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        writer = PyPDF2.PdfWriter()

        for page_num in range(start_page - 1, end_page):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])

        with open(output_pdf, 'wb') as output_file:
            writer.write(output_file)

# Usage
input_file = 'vafull.pdf'
output_file = 'va.pdf'
start_page = 15
end_page = 72

extract_pages(input_file, output_file, start_page, end_page)
print(f"Pages {start_page}-{end_page} extracted to {output_file}")
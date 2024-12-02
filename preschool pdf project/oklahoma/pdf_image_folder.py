import os
import fitz  # PyMuPDF
from PIL import Image

def pdf_to_images(pdf_path, output_folder):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Open the PDF file
    pdf = fitz.open(pdf_path)

    # Iterate through each page
    for page_num in range(len(pdf)):
        # Get the page
        page = pdf[page_num]
        
        # Convert page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save the image
        img_path = os.path.join(output_folder, f'page_{page_num + 1}.png')
        img.save(img_path)

        print(f"Saved page {page_num + 1} as {img_path}")

    # Close the PDF
    pdf.close()

# Set the paths
pdf_path = 'oklahoma.pdf'
output_folder = 'okimages'

# Run the function
pdf_to_images(pdf_path, output_folder)
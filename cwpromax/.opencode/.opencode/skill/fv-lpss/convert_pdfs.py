#!/usr/bin/env python3
"""
PDF to Text Converter for LPSS Documentation
Extracts text from PDF files and saves as .txt files
"""

import PyPDF2
import os
import sys

def extract_pdf_text(pdf_path, output_path):
    """Extract text from PDF and save to text file"""
    try:
        print(f"Processing: {os.path.basename(pdf_path)}")
        
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            print(f"  Total pages: {total_pages}")
            
            # Extract text from all pages
            text_content = []
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                text_content.append(f"\n{'='*80}\n")
                text_content.append(f"PAGE {page_num + 1} of {total_pages}\n")
                text_content.append(f"{'='*80}\n\n")
                text_content.append(text)
            
            # Save to text file
            with open(output_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(''.join(text_content))
            
            print(f"  ✓ Saved to: {os.path.basename(output_path)}")
            print(f"  Extracted {len(''.join(text_content))} characters\n")
            return True
            
    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")
        return False

def main():
    # Define paths
    base_path = r'C:\git\applications.ai.ocode.market.skills\.opencode\skill\fv-lpss\docs'
    
    pdf_files = [
        (os.path.join(base_path, 'i2c', 'DW_apb_i2c_databook.pdf'),
         os.path.join(base_path, 'i2c', 'DW_apb_i2c_databook.txt')),
        (os.path.join(base_path, 'i3c', 'DWC_mipi_i3c_databook.pdf'),
         os.path.join(base_path, 'i3c', 'DWC_mipi_i3c_databook.txt')),
        (os.path.join(base_path, 'i3c', 'mipi_I3C-Basic_specification_v1-1-1.pdf'),
         os.path.join(base_path, 'i3c', 'mipi_I3C-Basic_specification_v1-1-1.txt')),
    ]
    
    print("="*80)
    print("PDF to Text Converter for LPSS Documentation")
    print("="*80 + "\n")
    
    success_count = 0
    for pdf_path, txt_path in pdf_files:
        if os.path.exists(pdf_path):
            if extract_pdf_text(pdf_path, txt_path):
                success_count += 1
        else:
            print(f"Not found: {os.path.basename(pdf_path)}\n")
    
    print("="*80)
    print(f"Conversion complete: {success_count}/{len(pdf_files)} files successfully converted")
    print("="*80)

if __name__ == "__main__":
    main()

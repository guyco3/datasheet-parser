"""
PDF to Text/Markdown Converter

Extracts all text content from a PDF and saves it to a file.
"""

import sys

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def convert_pdf_to_text(pdf_path: str, output_path: str, format: str = "txt", verbose: bool = False) -> bool:
    """
    Convert entire PDF to text or markdown file.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path to save the output file
        format: Output format ("txt" or "md")
        verbose: Whether to print progress information
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_PDFPLUMBER:
        if verbose:
            print("  pdfplumber not available - install with: pip install pdfplumber")
        return False
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            if verbose:
                print(f"  Converting {total_pages} pages to {format.upper()}...")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for page_num, page in enumerate(pdf.pages, 1):
                    if verbose and page_num % 10 == 0:
                        print(f"    Processing page {page_num}/{total_pages}...")
                    
                    text = page.extract_text()
                    
                    if text:
                        if format == "md":
                            # Add markdown headers for pages
                            f.write(f"\n\n{'='*80}\n")
                            f.write(f"# Page {page_num}\n")
                            f.write(f"{'='*80}\n\n")
                        else:
                            # Plain text with page separators
                            f.write(f"\n\n{'='*80}\n")
                            f.write(f"PAGE {page_num}\n")
                            f.write(f"{'='*80}\n\n")
                        
                        f.write(text)
                    else:
                        if verbose:
                            print(f"    Warning: No text on page {page_num}")
            
            if verbose:
                print(f"  ✓ Saved to: {output_path}")
            
            return True
            
    except Exception as e:
        if verbose:
            print(f"  ✗ Conversion error: {e}")
            import traceback
            traceback.print_exc()
        return False


def convert_pdf_to_markdown(pdf_path: str, output_path: str, verbose: bool = False) -> bool:
    """
    Convert PDF to markdown with enhanced formatting.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path to save the markdown file
        verbose: Whether to print progress information
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_PDFPLUMBER:
        if verbose:
            print("  pdfplumber not available - install with: pip install pdfplumber")
        return False
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            if verbose:
                print(f"  Converting {total_pages} pages to Markdown...")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write document header
                f.write("# PDF Document Export\n\n")
                f.write(f"**Total Pages:** {total_pages}\n\n")
                f.write("---\n\n")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    if verbose and page_num % 10 == 0:
                        print(f"    Processing page {page_num}/{total_pages}...")
                    
                    # Page header
                    f.write(f"\n## Page {page_num}\n\n")
                    
                    # Extract and write text
                    text = page.extract_text()
                    if text:
                        f.write(text)
                        f.write("\n\n")
                    
                    # Extract tables if any
                    tables = page.extract_tables()
                    if tables:
                        f.write(f"\n### Tables on Page {page_num}\n\n")
                        for table_idx, table in enumerate(tables, 1):
                            if table and len(table) > 0:
                                f.write(f"**Table {table_idx}:**\n\n")
                                
                                # Write table in markdown format
                                if len(table) > 0:
                                    # Header row
                                    header = table[0]
                                    f.write("| " + " | ".join(str(cell) if cell else "" for cell in header) + " |\n")
                                    f.write("| " + " | ".join(["---"] * len(header)) + " |\n")
                                    
                                    # Data rows
                                    for row in table[1:]:
                                        if len(row) == len(header):
                                            f.write("| " + " | ".join(str(cell) if cell else "" for cell in row) + " |\n")
                                
                                f.write("\n")
                    
                    # Page separator
                    f.write("\n---\n")
            
            if verbose:
                print(f"  ✓ Saved to: {output_path}")
            
            return True
            
    except Exception as e:
        if verbose:
            print(f"  ✗ Conversion error: {e}")
            import traceback
            traceback.print_exc()
        return False

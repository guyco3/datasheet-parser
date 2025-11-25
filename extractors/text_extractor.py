"""Text-based pin extraction using regex patterns."""

import re
from typing import Optional, List

try:
    import pytesseract
    from pdf2image import convert_from_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

import config


def extract_pins_from_text(pdf_path: str, verbose: bool = False) -> Optional[List[str]]:
    """
    Extract pin names from simple text patterns.
    
    Last-resort method that renders pages as text via OCR and looks
    for simple line-based patterns like "1  VDD".
    
    Args:
        pdf_path: Path to the PDF file
        verbose: Whether to print debug information
        
    Returns:
        List of pin names in order, or None if extraction failed
    """
    if not HAS_OCR:
        if verbose:
            print("  Text extraction requires OCR dependencies")
        return None
    
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=5, dpi=config.OCR_DPI)
    except Exception as e:
        if verbose:
            print(f"  Text extraction error: {e}")
        return None

    text = "".join(pytesseract.image_to_string(img) for img in images)

    pattern = r"^\s*(\d{1,3})\s+([A-Za-z0-9_/.-]+)\s*$"
    results = []

    for line in text.splitlines():
        m = re.match(pattern, line)
        if m:
            pin = int(m.group(1))
            name = m.group(2)
            results.append((pin, name))

    if not results:
        return None

    results.sort(key=lambda x: x[0])
    return [name for _, name in results]

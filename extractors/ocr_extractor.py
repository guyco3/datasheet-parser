"""OCR-based pin extraction from pin diagrams."""

import re
from typing import Optional, List

try:
    import pytesseract
    from pdf2image import convert_from_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

import config


def extract_pins_from_ocr(pdf_path: str, verbose: bool = False) -> Optional[List[str]]:
    """
    Extract pin names using OCR on pin diagrams.
    
    Converts the first few pages to images and uses OCR to extract
    text, looking for pin number/name patterns.
    
    Args:
        pdf_path: Path to the PDF file
        verbose: Whether to print debug information
        
    Returns:
        List of pin names in order, or None if extraction failed
    """
    if not HAS_OCR:
        if verbose:
            print("  OCR dependencies not available - install with: pip install pytesseract pdf2image")
        return None
    
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=3, dpi=config.PDF_DPI)
    except Exception as e:
        if verbose:
            print(f"  OCR image conversion error: {e}")
        return None

    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)

    # Look for patterns of form:
    #   VDD    1
    #   2      SDA
    pattern_A = r"([A-Za-z0-9_/.-]+)\s+(\d{1,3})"
    pattern_B = r"(\d{1,3})\s+([A-Za-z0-9_/.-]+)"

    pairs = []

    for m in re.findall(pattern_A, text):
        name, pin = m
        if re.match(r"^\d+$", pin):
            pairs.append((int(pin), name))

    for m in re.findall(pattern_B, text):
        pin, name = m
        if re.match(r"^\d+$", pin):
            pairs.append((int(pin), name))

    if not pairs:
        return None

    # Deduplicate
    cleaned = {}
    for pin, name in pairs:
        cleaned[pin] = name

    return [cleaned[p] for p in sorted(cleaned.keys())]

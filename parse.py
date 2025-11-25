"""
Datasheet Pin Extractor

A tool to extract pin information from IC datasheets using multiple methods:
- Table extraction (fast, structured)
- OCR from pin diagrams
- Text pattern matching
- LLM-based analysis (most robust)
"""

import sys
import json
import argparse
from typing import Optional, List, Dict

from utils import download_pdf, format_pin_data
from extractors import (
    extract_pins_from_tables,
    extract_pins_from_ocr,
    extract_pins_from_text,
    extract_pins_with_llm,
    convert_pdf_to_text,
    convert_pdf_to_markdown
)


def extract_pins_traditional(pdf_path: str, verbose: bool = False) -> Optional[Dict]:
    """
    Extract pins using traditional methods (table, OCR, text).
    
    Tries methods in order of reliability:
    1. Table extraction (most reliable for structured datasheets)
    2. OCR from diagrams
    3. Text pattern matching
    
    Args:
        pdf_path: Path to the PDF file
        verbose: Whether to print progress information
        
    Returns:
        Dictionary with pins and metadata, or None if all methods failed
    """
    if verbose:
        print("\n" + "="*60)
        print("TRADITIONAL EXTRACTION (Table + OCR + Text)")
        print("="*60)
    
    # Method 1: Table extraction
    if verbose:
        print("\n[1/3] Trying table extraction...")
    result = extract_pins_from_tables(pdf_path, verbose=verbose)
    if result and result.get("pins"):
        if verbose:
            print(f"✓ Found {len(result['pins'])} pins via table extraction")
        return result
    elif verbose:
        print("✗ Table extraction failed")

    # Method 2: OCR diagram (returns list of pin names)
    if verbose:
        print("\n[2/3] Trying OCR diagram extraction...")
    pins = extract_pins_from_ocr(pdf_path, verbose=verbose)
    if pins:
        if verbose:
            print(f"✓ Found {len(pins)} pins via OCR")
        # Convert simple pin names to Pin objects
        from schema import Pin
        pin_objects = [Pin(number=i, name=name) for i, name in enumerate(pins, 1)]
        return {"pins": pin_objects, "metadata": None}
    elif verbose:
        print("✗ OCR extraction failed")

    # Method 3: Text fallback (returns list of pin names)
    if verbose:
        print("\n[3/3] Trying text pattern extraction...")
    pins = extract_pins_from_text(pdf_path, verbose=verbose)
    if pins:
        if verbose:
            print(f"✓ Found {len(pins)} pins via text extraction")
        # Convert simple pin names to Pin objects
        from schema import Pin
        pin_objects = [Pin(number=i, name=name) for i, name in enumerate(pins, 1)]
        return {"pins": pin_objects, "metadata": None}
    elif verbose:
        print("✗ Text extraction failed")

    return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract pin information from IC datasheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use traditional methods (table + OCR + text)
  python parse.py <url>
  
  # Use LLM-based extraction (requires LLM integration)
  python parse.py <url> --method llm
  
  # Convert entire PDF to text file
  python parse.py <url> --convert txt
  
  # Convert entire PDF to markdown with tables
  python parse.py <url> --convert md -o output.md
  
  # Verbose output
  python parse.py <url> --verbose
  
  # Save extracted text for LLM integration
  python parse.py <url> --method llm --save-text extracted.json
        """
    )
    
    parser.add_argument(
        "url",
        help="URL of the datasheet PDF to parse"
    )
    
    parser.add_argument(
        "-m", "--method",
        choices=["traditional", "llm"],
        default="traditional",
        help="Extraction method to use (default: traditional)"
    )
    
    parser.add_argument(
        "--convert",
        choices=["txt", "md"],
        metavar="FORMAT",
        help="Convert entire PDF to text file (txt=plain text, md=markdown with tables)"
    )
    
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Output file path for --convert (default: datasheet.txt or datasheet.md)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--save-text",
        metavar="FILE",
        help="Save extracted page text to JSON file (useful for LLM integration)"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only JSON (no formatted text)"
    )
    
    args = parser.parse_args()
    
    # Handle PDF conversion mode
    if args.convert:
        if args.verbose:
            print(f"\nDownloading PDF from: {args.url}")
        
        try:
            pdf_path = download_pdf(args.url)
            if args.verbose:
                print(f"✓ Downloaded to: {pdf_path}\n")
        except Exception as e:
            print(f"✗ Failed to download PDF: {e}", file=sys.stderr)
            return 1
        
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            output_path = f"datasheet.{args.convert}"
        
        print(f"\nConverting PDF to {args.convert.upper()}...")
        
        if args.convert == "md":
            success = convert_pdf_to_markdown(pdf_path, output_path, verbose=args.verbose)
        else:
            success = convert_pdf_to_text(pdf_path, output_path, format="txt", verbose=args.verbose)
        
        if success:
            print(f"\n✓ Successfully converted PDF to: {output_path}")
            return 0
        else:
            print(f"\n✗ Failed to convert PDF", file=sys.stderr)
            return 1
    
    # Download PDF
    if args.verbose:
        print(f"\nDownloading PDF from: {args.url}")
    
    try:
        pdf_path = download_pdf(args.url)
        if args.verbose:
            print(f"✓ Downloaded to: {pdf_path}\n")
    except Exception as e:
        print(f"✗ Failed to download PDF: {e}", file=sys.stderr)
        return 1
    
    # Extract pins using selected method
    pins = None
    
    if args.method == "llm":
        result = extract_pins_with_llm(pdf_path, verbose=args.verbose)
        
        # Save extracted text if requested (regardless of success)
        if args.save_text:
            from extractors.llm_extractor import extract_text_from_pdf
            pages_data = extract_text_from_pdf(pdf_path, verbose=False)
            with open(args.save_text, "w") as f:
                json.dump(pages_data, f, indent=2)
            if args.verbose:
                print(f"\n✓ Saved extracted text to: {args.save_text}")
        
        if result and result.get("success"):
            pins = result.get("pins", [])
            
            # Check if we got actual pins or just mock data
            if not pins:
                if not args.json_only:
                    print("\n✗ LLM extraction returned no pins (mock implementation)", file=sys.stderr)
                    print("\nNote: The LLM method is currently using mock data.")
                    print("To enable real extraction:")
                    print("  1. Edit extractors/llm_extractor.py")
                    print("  2. Replace process_page_with_llm() with your LLM API call")
                    print("  3. See README.md for integration examples")
                return 1
        else:
            if not args.json_only:
                print("\n✗ LLM extraction failed", file=sys.stderr)
            return 1
    else:
        # Traditional extraction
        result = extract_pins_traditional(pdf_path, verbose=args.verbose)
        if result:
            pins = result.get("pins", [])
            metadata = result.get("metadata")
    
    # Output results
    if pins:
        if not args.json_only:
            # Display metadata if available
            if metadata:
                print("\n" + "="*60)
                print("DATASHEET METADATA")
                print("="*60)
                if metadata.get("part_number"):
                    print(f"Part Number: {metadata['part_number']}")
                if metadata.get("title"):
                    print(f"Title: {metadata['title']}")
                if metadata.get("features"):
                    print(f"\nFeatures ({len(metadata['features'])}):")
                    for feat in metadata['features'][:5]:  # Show first 5
                        print(f"  • {feat}")
                    if len(metadata['features']) > 5:
                        print(f"  ... and {len(metadata['features']) - 5} more")
                if metadata.get("applications"):
                    print(f"\nApplications ({len(metadata['applications'])}):")
                    for app in metadata['applications'][:5]:  # Show first 5
                        print(f"  • {app}")
                print()
            
            print("\n" + "="*60)
            print("EXTRACTED PIN DATA")
            print("="*60)
            for pin in pins:
                # Handle both Pin objects and simple dicts
                if hasattr(pin, 'number'):
                    pin_num = pin.number
                    pin_name = pin.name
                    details = getattr(pin, 'details', None) or {}
                else:
                    pin_num = pin.get('number', '?')
                    pin_name = pin.get('name', '?')
                    details = pin.get('details', {}) or {}
                
                print(f"\nPin {pin_num:2}: {pin_name}")
                
                # Display details if present
                if details:
                    # Show type and direction on one line if both present
                    type_dir = []
                    if details.get('type'):
                        type_dir.append(f"Type: {details['type']}")
                    if details.get('direction'):
                        type_dir.append(f"Direction: {details['direction']}")
                    if type_dir:
                        print(f"        {' | '.join(type_dir)}")
                    
                    # Show description
                    if details.get('description'):
                        desc = details['description']
                        # Wrap long descriptions
                        desc_lines = [desc[i:i+70] for i in range(0, len(desc), 70)]
                        for line in desc_lines:
                            print(f"        {line}")
                    
                    # Show any other details
                    for key, value in details.items():
                        if key not in ['type', 'direction', 'description']:
                            print(f"        {key}: {value}")
                            
            print("="*60)
            print(f"\nTotal pins: {len(pins)}\n")
        
        # Always output JSON
        if not args.json_only:
            print("JSON Output:")
        
        # Convert Pin objects to dicts if needed
        pins_data = []
        for pin in pins:
            if hasattr(pin, 'model_dump'):
                pins_data.append(pin.model_dump(exclude_none=True))
            elif hasattr(pin, 'dict'):
                pins_data.append(pin.dict(exclude_none=True))
            else:
                pins_data.append(pin)
        
        result_data = {
            "pins": pins_data,
            "count": len(pins)
        }
        if metadata:
            result_data["metadata"] = metadata
        
        print(json.dumps(result_data, indent=2))
        
        return 0
    else:
        if not args.json_only:
            print("\n✗ Failed to extract pin data from the datasheet.", file=sys.stderr)
            print("\nTroubleshooting:")
            print("1. Try --method llm (requires LLM integration)")
            print("2. Use --verbose to see detailed extraction attempts")
            print("3. Check if the PDF contains pin tables or diagrams")
        return 1


if __name__ == "__main__":
    sys.exit(main())

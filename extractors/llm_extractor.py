"""LLM-based pin extraction from PDF text."""

import os
import json
from typing import Optional, Dict, List

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pydantic import ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

import config
from schema import Pin, PinExtractionResult

# Try to import LLM providers
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def extract_text_from_pdf(pdf_path: str, max_pages: int = None, verbose: bool = False) -> List[Dict]:
    """
    Extract text from PDF, page by page.
    
    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract (default from config)
        verbose: Whether to print progress information
        
    Returns:
        List of dicts with page number, text content, and character count
    """
    if not HAS_PDFPLUMBER:
        if verbose:
            print("pdfplumber not available - install with: pip install pdfplumber")
        return []
    
    if max_pages is None:
        max_pages = config.DEFAULT_MAX_PAGES
    
    pages_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = min(len(pdf.pages), max_pages)
            if verbose:
                print(f"Extracting text from {total_pages} pages...")
            
            for page_num, page in enumerate(pdf.pages[:max_pages], 1):
                text = page.extract_text()
                
                if text and text.strip():
                    pages_data.append({
                        "page_number": page_num,
                        "text": text,
                        "char_count": len(text)
                    })
                    if verbose:
                        print(f"  Page {page_num}: {len(text)} characters extracted")
                elif verbose:
                    print(f"  Page {page_num}: No text extracted")
    
    except Exception as e:
        if verbose:
            print(f"Error extracting text: {e}")
        return []
    
    return pages_data


def process_page_with_llm(page_text: str, page_number: int, verbose: bool = False) -> Optional[Dict]:
    """
    Process page text and extract pin data with LLM.
    
    This function sends the page text to an LLM (OpenAI, Anthropic, or mock)
    and requests structured pin information extraction using Pydantic schema.
    
    Args:
        page_text: Text content of the page
        page_number: Page number for reference
        verbose: Whether to print debug information
        
    Returns:
        Dictionary with extracted pins (validated via Pydantic), or None if no pins found
    """
    
    # Get JSON schema from Pydantic model
    if HAS_PYDANTIC:
        schema_json = PinExtractionResult.model_json_schema()
        schema_str = json.dumps(schema_json, indent=2)
    else:
        schema_str = """{
  "pins": [
    {
      "number": 1,
      "name": "VDD",
      "type": "Analog|Digital|Power|Ground|Analog/Digital",
      "direction": "Input|Output|I/O|Bidirectional",
      "description": "string"
    }
  ]
}"""
    
    # Construct the prompt for pin extraction
    prompt = f"""Extract all IC pin information from this datasheet page.

You must return valid JSON matching this schema:
{schema_str}

Required fields for each pin:
- "number": Pin number (integer or string like "A1")
- "name": Primary pin name/signal name

Optional fields (include if information is available):
- "alternate_names": List of alternative names (e.g., ["ALERT", "RDY"])
- "type": Must be one of: "Analog", "Digital", "Power", "Ground", or "Analog/Digital"
- "direction": Must be one of: "Input", "Output", "I/O", "Bidirectional"
- "description": Detailed description of the pin's function

Important:
- Only extract actual pin information (ignore headers, page numbers, etc.)
- If this page has no pin information, return {{"pins": []}}
- Return ONLY valid JSON, no markdown formatting or explanations
- Preserve exact pin names as they appear in the datasheet
- Use exact values for type and direction fields as specified above

Page {page_number} content:
{page_text}
"""
    
    provider = config.LLM_PROVIDER.lower()
    
    # OpenAI implementation
    if provider == "openai" and HAS_OPENAI:
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation parser that extracts structured IC pin information from datasheets. Always return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Parse and validate with Pydantic
            if HAS_PYDANTIC:
                result = PinExtractionResult.model_validate_json(content)
                pins_data = result.model_dump()
            else:
                pins_data = json.loads(content)
            
            pins = pins_data.get("pins", [])
            
            if verbose:
                print(f"\n✓ Page {page_number}: Extracted {len(pins)} pins via OpenAI")
                if pins and verbose:
                    print(f"  Sample: {pins[0].get('name', 'N/A')}")
            
            return pins_data if pins else None
            
        except ValidationError as e:
            if verbose:
                print(f"\n✗ Page {page_number}: Validation error: {e}")
            return None
        except Exception as e:
            if verbose:
                print(f"\n✗ Page {page_number}: OpenAI error: {e}")
            return None
    
    # Anthropic implementation
    elif provider == "anthropic" and HAS_ANTHROPIC:
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            response = client.messages.create(
                model=config.LLM_MODEL,
                max_tokens=config.LLM_MAX_TOKENS,
                temperature=config.LLM_TEMPERATURE,
                system="You are a technical documentation parser that extracts structured IC pin information from datasheets. Always return valid JSON only.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Parse and validate with Pydantic
            if HAS_PYDANTIC:
                result = PinExtractionResult.model_validate_json(content)
                pins_data = result.model_dump()
            else:
                pins_data = json.loads(content)
            
            pins = pins_data.get("pins", [])
            
            if verbose:
                print(f"\n✓ Page {page_number}: Extracted {len(pins)} pins via Anthropic")
                if pins and verbose:
                    print(f"  Sample: {pins[0].get('name', 'N/A')}")
            
            return pins_data if pins else None
            
        except ValidationError as e:
            if verbose:
                print(f"\n✗ Page {page_number}: Validation error: {e}")
            return None
        except Exception as e:
            if verbose:
                print(f"\n✗ Page {page_number}: Anthropic error: {e}")
            return None
    
    # Mock implementation (for testing without API)
    else:
        if verbose:
            print(f"\n{'='*60}")
            print(f"MOCK LLM PROCESSING - Page {page_number}")
            print(f"{'='*60}")
            print(f"Text length: {len(page_text)} characters")
            print(f"\nFirst 300 characters:")
            print("-" * 60)
            print(page_text[:300])
            print("-" * 60)
        
        # Check if this page likely contains pin information
        keywords = ["pin", "terminal", "connection", "signal", "description"]
        has_pin_info = any(kw in page_text.lower() for kw in keywords)
        
        if has_pin_info:
            if verbose:
                print(f"✓ Page {page_number} appears to contain pin information")
            # Return empty pins array - mock mode doesn't extract real data
            return {"pins": []}
        else:
            if verbose:
                print(f"✗ Page {page_number} does not appear to contain pin information")
            return None


def extract_pins_with_llm(pdf_path: str, verbose: bool = False) -> Optional[Dict]:
    """
    Extract pins using LLM-based text analysis.
    
    This method:
    1. Extracts text from each page
    2. Sends each page to an LLM for pin extraction
    3. Aggregates results
    
    Args:
        pdf_path: Path to the PDF file
        verbose: Whether to print progress information
        
    Returns:
        Dictionary with extraction results and metadata, or None if failed
    """
    # Extract text from all pages
    pages_data = extract_text_from_pdf(pdf_path, verbose=verbose)
    
    if not pages_data:
        return None
    
    if verbose:
        print(f"\n✓ Successfully extracted text from {len(pages_data)} pages\n")
        print("="*60)
        print("PROCESSING PAGES WITH LLM")
        print("="*60)
    
    # Process each page with LLM
    results = []
    all_pins = []
    
    for page_data in pages_data:
        result = process_page_with_llm(
            page_data["text"], 
            page_data["page_number"],
            verbose=verbose
        )
        
        if result:
            results.append(result)
            # In real implementation, extract pins from LLM response
            # all_pins.extend(result.get("pins", []))
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total pages processed: {len(pages_data)}")
        print(f"Pages with potential pin data: {len(results)}")
        print(f"\nNote: Replace process_page_with_llm() with actual LLM API call")
    
    return {
        "success": True,
        "total_pages": len(pages_data),
        "pages_with_pins": len(results),
        "pins": all_pins,  # Will be populated by real LLM
        "llm_results": results
    }

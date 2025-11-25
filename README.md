# Datasheet Pin Extractor

A Python tool to automatically extract pin information from IC datasheets (PDFs).

## Features

- **Multiple Extraction Methods**:
  - **Table Extraction**: Fast, reliable extraction from structured pin tables with type, direction, and description
  - **OCR**: Extracts pins from diagrams and images
  - **Text Pattern Matching**: Fallback for simple text layouts
  - **LLM Integration**: Most robust method using AI (requires API setup)

- **Metadata Extraction**: Automatically extracts features, applications, and descriptions from datasheets
- **PDF Conversion**: Convert entire PDFs to text or markdown format
- **Flexible CLI**: Choose extraction method, verbosity, and output format
- **Clean Architecture**: Modular design with separate extractors

## Installation

```bash
# Clone repository
git clone <your-repo-url>
cd datasheet-parser

# Install dependencies
pip install pdfplumber requests

# Optional: For OCR support
pip install pytesseract pdf2image

# Optional: For LLM support (see LLM Integration below)
pip install openai  # or anthropic

# Optional: For enhanced schema validation
pip install pydantic
```

## Quick Start

```bash
# Extract pins using traditional methods (table + OCR + text)
python parse.py https://datasheet.octopart.com/ADS1115IDGST-Texas-Instruments-datasheet-21818186.pdf

# Convert entire PDF to text file
python parse.py <datasheet-url> --convert txt -o output.txt

# Convert entire PDF to markdown with tables
python parse.py <datasheet-url> --convert md -o output.md

# Use LLM extraction (requires setup - see below)
python parse.py <datasheet-url> --method llm

# Verbose output to see what's happening
python parse.py <datasheet-url> --verbose

# Save extracted text for inspection
python parse.py <datasheet-url> --method llm --save-text extracted.json
```

## Usage

```
usage: parse.py [-h] [-m {traditional,llm}] [--convert FORMAT] [-o FILE] 
                [-v] [--save-text FILE] [--json-only] url

Extract pin information from IC datasheets

positional arguments:
  url                   URL of the datasheet PDF to parse

options:
  -h, --help            show this help message and exit
  -m {traditional,llm}, --method {traditional,llm}
                        Extraction method to use (default: traditional)
  --convert FORMAT      Convert entire PDF to text file (txt=plain text, 
                        md=markdown with tables)
  -o FILE, --output FILE
                        Output file path for --convert
  -v, --verbose         Enable verbose output
  --save-text FILE      Save extracted page text to JSON file
  --json-only           Output only JSON (no formatted text)
```

## Example Output

### Pin Extraction

```
============================================================
DATASHEET METADATA
============================================================
Part Number: ADS1113
Features (7):
  • Ultra-small packages: The ADS1113, ADS1114, and ADS1115 (ADS111x)
  • Wide supply range: 2.0V to 5.5V leadless X2QFN-10
  • Low current consumption: 150μA
  ... and 4 more

============================================================
EXTRACTED PIN DATA
============================================================
Pin  1: ADDR
        Type: Digital
        I2C target address select

Pin  3: GND
        Type: Analog
        Ground

Pin  4: AIN0
        Type: Analog
        Analog input 0
        
... (7 pins total)

JSON Output:
{
  "pins": [
    {
      "number": 1,
      "name": "ADDR",
      "details": {
        "type": "Digital",
        "direction": "Input",
        "description": "I2C target address select"
      }
    },
    {
      "number": 8,
      "name": "VDD",
      "details": {
        "type": "Power",
        "description": "Power supply: 2.0V to 5.5V"
      }
    }
  ],
  "count": 7,
  "metadata": {
    "part_number": "ADS1113",
    "features": [...],
    "applications": [...],
    "description": "..."
  }
}
```

**Note on Pin Schema:** Datasheet pin tables vary significantly across manufacturers and components. Some provide extensive details (type, direction, voltage ranges, protocols), while others only list pin numbers and names. Our flexible schema captures whatever information is available:
- **Always present**: `number` and `name` (the essentials)
- **Optional `details`**: Any additional fields found (type, direction, description, etc.)

This approach ensures we can extract data from any datasheet format without losing information or failing validation.

### PDF Conversion

```bash
# Text output
python parse.py <url> --convert txt -o datasheet.txt

# Markdown output with tables
python parse.py <url> --convert md -o datasheet.md
```

## LLM Integration

The LLM method provides the most robust extraction but requires integration with an LLM API.

### Setup

1. Install your LLM SDK:
   ```bash
   pip install openai  # for OpenAI
   # or
   pip install anthropic  # for Anthropic Claude
   ```

2. Edit `extractors/llm_extractor.py` and replace the `process_page_with_llm()` function:

   ```python
   import openai
   import json
   
   def process_page_with_llm(page_text: str, page_number: int, verbose: bool = False):
       """Extract pins using OpenAI GPT-4."""
       
       prompt = f'''Extract all IC pin information from this datasheet page.
       Return ONLY valid JSON with this exact format:
       {{"pins": [{{"number": 1, "name": "VDD"}}, {{"number": 2, "name": "GND"}}]}}
       
       Page text:
       {page_text}
       '''
       
       response = openai.chat.completions.create(
           model="gpt-4",
           messages=[{"role": "user", "content": prompt}],
           temperature=0
       )
       
       try:
           result = json.loads(response.choices[0].message.content)
           return result if result.get("pins") else None
       except:
           return None
   ```

3. Set your API key:
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

4. Run with LLM:
   ```bash
   python parse.py <datasheet-url> --method llm
   ```

## Project Structure

```
datasheet-parser/
├── parse.py                    # Main CLI entry point
├── config.py                   # Configuration constants
├── schema.py                   # Pydantic schemas for type validation
├── utils.py                    # Shared utility functions
├── extractors/
│   ├── __init__.py
│   ├── table_extractor.py     # Table-based extraction with metadata
│   ├── ocr_extractor.py       # OCR-based extraction
│   ├── text_extractor.py      # Text pattern extraction
│   ├── llm_extractor.py       # LLM-based extraction
│   └── pdf_to_text.py         # PDF to text/markdown conversion
├── requirements.txt            # Python dependencies
└── README.md
```

## How It Works

### Traditional Method (Default)

1. **Table Extraction**: 
   - Uses `pdfplumber` to find tables with pin information
   - Extracts pin number, name, type (Analog/Digital), direction (Input/Output), and description
   - Handles multi-row headers and device-specific columns
   - Extracts metadata (features, applications, description) from first page
   
2. **OCR Extraction**: Converts pages to images and uses OCR to find pin diagrams

3. **Text Pattern**: Looks for simple line patterns like "1  VDD"

### LLM Method

1. Extracts text from each page using `pdfplumber`
2. Sends page text to LLM with structured prompt
3. LLM analyzes context and returns structured pin data
4. Works with inconsistent formats, diagrams described in text, etc.

## Troubleshooting

### "pdfplumber not available"
```bash
pip install pdfplumber
```

### "OCR dependencies not available"
```bash
pip install pytesseract pdf2image
```

### No pins extracted
- Try `--verbose` to see what's happening
- Use `--method llm` for more robust extraction
- Check if the PDF has selectable text (not just images)
- Verify the datasheet has a pin table or diagram

### LLM extraction returns mock data
- You need to integrate a real LLM API
- Edit `extractors/llm_extractor.py`
- See "LLM Integration" section above

## Advanced Features

### Type-Safe Schemas

The tool uses Pydantic models for robust data validation with a flexible schema that adapts to different datasheet formats:

```python
from schema import Pin

# Minimal pin (only required fields)
pin = Pin(number=1, name="GND")

# Pin with full details
pin = Pin(
    number=2,
    name="VDD",
    details={
        "type": "Power",
        "direction": "Input",
        "description": "Power supply input",
        "voltage_range": "2.0V - 5.5V"
    }
)
```

**Why flexible details?** Pin tables across datasheets are inconsistent. Some specify type/direction/description, others include protocol info, voltage specs, or alternate names. The `details` dictionary captures whatever is available without enforcing a rigid structure, ensuring compatibility with any datasheet while preserving all extracted information.

### Metadata Extraction

Automatically extracts from the first page:
- Part number
- Title
- Features (bullet points)
- Applications
- Description

### PDF to Text/Markdown

Convert entire datasheets for:
- LLM processing
- Manual review
- Documentation generation
- Text analysis

## Contributing

Contributions welcome! Areas for improvement:
- Support for non-numeric pin names (A1, B2, etc.)
- Better OCR accuracy
- More table format detection patterns
- Additional LLM providers
- Enhanced metadata parsing

## License

MIT License

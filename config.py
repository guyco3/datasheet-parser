"""Configuration settings for datasheet parser."""

# PDF Processing
DEFAULT_MAX_PAGES = 15
PDF_DPI = 300
OCR_DPI = 200
DOWNLOAD_TIMEOUT = 20

# Pin Extraction
MIN_PIN_NAME_LENGTH = 1
MAX_PIN_NAME_LENGTH = 30

# Extraction Methods
METHOD_TABLE = "table"
METHOD_OCR = "ocr"
METHOD_TEXT = "text"
METHOD_LLM = "llm"

# LLM Configuration
LLM_PROVIDER = "openai"  # Options: "openai", "anthropic", "mock"
LLM_MODEL = "gpt-4o-mini"  # or "gpt-4", "claude-3-5-sonnet-20241022", etc.
LLM_TEMPERATURE = 0
LLM_MAX_TOKENS = 4000

# Pin Schema - Expected fields in LLM output
PIN_SCHEMA = {
    "number": "int or string - Pin number (e.g., 1, 2, or A1, B2)",
    "name": "string - Primary pin name/signal name",
    "alternate_names": "list[string] - Alternative names for the pin (optional)",
    "type": "string - Analog|Digital|Power|Ground|Analog/Digital (optional)",
    "direction": "string - Input|Output|I/O|Bidirectional (optional)",
    "description": "string - Detailed description of pin function (optional)"
}


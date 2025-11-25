"""Table-based pin extraction using pdfplumber."""

import re
from typing import Optional, List, Dict

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

import config
from schema import Pin


def extract_metadata_from_text(text: str) -> Dict:
    """
    Extract features, description, and applications from text.
    
    Args:
        text: Page text content
        
    Returns:
        Dictionary with metadata fields
    """
    metadata = {
        "features": [],
        "applications": [],
        "description": None,
        "title": None,
        "part_number": None
    }
    
    lines = text.split('\n')
    
    # Look for part number (usually at top)
    for i, line in enumerate(lines[:10]):
        # Match patterns like ADS1115, TPS54360, etc.
        part_match = re.search(r'\b([A-Z]{2,}\d{3,}[A-Z0-9]*)\b', line)
        if part_match and not metadata["part_number"]:
            metadata["part_number"] = part_match.group(1)
    
    # Look for title (often after part number)
    for i, line in enumerate(lines[:15]):
        if len(line) > 20 and len(line) < 150 and not line.isupper():
            if any(word in line.lower() for word in ['converter', 'regulator', 'amplifier', 'controller', 'interface']):
                metadata["title"] = line.strip()
                break
    
    # Extract features section
    in_features = False
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        if 'features' in line_lower and len(line_lower) < 30:
            in_features = True
            continue
        
        if in_features:
            # Stop at next major section
            if any(section in line_lower for section in ['description', 'application', 'specification', 'pin config']):
                in_features = False
                continue
            
            # Extract bullet points
            if line.strip().startswith('•') or line.strip().startswith('-'):
                feature = re.sub(r'^[•\-\*]\s*', '', line).strip()
                if len(feature) > 5 and len(feature) < 200:
                    metadata["features"].append(feature)
    
    # Extract applications section
    in_applications = False
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        if 'application' in line_lower and len(line_lower) < 30:
            in_applications = True
            continue
        
        if in_applications:
            # Stop at next major section
            if any(section in line_lower for section in ['pin config', 'specification', 'features']):
                in_applications = False
                continue
            
            # Extract bullet points
            if line.strip().startswith('•') or line.strip().startswith('-'):
                app = re.sub(r'^[•\-\*]\s*', '', line).strip()
                if len(app) > 5 and len(app) < 200:
                    metadata["applications"].append(app)
    
    # Extract description (text between DESCRIPTION header and next section)
    description_text = []
    in_description = False
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        if line_lower == 'description' or (len(line_lower) < 30 and 'description' in line_lower):
            in_description = True
            continue
        
        if in_description:
            # Stop at pin configuration or other sections
            if any(section in line_lower for section in ['pin config', 'pin description', 'specification', 'features', 'application']):
                break
            
            if line.strip() and not line.strip().startswith('•'):
                description_text.append(line.strip())
    
    if description_text:
        metadata["description"] = ' '.join(description_text[:10])  # Limit to first ~10 lines
    
    return metadata


def extract_pins_from_tables(pdf_path: str, verbose: bool = False) -> Optional[Dict]:
    """
    Extract pin data with full details from PDF tables.
    
    Uses pdfplumber to find tables with pin information including
    pin number, name, type, direction, and description.
    
    Args:
        pdf_path: Path to the PDF file
        verbose: Whether to print debug information
        
    Returns:
        Dictionary with 'pins' (List[Pin]) and 'metadata', or None if extraction failed
    """
    if not HAS_PDFPLUMBER:
        if verbose:
            print("  pdfplumber not available - install with: pip install pdfplumber")
        return None
    
    candidates = []  # List of (pin_number, Pin object)
    metadata = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract metadata from first page
            if pdf.pages:
                first_page_text = pdf.pages[0].extract_text()
                if first_page_text:
                    metadata = extract_metadata_from_text(first_page_text)
                    if verbose and metadata:
                        print(f"  Extracted metadata: {metadata.get('part_number', 'N/A')}")
            
            # Scan more pages to find pin tables (some datasheets have them later)
            # Check first 50 pages or entire document if shorter
            pages_to_check = min(50, len(pdf.pages))
            for page_num, page in enumerate(pdf.pages[:pages_to_check], 1):
                tables = page.extract_tables()
                
                if verbose:
                    print(f"  Page {page_num}: Found {len(tables)} tables")
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue
                    
                    # Handle multi-row headers (sometimes pin tables have merged header cells)
                    # Try first row as headers
                    headers = [str(h).lower().strip() if h else "" for h in table[0]]
                    # Clean newlines and extra whitespace from headers
                    headers = [re.sub(r'\s+', ' ', h) for h in headers]
                    data_start_idx = 1
                    
                    # If first row doesn't have enough info, check if second row is the real header
                    if headers.count("") > len(headers) / 2 or not any("name" in h for h in headers):
                        if len(table) > 2:
                            # Try combining first two rows for headers
                            headers_row2 = [str(h).lower().strip() if h else "" for h in table[1]]
                            # If second row looks more like headers, use it
                            if any(keyword in " ".join(headers_row2) for keyword in ["name", "type", "description"]):
                                headers = headers_row2
                                data_start_idx = 2
                    
                    if verbose:
                        print(f"    Table {table_idx + 1} headers: {headers[:5]}")  # Show first 5 headers
                    
                    # Look for pin table columns
                    pin_idx = None
                    name_idx = None
                    type_idx = None
                    direction_idx = None
                    description_idx = None
                    
                    for i, h in enumerate(headers):
                        h_lower = h.lower()
                        
                        # Match pin column (pin, pin#, pin no, pin number, etc)
                        if re.search(r'pin\s*#?|pin\s*no|pin\s*num', h_lower) and "description" not in h_lower:
                            pin_idx = i
                        
                        # Match name/signal/function column
                        if re.search(r'\bname\b|signal|function|device', h_lower) and "description" not in h_lower and "package" not in h_lower and "orderable" not in h_lower and "reel" not in h_lower and "spq" not in h_lower:
                            if name_idx is None:
                                name_idx = i
                        
                        # Match "I/O Type" column - this is actually a type+direction combined column
                        # Handles: "I/O TYPE", "I/O Type", etc.
                        if re.match(r'^i\s*/\s*o\s+type', h_lower):
                            if type_idx is None:
                                type_idx = i
                            if direction_idx is None:
                                direction_idx = i
                            continue
                        
                        # Match type column (analog/digital)
                        # Handles: "TYPE", "ANALOG/DIGITAL", "Analog/Digital", etc.
                        # Also handles multi-line headers like "ANALOG/\nDIGITAL" (now cleaned to "analog/ digital")
                        if h_lower == 'type' or 'analog' in h_lower or 'digital' in h_lower:
                            # Only if it's not part of description
                            if 'description' not in h_lower:
                                # Check if this is a combined type/direction column
                                # E.g., "analog/ digital input/ output" or "analog/digital"
                                if type_idx is None:  # Take first match
                                    type_idx = i
                                    # Also check if it contains direction info
                                    if ('input' in h_lower or 'output' in h_lower) and direction_idx is None:
                                        direction_idx = i
                        
                        # Match direction column (input/output)
                        # Handles: "INPUT/OUTPUT", "I/O", "DIRECTION", etc.
                        # Skip if already matched as "I/O TYPE"
                        if re.search(r'input.*output|output.*input|direction', h_lower) and 'type' not in h_lower:
                            if re.search(r'\bi\s*/\s*o\b', h_lower) and 'type' not in h_lower:
                                if direction_idx is None:
                                    direction_idx = i
                        
                        # Match description column
                        if 'description' in h_lower:
                            if description_idx is None:  # Take first match
                                description_idx = i
                    
                    # Special case: For tables where NAME is column 0 and pin numbers are in device-specific columns
                    # (e.g., ADS1113, ADS1114, ADS1115 columns contain the pin numbers)
                    if name_idx == 0 and pin_idx is None:
                        # Look for numeric values in rows to find pin number column
                        # Try columns 1, 2, 3 after NAME
                        for test_col in range(1, min(4, len(headers))):
                            # Check if this column has numeric data in the rows
                            has_numbers = False
                            for row in table[data_start_idx:data_start_idx + 3]:  # Check first few rows
                                if len(row) > test_col and row[test_col]:
                                    if re.match(r'^\d+$', str(row[test_col]).strip()):
                                        has_numbers = True
                                        break
                            if has_numbers:
                                pin_idx = test_col
                                if verbose:
                                    print(f"      Detected pin numbers in column {test_col} (header: '{headers[test_col]}')")
                                break
                    
                    if pin_idx is None or name_idx is None:
                        if verbose and pin_idx is None:
                            print(f"      Skipping - no pin column found")
                        elif verbose:
                            print(f"      Skipping - no name column found")
                        continue
                    
                    if verbose:
                        print(f"      Found pin table! pin_idx={pin_idx}, name_idx={name_idx}, type_idx={type_idx}, direction_idx={direction_idx}, description_idx={description_idx}")
                    
                    # Additional check: skip if table has packaging-related headers
                    if any(kw in " ".join(headers) for kw in ["reel diameter", "length(mm)", "width(mm)", "height(mm)"]):
                        if verbose:
                            print(f"      Skipping - packaging table")
                        continue
                    
                    # Extract pin data from rows
                    for row in table[data_start_idx:]:
                        # Filter out None values from row
                        cleaned_row = [cell for cell in row if cell is not None and str(cell).strip()]
                        
                        # Skip empty rows
                        if len(cleaned_row) < 2:
                            continue
                        
                        max_idx = max(i for i in [pin_idx, name_idx, type_idx, direction_idx, description_idx] if i is not None)
                        if len(row) <= max_idx:
                            continue
                        
                        pin_num = str(row[pin_idx]).strip() if row[pin_idx] else ""
                        # Sometimes pin number is in the next column if first is empty
                        if not pin_num and pin_idx + 1 < len(row) and row[pin_idx + 1]:
                            pin_num = str(row[pin_idx + 1]).strip()
                        
                        name = str(row[name_idx]).strip() if row[name_idx] else ""
                        
                        # Clean and validate pin number and name
                        if not re.match(r"^\d+$", pin_num):
                            continue
                        
                        # Skip pin 0 (invalid)
                        pin_num_int = int(pin_num)
                        if pin_num_int == 0:
                            continue
                        
                        if len(name) < config.MIN_PIN_NAME_LENGTH or len(name) > config.MAX_PIN_NAME_LENGTH:
                            continue
                        
                        # Skip if name is just a single digit (e.g., "0")
                        if name.isdigit() and len(name) <= 2:
                            continue
                        
                        # Skip if name looks like a device/part number (e.g., ADS1115)
                        if re.match(r'^[A-Z]{3}\d{4}', name):
                            continue
                        
                        # Extract optional fields
                        pin_type = None
                        if type_idx is not None and len(row) > type_idx and row[type_idx]:
                            type_val = str(row[type_idx]).strip()
                            # Clean newlines and extra whitespace from cell values
                            type_val = re.sub(r'\s+', ' ', type_val)
                            type_lower = type_val.lower()
                            
                            # Handle combined types (e.g., "Analog input", "Digital output", "Digital I/O")
                            if 'analog' in type_lower and 'digital' in type_lower:
                                pin_type = "Analog/Digital"
                            elif 'analog' in type_lower:
                                pin_type = "Analog"
                            elif 'digital' in type_lower:
                                pin_type = "Digital"
                            elif 'power' in type_lower or 'supply' in type_lower:
                                pin_type = "Power"
                            elif 'ground' in type_lower or type_lower == 'gnd' or type_lower == 'ground':
                                pin_type = "Ground"
                            
                            # Check adjacent column for additional type info (e.g., BMP280 has "Supply" in next column)
                            if pin_type is None and type_idx + 1 < len(row) and row[type_idx + 1]:
                                adj_type = str(row[type_idx + 1]).strip().lower()
                                if 'supply' in adj_type or 'power' in adj_type:
                                    pin_type = "Power"
                        
                        direction = None
                        if direction_idx is not None and len(row) > direction_idx and row[direction_idx]:
                            dir_val = str(row[direction_idx]).strip()
                            # Clean newlines and extra whitespace
                            dir_val = re.sub(r'\s+', ' ', dir_val)
                            dir_lower = dir_val.lower()
                            
                            # Handle various direction formats
                            if 'i/o' in dir_lower or 'i / o' in dir_lower or 'bidirectional' in dir_lower or 'input/output' in dir_lower or 'inout' in dir_lower:
                                direction = "I/O"
                            elif 'output' in dir_lower:
                                direction = "Output"
                            elif 'input' in dir_lower:
                                direction = "Input"
                        
                        # Fallback: Extract type/direction from TYPE column if it contains both
                        # E.g., "Digital input" or "Analog output" or "DigitalInput" (no space)
                        if type_idx is not None and len(row) > type_idx and row[type_idx]:
                            type_val = str(row[type_idx]).strip()
                            type_val = re.sub(r'\s+', ' ', type_val)
                            type_lower = type_val.lower()
                            
                            # Extract direction from combined type field if direction not found
                            if direction is None:
                                if 'i/o' in type_lower or 'i / o' in type_lower or 'input/output' in type_lower or 'input / output' in type_lower:
                                    direction = "I/O"
                                elif 'output' in type_lower:
                                    direction = "Output"
                                elif 'input' in type_lower:
                                    direction = "Input"
                        
                        description = None
                        if description_idx is not None and len(row) > description_idx and row[description_idx]:
                            desc = str(row[description_idx]).strip()
                            if len(desc) > 3:  # Meaningful description
                                description = desc
                        
                        # Build flexible details dictionary
                        details = {}
                        if pin_type:
                            details["type"] = pin_type
                        if direction:
                            details["direction"] = direction
                        if description:
                            details["description"] = description
                        
                        # Create Pin object with flexible schema
                        pin_obj = Pin(
                            number=int(pin_num),
                            name=name,
                            details=details if details else None
                        )
                        
                        candidates.append((int(pin_num), pin_obj))
    except Exception as e:
        if verbose:
            print(f"  Table extraction error: {e}")
            import traceback
            traceback.print_exc()
        return None

    if verbose:
        print(f"  Found {len(candidates)} pin candidates from tables")

    # Fallback: Also check page text for pin definitions that might be outside tables
    # Pattern: "4 VSS Ground" or similar
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = min(50, len(pdf.pages))
            for page in pdf.pages[:pages_to_check]:
                text = page.extract_text()
                if not text:
                    continue
                
                # Look for lines like "4 VSS Ground" or "Pin 4: VSS - Ground"
                for line in text.split('\n'):
                    # Pattern: number name description
                    match = re.match(r'^(\d+)\s+([A-Z][A-Z0-9/_\-]{1,20})\s+(.+)', line.strip())
                    if match:
                        pin_num = int(match.group(1))
                        name = match.group(2).strip()
                        desc = match.group(3).strip()
                        
                        # Skip pin 0 (likely not a real pin)
                        if pin_num == 0:
                            continue
                        
                        # Skip if pin number is too high (likely not a pin table)
                        if pin_num > 256:  # Reasonable max for IC pins
                            continue
                        
                        # Skip if we already have this pin from table
                        if any(p[0] == pin_num for p in candidates):
                            continue
                        
                        # Validate it looks like a pin name (common pin name patterns)
                        # Must start with letter and not look like register/parameter names
                        if not re.match(r'^[A-Z]', name):
                            continue
                        
                        # Skip common false positives (register names, parameters, etc.)
                        false_positive_patterns = [
                            r'^DR$',  # Data Rate (not a pin)
                            r'^\d+$',  # Just numbers
                            r'^[A-Z]S$',  # XS pattern (might be other things)
                            r'^T[A-Z]$',  # TX pattern followed by single letter
                        ]
                        if any(re.match(pattern, name) for pattern in false_positive_patterns):
                            continue
                        
                        # Validate it looks like a pin (not random text)
                        if len(name) >= config.MIN_PIN_NAME_LENGTH and len(name) <= config.MAX_PIN_NAME_LENGTH:
                            # Additional validation: description should look reasonable
                            # (not just a number or formula)
                            if re.match(r'^[=<>]|^\d+$', desc):  # Starts with operator or just numbers
                                continue
                            
                            details = {"description": desc} if desc else None
                            pin_obj = Pin(
                                number=pin_num,
                                name=name,
                                details=details
                            )
                            candidates.append((pin_num, pin_obj))
                            if verbose:
                                print(f"    Found pin {pin_num} ({name}) from text")
    except Exception as e:
        if verbose:
            print(f"  Text fallback error: {e}")

    if verbose and len(candidates) > 0:
        print(f"  Total pin candidates (tables + text): {len(candidates)}")

    if not candidates:
        # Return metadata even if no pins found
        if metadata:
            return {
                "pins": [],
                "metadata": metadata
            }
        return None

    # Sort by pin number and deduplicate (keep first occurrence)
    seen = {}
    for pin_num, pin_obj in candidates:
        if pin_num not in seen:
            seen[pin_num] = pin_obj

    # Return pins in order with metadata
    pins = [seen[p] for p in sorted(seen.keys())]
    
    if verbose:
        print(f"  Extracted {len(pins)} unique pins")
    
    return {
        "pins": pins,
        "metadata": metadata
    }


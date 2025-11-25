"""Pydantic models for pin data schema."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Pin(BaseModel):
    """Schema for a single IC pin with flexible metadata."""
    
    number: int | str = Field(
        description="Pin number (e.g., 1, 2) or alphanumeric (e.g., 'A1', 'B2')"
    )
    
    name: str = Field(
        description="Primary pin name/signal name"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Flexible key-value pairs for any additional pin information (type, direction, description, alternate_names, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "number": 1,
                "name": "VDD",
                "details": {
                    "type": "Power",
                    "direction": "Input",
                    "description": "Power supply: 2.0V to 5.5V",
                    "voltage_range": "2.0V - 5.5V"
                }
            }
        }


class PinExtractionResult(BaseModel):
    """Schema for LLM pin extraction response."""
    
    pins: List[Pin] = Field(
        description="List of extracted pins from the datasheet page"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "pins": [
                    {
                        "number": 1,
                        "name": "ADDR",
                        "details": {
                            "type": "Digital",
                            "direction": "Input",
                            "description": "I2C slave address select"
                        }
                    },
                    {
                        "number": 2,
                        "name": "ALERT/RDY",
                        "details": {
                            "alternate_names": ["ALERT", "RDY"],
                            "type": "Digital",
                            "direction": "Output",
                            "description": "Digital comparator output or conversion ready"
                        }
                    }
                ]
            }
        }


class DatasheetMetadata(BaseModel):
    """Metadata extracted from the datasheet."""
    
    part_number: Optional[str] = Field(default=None, description="IC part number")
    title: Optional[str] = Field(default=None, description="Datasheet title")
    features: Optional[List[str]] = Field(default=None, description="List of key features")
    description: Optional[str] = Field(default=None, description="Product description")
    applications: Optional[List[str]] = Field(default=None, description="Typical applications")


class DatasheetExtractionResult(BaseModel):
    """Complete extraction result from all pages."""
    
    success: bool = Field(description="Whether extraction succeeded")
    total_pages: int = Field(description="Number of pages processed")
    pins: List[Pin] = Field(description="All extracted pins, deduplicated and sorted")
    extraction_method: str = Field(description="Method used: llm, table, ocr, or text")
    metadata: Optional[DatasheetMetadata] = Field(default=None, description="Datasheet metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_pages": 15,
                "extraction_method": "llm",
                "metadata": {
                    "part_number": "ADS1115",
                    "title": "16-Bit ADC with Internal Reference",
                    "features": ["Low power", "I2C interface"],
                    "applications": ["Portable instrumentation", "Battery monitoring"]
                },
                "pins": [
                    {
                        "number": 1,
                        "name": "VDD",
                        "details": {
                            "type": "Power",
                            "direction": "Input",
                            "description": "Power supply: 2.0V to 5.5V"
                        }
                    }
                ]
            }
        }


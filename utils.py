"""Utility functions for datasheet parsing."""

import os
import tempfile
import requests
from typing import Optional

import config


def download_pdf(url: str) -> str:
    """
    Download PDF from URL to temporary file.
    
    Args:
        url: URL of the PDF to download
        
    Returns:
        Path to the downloaded temporary PDF file
        
    Raises:
        requests.RequestException: If download fails
    """
    response = requests.get(url, timeout=config.DOWNLOAD_TIMEOUT)
    response.raise_for_status()

    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(response.content)

    return path


def format_pin_data(pins: list, include_indices: bool = True) -> dict:
    """
    Format pin data into structured dictionary.
    
    Args:
        pins: List of pin names
        include_indices: Whether to include pin indices (1-based)
        
    Returns:
        Dictionary with formatted pin data
    """
    if include_indices:
        pin_list = [{"pin": i, "name": name} for i, name in enumerate(pins, 1)]
    else:
        pin_list = pins
        
    return {
        "pins": pin_list,
        "count": len(pins)
    }

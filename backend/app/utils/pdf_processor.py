"""
PDF Processing Utility.
Extracts text and metadata from PDF files using pypdf and pdfplumber.
"""

import pypdf
import pdfplumber
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Extract text and metadata from PDF files."""
    
    @staticmethod
    def extract_text_and_metadata(pdf_path: str) -> Tuple[str, Dict]:
        """
        Extract all text and metadata from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (full_text, metadata_dict)
        """
        try:
            full_text = ""
            metadata = {
                "pages": 0,
                "title": "",
                "author": "",
                "has_images": False,
                "has_tables": False
            }
            
            # Use pdfplumber for better text extraction
            with pdfplumber.open(pdf_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                
                # Extract text from each page
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += f"\n\n--- Page {i+1} ---\n\n"
                            full_text += page_text
                        
                        # Check for tables
                        if page.extract_tables():
                            metadata["has_tables"] = True
                        
                        # Check for images
                        if page.images:
                            metadata["has_images"] = True
                    
                    except Exception as e:
                        logger.warning(f"Error extracting page {i+1}: {e}")
                        continue
            
            # Get metadata using pypdf
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_reader = pypdf.PdfReader(f)
                    if pdf_reader.metadata:
                        metadata["title"] = pdf_reader.metadata.get("/Title", "")
                        metadata["author"] = pdf_reader.metadata.get("/Author", "")
            except:
                pass
            
            logger.info(f"✓ Extracted {len(full_text)} characters from {metadata['pages']} pages")
            return full_text, metadata
        
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise
    
    @staticmethod
    def validate_pdf(pdf_path: str, max_pages: int = 50) -> Tuple[bool, str]:
        """
        Validate PDF file.
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum allowed pages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path = Path(pdf_path)
            
            # Check file exists
            if not path.exists():
                return False, "File not found"
            
            # Check file size (max 50MB for learning project)
            max_size = 50 * 1024 * 1024  # 50MB
            if path.stat().st_size > max_size:
                return False, f"File too large. Max size: 50MB"
            
            # Check it's a valid PDF
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)
            
            # Check page count
            if num_pages > max_pages:
                return False, f"Too many pages. Max allowed: {max_pages} (for cost control)"
            
            if num_pages == 0:
                return False, "PDF has no pages"
            
            return True, ""
        
        except Exception as e:
            return False, f"Invalid PDF: {str(e)}"
"""
Text Chunking Utility.
Splits text into semantic chunks using LlamaIndex's SentenceSplitter.
"""

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document
from typing import List
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """Split text into semantic chunks."""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Overlap between chunks (for context preservation)
        """
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            paragraph_separator="\n\n",
        )
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[Document]:
        """
        Split text into chunks while preserving context.
        
        Args:
            text: Full document text
            metadata: Document metadata to attach to chunks
            
        Returns:
            List of Document objects (LlamaIndex format)
        """
        try:
            # Create base metadata
            base_metadata = metadata or {}
            
            # Create LlamaIndex document
            doc = Document(text=text, metadata=base_metadata)
            
            # Split into nodes
            nodes = self.splitter.get_nodes_from_documents([doc])
            
            # Convert back to documents with chunk metadata
            chunks = []
            for i, node in enumerate(nodes):
                chunk_metadata = {
                    **base_metadata,
                    "chunk_id": i,
                    "total_chunks": len(nodes)
                }
                chunk_doc = Document(
                    text=node.get_content(),
                    metadata=chunk_metadata
                )
                chunks.append(chunk_doc)
            
            logger.info(f"✓ Created {len(chunks)} chunks from text")
            return chunks
        
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            raise
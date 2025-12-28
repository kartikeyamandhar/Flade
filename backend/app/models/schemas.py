"""
Pydantic data models for API requests and responses.
Defines the schema for all data structures used in the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    """Response after document upload."""
    document_id: str
    filename: str
    size: int
    pages: int
    status: DocumentStatus
    message: str


class ProcessingProgress(BaseModel):
    """Document processing progress information."""
    document_id: str
    status: DocumentStatus
    progress_percent: int
    current_step: str
    chunks_processed: int
    total_chunks: int
    entities_extracted: int
    relationships_created: int
    estimated_time_remaining: Optional[int] = None
    error_message: Optional[str] = None


class QueryRequest(BaseModel):
    """Request to query a document."""
    document_id: str
    question: str
    include_context: bool = True
    retrieval_method: Optional[str] = None  # auto, vector, graph, text2cypher


class QueryResponse(BaseModel):
    """Response from document query."""
    answer: str
    sources: List[Dict[str, Any]]
    retrieval_method: str
    graph_visualization: Optional[Dict[str, Any]] = None
    flowchart: Optional[str] = None  # Mermaid syntax
    context_used: Optional[List[Dict[str, Any]]] = None


class GraphStats(BaseModel):
    """Statistics about the knowledge graph."""
    total_nodes: int
    total_relationships: int
    node_types: Dict[str, int]
    relationship_types: Dict[str, int]


class DocumentInfo(BaseModel):
    """Information about a processed document."""
    document_id: str
    filename: str
    upload_date: datetime
    status: DocumentStatus
    pages: int
    graph_stats: Optional[GraphStats] = None
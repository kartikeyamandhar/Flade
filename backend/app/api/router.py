"""
API Router - FIXED for async event loop.
Uses ThreadPoolExecutor to avoid asyncio.run() conflicts.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import shutil
import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import functools

from app.models.schemas import (
    UploadResponse,
    ProcessingProgress,
    QueryRequest,
    QueryResponse,
    GraphStats,
    DocumentInfo,
    DocumentStatus
)
from app.services.document_service import DocumentService
from app.services.retriever import SimpleAsyncRetriever
from app.core.config import settings
from app.core.database import db

logger = logging.getLogger(__name__)

# Create router
api_router = APIRouter()

# Services
doc_service = DocumentService()
retriever = SimpleAsyncRetriever()

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=3)

# In-memory storage for demo (use database in production)
documents_db = {}


@api_router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process a PDF document.
    
    - **file**: PDF file to upload
    
    Returns document ID and processing status.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are allowed")
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{document_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File uploaded: {file.filename} -> {document_id}")
        
        # Get file size and validate
        file_size = file_path.stat().st_size
        
        # Quick page count check
        import pypdf
        with open(file_path, 'rb') as f:
            pdf = pypdf.PdfReader(f)
            num_pages = len(pdf.pages)
        
        # Store document info
        documents_db[document_id] = {
            "document_id": document_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "size": file_size,
            "pages": num_pages,
            "status": DocumentStatus.UPLOADED,
            "upload_date": datetime.now()
        }
        
        # Start background processing in thread pool
        background_tasks.add_task(
            process_document_in_thread,
            str(file_path),
            document_id
        )
        
        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            size=file_size,
            pages=num_pages,
            status=DocumentStatus.PROCESSING,
            message=f"Document uploaded successfully. Processing {num_pages} pages..."
        )
    
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


def process_document_sync(file_path: str, document_id: str):
    """
    Synchronous document processing (runs in thread pool).
    This avoids asyncio.run() conflicts.
    """
    try:
        logger.info(f"Starting background processing for {document_id}")
        
        # Update status
        if document_id in documents_db:
            documents_db[document_id]["status"] = DocumentStatus.PROCESSING
        
        # Import here to avoid issues
        from app.services.document_service import DocumentService
        
        service = DocumentService()
        
        # Call the synchronous version
        # We'll need to modify document_service to have a sync version
        result = service.process_document_sync(
            file_path=file_path,
            document_id=document_id,
        )
        
        # Update document status
        if document_id in documents_db:
            documents_db[document_id].update({
                "status": DocumentStatus.COMPLETED,
                **result
            })
        
        logger.info(f"✓ Background processing complete for {document_id}")
    
    except Exception as e:
        logger.error(f"Background processing failed for {document_id}: {e}")
        if document_id in documents_db:
            documents_db[document_id]["status"] = DocumentStatus.FAILED
            documents_db[document_id]["error"] = str(e)


async def process_document_in_thread(file_path: str, document_id: str):
    """
    Run document processing in a thread pool to avoid event loop conflicts.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        executor,
        process_document_sync,
        file_path,
        document_id
    )


@api_router.get("/documents/{document_id}/status", response_model=ProcessingProgress)
async def get_processing_status(document_id: str):
    """
    Get processing status for a document.
    
    - **document_id**: Unique document identifier
    
    Returns current processing progress.
    """
    try:
        # Get from service
        status = doc_service.get_processing_status(document_id)
        
        # If not in processing, get from documents_db
        if not status or status.get("status") == "not_found":
            if document_id in documents_db:
                doc_info = documents_db[document_id]
                status = {
                    "document_id": document_id,
                    "status": doc_info["status"],
                    "progress_percent": 100 if doc_info["status"] == "completed" else 0,
                    "current_step": "Complete" if doc_info["status"] == "completed" else "Unknown",
                    "chunks_processed": doc_info.get("chunks", 0),
                    "total_chunks": doc_info.get("chunks", 0),
                    "entities_extracted": 0,
                    "relationships_created": 0,
                }
            else:
                raise HTTPException(404, "Document not found")
        
        return ProcessingProgress(**status)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(500, str(e))


@api_router.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """
    Query a processed document.
    
    - **document_id**: Document to query
    - **question**: User's question
    - **include_context**: Include retrieved context (optional)
    - **retrieval_method**: Specific method or "auto" (optional)
    
    Returns answer with sources and metadata.
    """
    try:
        # Check document exists and is processed
        if request.document_id not in documents_db:
            raise HTTPException(404, "Document not found")
        
        doc_info = documents_db[request.document_id]
        if doc_info["status"] != DocumentStatus.COMPLETED:
            raise HTTPException(400, f"Document is not ready. Status: {doc_info['status']}")
        
        # Execute query
        result = await retriever.aquery(
            question=request.question,
            document_id=request.document_id,
            include_context=request.include_context  # ✅ Clean!
        )
        
        return QueryResponse(
            answer=result.get("answer", "No answer generated"),
            sources=result.get("sources", []),
            retrieval_method=result.get("retrieval_method", "unknown"),
            context_used=result.get("context") if request.include_context else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(500, f"Query failed: {str(e)}")


@api_router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """
    List all uploaded documents.
    
    Returns list of all documents with their metadata.
    """
    try:
        docs = []
        for doc_id, doc_info in documents_db.items():
            docs.append(DocumentInfo(
                document_id=doc_id,
                filename=doc_info["filename"],
                upload_date=doc_info.get("upload_date", datetime.now()),
                status=doc_info["status"],
                pages=doc_info.get("pages", 0),
                graph_stats=None  # Would fetch actual stats in production
            ))
        
        return docs
    
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(500, str(e))


@api_router.get("/graph/{document_id}/stats", response_model=GraphStats)
async def get_graph_stats(document_id: str):
    """
    Get graph statistics for a document.
    
    - **document_id**: Document identifier
    
    Returns node and relationship counts by type.
    """
    try:
        # This would query Neo4j for actual stats
        # Simplified for learning project
        driver = db.get_driver()
        with driver.session() as session:
            # Total nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = result.single()["count"]
            
            # Total relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_rels = result.single()["count"]
            
            # Node types
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
            """)
            node_types = {r["label"]: r["count"] for r in result if r["label"]}
            
            # Relationship types
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
            """)
            rel_types = {r["type"]: r["count"] for r in result}
        
        return GraphStats(
            total_nodes=total_nodes,
            total_relationships=total_rels,
            node_types=node_types,
            relationship_types=rel_types
        )
    
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(500, str(e))


@api_router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system health status.
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "neo4j_connected": db.get_driver() is not None,
        "documents_count": len(documents_db)
    }

@api_router.get("/graph/{document_id}/data")
async def get_graph_data(document_id: str, limit: int = 100):
    """Get graph nodes and links for visualization"""
    try:
        driver = db.get_driver()
        
        with driver.session() as session:
            # Get nodes
            result = session.run("""
                MATCH (n:Entity {document_id: $doc_id})
                RETURN n.name as name, id(n) as id
                LIMIT $limit
            """, doc_id=document_id, limit=limit)
            
            nodes = [{"id": r["id"], "name": r["name"]} for r in result]
            node_ids = {n["id"] for n in nodes}
            
            # Get relationships between those nodes
            result = session.run("""
                MATCH (a:Entity {document_id: $doc_id})-[r]->(b:Entity {document_id: $doc_id})
                WHERE id(a) IN $node_ids AND id(b) IN $node_ids
                RETURN id(a) as source, id(b) as target, r.type as type
                LIMIT $limit
            """, doc_id=document_id, node_ids=list(node_ids), limit=limit)
            
            links = [{"source": r["source"], "target": r["target"], "type": r["type"]} for r in result]
        
        return {
            "nodes": nodes,
            "links": links
        }
    
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}")
        raise HTTPException(500, str(e))
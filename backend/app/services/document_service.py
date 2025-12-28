# import uuid
# import json
# from pathlib import Path
# from typing import Dict, Callable
# import logging
# from app.utils.pdf_processor import PDFProcessor
# from app.utils.chunker import TextChunker
# from app.services.graph_builder import KnowledgeGraphBuilder
# from app.core.config import settings

# logger = logging.getLogger(__name__)


# class DocumentService:
#     """Document processing service with proper stats reporting"""
    
#     def __init__(self):
#         self.pdf_processor = PDFProcessor()
#         self.chunker = TextChunker(
#             chunk_size=settings.CHUNK_SIZE,
#             chunk_overlap=settings.CHUNK_OVERLAP
#         )
#         self.graph_builder = KnowledgeGraphBuilder()
        
#         # Track processing status
#         self.processing_status = {}
    
#     def process_document_sync(
#         self,
#         file_path: str,
#         document_id: str,
#         progress_callback: Callable[[Dict], None] = None
#     ) -> Dict:
#         """Process document and report stats correctly"""
        
#         try:
#             # Initialize status
#             status = {
#                 "document_id": document_id,
#                 "status": "processing",
#                 "progress_percent": 0,
#                 "current_step": "Starting...",
#                 "chunks_processed": 0,
#                 "total_chunks": 0,
#                 "entities_extracted": 0,
#                 "relationships_created": 0,
#                 "error_message": None
#             }
#             self.processing_status[document_id] = status
            
#             def update_progress(percent: int, step: str, **kwargs):
#                 status["progress_percent"] = percent
#                 status["current_step"] = step
#                 status.update(kwargs)
#                 self.processing_status[document_id] = status
#                 if progress_callback:
#                     progress_callback(status)
            
#             # Step 1: Validate
#             update_progress(5, "Validating PDF...")
#             is_valid, error_msg = self.pdf_processor.validate_pdf(
#                 file_path,
#                 max_pages=settings.MAX_PAGES_PER_DOCUMENT
#             )
#             if not is_valid:
#                 raise ValueError(error_msg)
            
#             # Step 2: Extract text
#             update_progress(10, "Extracting text...")
#             full_text, metadata = self.pdf_processor.extract_text_and_metadata(file_path)
            
#             if not full_text or len(full_text.strip()) < 100:
#                 raise ValueError("PDF contains insufficient text")
            
#             # Step 3: Chunk text
#             update_progress(20, "Creating text chunks...")
#             chunks = self.chunker.chunk_text(
#                 full_text,
#                 metadata={
#                     "document_id": document_id,
#                     "filename": Path(file_path).name,
#                     "total_pages": metadata["pages"]
#                 }
#             )
            
#             update_progress(30, f"Created {len(chunks)} chunks", total_chunks=len(chunks))
            
#             # Step 4: Build graph
#             update_progress(40, "Building knowledge graph...")
            
#             def graph_progress(percent: int, message: str):
#                 overall_percent = 40 + int((percent / 100) * 50)
#                 update_progress(overall_percent, message)
            
#             stats = self.graph_builder.build_graph(
#                 documents=chunks,
#                 document_id=document_id,
#                 progress_callback=graph_progress
#             )
            
#             # CRITICAL: Update stats from graph builder
#             update_progress(
#                 95,
#                 "Processing complete!",
#                 chunks_processed=len(chunks),
#                 entities_extracted=stats.get('total_nodes', 0),
#                 relationships_created=stats.get('total_relationships', 0)
#             )
            
#             # Step 5: Save metadata
#             result = {
#                 "document_id": document_id,
#                 "filename": Path(file_path).name,
#                 "pages": metadata["pages"],
#                 "chunks": len(chunks),
#                 "entities": stats.get('total_nodes', 0),
#                 "relationships": stats.get('total_relationships', 0),
#                 "status": "completed"
#             }
            
#             metadata_file = Path(settings.UPLOAD_DIR) / f"{document_id}_metadata.json"
#             with open(metadata_file, 'w') as f:
#                 json.dump(result, f, indent=2)
            
#             # Final update
#             update_progress(
#                 100,
#                 "Complete!",
#                 status="completed",
#                 entities_extracted=stats.get('total_nodes', 0),
#                 relationships_created=stats.get('total_relationships', 0)
#             )
            
#             logger.info(f"✓ Document {document_id} processed successfully")
#             logger.info(f"  Entities: {result['entities']}, Relationships: {result['relationships']}")
            
#             return result
            
#         except Exception as e:
#             logger.error(f"Document processing failed: {e}")
#             update_progress(0, "Processing failed", status="failed", error_message=str(e))
#             raise
    
#     def get_processing_status(self, document_id: str) -> Dict:
#         """Get current processing status"""
#         return self.processing_status.get(document_id, {
#             "document_id": document_id,
#             "status": "not_found",
#             "error_message": "Document not found"
#         })

import uuid
import json
from pathlib import Path
from typing import Dict, Callable
import logging
from app.utils.pdf_processor import PDFProcessor
from app.utils.chunker import TextChunker
from app.services.graph_builder import KnowledgeGraphBuilder
from app.services.document_validator import DocumentTypeValidator
from app.core.config import settings
from app.core.database import db

logger = logging.getLogger(__name__)


class DocumentService:
    """Document processing service with type validation"""
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.chunker = TextChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.graph_builder = KnowledgeGraphBuilder()
        self.validator = DocumentTypeValidator(db.get_llm())
        
        # Track processing status
        self.processing_status = {}
    
    def process_document_sync(
        self,
        file_path: str,
        document_id: str,
        progress_callback: Callable[[Dict], None] = None
    ) -> Dict:
        """Process document with type validation"""
        
        try:
            # Initialize status
            status = {
                "document_id": document_id,
                "status": "processing",
                "progress_percent": 0,
                "current_step": "Starting...",
                "chunks_processed": 0,
                "total_chunks": 0,
                "entities_extracted": 0,
                "relationships_created": 0,
                "error_message": None
            }
            self.processing_status[document_id] = status
            
            def update_progress(percent: int, step: str, **kwargs):
                status["progress_percent"] = percent
                status["current_step"] = step
                status.update(kwargs)
                self.processing_status[document_id] = status
                if progress_callback:
                    progress_callback(status)
            
            # Step 1: Validate
            update_progress(5, "Validating PDF...")
            is_valid, error_msg = self.pdf_processor.validate_pdf(
                file_path,
                max_pages=settings.MAX_PAGES_PER_DOCUMENT
            )
            if not is_valid:
                raise ValueError(error_msg)
            
            # Step 2: Extract text
            update_progress(10, "Extracting text...")
            full_text, metadata = self.pdf_processor.extract_text_and_metadata(file_path)
            
            if not full_text or len(full_text.strip()) < 100:
                raise ValueError("PDF contains insufficient text")
            
            # Step 3: VALIDATE DOCUMENT TYPE (NEW!)
            update_progress(15, "Validating document type...")
            
            import asyncio
            
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run async validation
            is_procedural, doc_type, rejection_msg = loop.run_until_complete(
                self.validator.validate_document_type(
                    full_text[:2000],
                    Path(file_path).name
                )
            )
            
            if not is_procedural:
                logger.warning(f"❌ Document rejected: {doc_type}")
                raise ValueError(f"DOCUMENT_TYPE_REJECTED:{doc_type}:{rejection_msg}")
            
            logger.info(f"✓ Document type validated: {doc_type}")
            
            # Step 4: Chunk text
            update_progress(20, "Creating text chunks...")
            chunks = self.chunker.chunk_text(
                full_text,
                metadata={
                    "document_id": document_id,
                    "filename": Path(file_path).name,
                    "total_pages": metadata["pages"]
                }
            )
            
            update_progress(30, f"Created {len(chunks)} chunks", total_chunks=len(chunks))
            
            # Step 5: Build graph
            update_progress(40, "Building knowledge graph...")
            
            def graph_progress(percent: int, message: str):
                overall_percent = 40 + int((percent / 100) * 50)
                update_progress(overall_percent, message)
            
            stats = self.graph_builder.build_graph(
                documents=chunks,
                document_id=document_id,
                progress_callback=graph_progress
            )
            
            # Update stats
            update_progress(
                95,
                "Processing complete!",
                chunks_processed=len(chunks),
                entities_extracted=stats.get('total_nodes', 0),
                relationships_created=stats.get('total_relationships', 0)
            )
            
            # Step 6: Save metadata
            update_progress(95, "Saving document metadata...")
            result = {
                "document_id": document_id,
                "filename": Path(file_path).name,
                "pages": metadata["pages"],
                "chunks": len(chunks),
                "entities": stats.get('total_nodes', 0),
                "relationships": stats.get('total_relationships', 0),
                "status": "completed",
                "document_type": doc_type
            }
            
            # Save to JSON
            metadata_file = Path(settings.UPLOAD_DIR) / f"{document_id}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            # Final update
            update_progress(
                100,
                "Complete!",
                status="completed",
                entities_extracted=stats.get('total_nodes', 0),
                relationships_created=stats.get('total_relationships', 0)
            )
            
            logger.info(f"✓ Document {document_id} processed successfully")
            logger.info(f"  Entities: {result['entities']}, Relationships: {result['relationships']}")
            
            return result
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a document type rejection
            if error_str.startswith("DOCUMENT_TYPE_REJECTED:"):
                parts = error_str.split(":", 2)
                doc_type = parts[1] if len(parts) > 1 else "unknown"
                rejection_msg = parts[2] if len(parts) > 2 else "Document type not supported"
                
                update_progress(
                    0,
                    "Document type not supported",
                    status="rejected",
                    error_message=rejection_msg,
                    document_type=doc_type
                )
            else:
                logger.error(f"Document processing failed: {e}")
                update_progress(0, "Processing failed", status="failed", error_message=str(e))
            
            raise
    
    def get_processing_status(self, document_id: str) -> Dict:
        """Get current processing status"""
        return self.processing_status.get(document_id, {
            "document_id": document_id,
            "status": "not_found",
            "error_message": "Document not found"
        })
from llama_index.core import Document
from llama_index.llms.openai import OpenAI
from typing import List, Dict, Callable
import logging
import time
import json
import os
from app.core.database import db
from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """Production-grade knowledge graph builder with reliable extraction"""
    
    def __init__(self):
        self.graph_store = db.get_graph_store()
        self.llm = db.get_llm()
        self.embed_model = db.get_embed_model()
    
    def build_graph(
        self,
        documents: List[Document],
        document_id: str,
        progress_callback: Callable[[int, str], None] = None
    ):
        """Build knowledge graph with custom reliable extraction"""
        try:
            logger.info(f"Building knowledge graph for document: {document_id}")
            start_time = time.time()
            
            if progress_callback:
                progress_callback(10, "Starting entity extraction...")
            
            # Extract entities using direct LLM calls (more reliable)
            all_entities = []
            all_relationships = []
            
            total_chunks = len(documents)
            for i, doc in enumerate(documents):
                if progress_callback:
                    percent = 20 + int((i / total_chunks) * 60)
                    progress_callback(percent, f"Extracting from chunk {i+1}/{total_chunks}...")
                
                entities, relationships = self._extract_from_chunk(doc.get_content(), document_id)
                all_entities.extend(entities)
                all_relationships.extend(relationships)
                
                logger.info(f"Chunk {i+1}: {len(entities)} entities, {len(relationships)} relationships")
            
            if progress_callback:
                progress_callback(85, "Saving to Neo4j...")
            
            # Save to Neo4j
            self._save_to_neo4j(all_entities, all_relationships, document_id)
            
            # Get stats
            stats = self._get_graph_stats(document_id)
            
            elapsed = time.time() - start_time
            logger.info(f"✓ Knowledge graph built in {elapsed:.2f}s")
            logger.info(f"  Entities: {stats['total_nodes']}, Relationships: {stats['total_relationships']}")
            
            if progress_callback:
                progress_callback(100, "Complete!")
            
            return stats
            
        except Exception as e:
            logger.error(f"Graph building failed: {e}", exc_info=True)
            raise
    
    def _extract_from_chunk(self, text: str, document_id: str) -> tuple:
        """Extract entities and relationships from text chunk using direct LLM"""
        
        prompt = f"""Extract entities and relationships from this technical manual text.

TEXT:
{text}

Extract in JSON format:
{{
  "entities": [
    {{"name": "entity name", "type": "EQUIPMENT|COMPONENT|TOOL|SPECIFICATION|PROCEDURE|FEATURE|ACCESSORY"}},
    ...
  ],
  "relationships": [
    {{"from": "entity1", "to": "entity2", "type": "REQUIRES|HAS_SPEC|PART_OF|COMPATIBLE_WITH|HAS_FEATURE"}},
    ...
  ]
}}

ENTITY TYPES:
- EQUIPMENT: Main devices (PlayStation 5, Camera, etc.)
- COMPONENT: Parts (HDMI Cable, Controller, Power Cord, etc.)
- TOOL: Tools needed (Screwdriver, etc.)
- SPECIFICATION: Technical specs (4K, 825GB SSD, HDMI 2.1, etc.)
- PROCEDURE: Tasks/processes (Setup, Installation, etc.)
- FEATURE: Capabilities (Ray Tracing, Haptic Feedback, etc.)
- ACCESSORY: Compatible accessories (VR Headset, Media Remote, etc.)

RELATIONSHIP TYPES:
- REQUIRES: X requires Y
- HAS_SPEC: X has specification Y
- PART_OF: X is part of Y
- COMPATIBLE_WITH: X works with Y
- HAS_FEATURE: X has feature Y

Extract ONLY information explicitly mentioned in the text.
Be accurate and specific.
Return valid JSON only."""

        try:
            response = self.llm.complete(prompt)
            result_text = response.text.strip()
            
            # Clean up JSON (remove markdown code blocks if present)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            data = json.loads(result_text)
            
            # Add document_id to entities
            entities = []
            for entity in data.get("entities", []):
                entity["document_id"] = document_id
                entities.append(entity)
            
            relationships = data.get("relationships", [])
            
            return entities, relationships
            
        except Exception as e:
            logger.error(f"Extraction failed for chunk: {e}")
            return [], []
    
    def _save_to_neo4j(self, entities: List[Dict], relationships: List[Dict], document_id: str):
        """Save entities and relationships to Neo4j"""
        
        try:
            driver = db.get_driver()
            with driver.session() as session:
                # Create entities
                for entity in entities:
                    query = f"""
                    MERGE (n:{entity['type']} {{name: $name, document_id: $document_id}})
                    RETURN n
                    """
                    session.run(query, name=entity['name'], document_id=document_id)
                
                logger.info(f"Created {len(entities)} entities")
                
                # Create relationships
                relationship_count = 0
                for rel in relationships:
                    try:
                        query = f"""
                        MATCH (a {{name: $from_name, document_id: $document_id}})
                        MATCH (b {{name: $to_name, document_id: $document_id}})
                        MERGE (a)-[r:{rel['type']}]->(b)
                        RETURN r
                        """
                        result = session.run(
                            query, 
                            from_name=rel['from'], 
                            to_name=rel['to'],
                            document_id=document_id
                        )
                        if result.single():
                            relationship_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to create relationship: {e}")
                        continue
                
                logger.info(f"Created {relationship_count} relationships")
                
        except Exception as e:
            logger.error(f"Failed to save to Neo4j: {e}")
            raise
    
    def _get_graph_stats(self, document_id: str) -> Dict:
        """Get graph statistics"""
        try:
            driver = db.get_driver()
            with driver.session() as session:
                # Count nodes
                result = session.run(
                    "MATCH (n) WHERE n.document_id = $document_id RETURN count(n) as count",
                    document_id=document_id
                )
                node_count = result.single()["count"]
                
                # Count relationships
                result = session.run(
                    """MATCH (a)-[r]->(b) 
                       WHERE a.document_id = $document_id 
                       RETURN count(r) as count""",
                    document_id=document_id
                )
                rel_count = result.single()["count"]
                
                return {
                    "total_nodes": node_count,
                    "total_relationships": rel_count,
                    "node_types": {},
                    "relationship_types": {}
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "node_types": {},
                "relationship_types": {}
            }


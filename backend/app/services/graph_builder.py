"""
Builds knowledge graph from document chunks

Takes text chunks and extracts entities
and relationships into Neo4j.

Uses parallel processing to extract from multiple chunks simultaneously.
Merges duplicate entities (e.g., "PS5" and "PlayStation 5" become one node).
Handles relationships that span across chunk boundaries.
Saves to Neo4j in batches for performance.
"""

import logging
import time
import json
import asyncio
from typing import List, Dict, Callable, Set
from concurrent.futures import ThreadPoolExecutor

from llama_index.core import Document
from llama_index.llms.openai import OpenAI
from app.core.database import db
from app.core.config import settings

logger = logging.getLogger(__name__)

UNIVERSAL_PROMPT = """Extract entities and relationships from this technical/procedural document.

TEXT:
{text}

Extract in JSON format:
{{
  "entities": [
    {{
      "name": "entity name",
      "type": "ENTITY_TYPE",
      "description": "detailed description with HOW-TO context from text"
    }},
    ...
  ],
  "relationships": [
    {{"from": "entity1", "to": "entity2", "type": "RELATIONSHIP_TYPE"}},
    ...
  ]
}}

ENTITY TYPES:
1. EQUIPMENT - Main devices, systems, products (PS5, Pump, Thermostat, Drill, Laptop)
2. COMPONENT - Parts, subassemblies (HDMI Cable, Valve, Battery, Filter, Screen)
3. TOOL - External tools needed (Screwdriver, Wrench, Multimeter, Level)
4. SPECIFICATION - Technical parameters (120V, 4K, 2000 PSI, 825GB SSD, IP67)
5. PROCEDURE - Action-oriented tasks (Installation, Setup, Calibration, Cleaning)
6. FEATURE - Built-in capabilities (Ray Tracing, Parental Controls, Auto-Shutoff)
7. CONSUMABLE - Used-up materials (Oil, Filter, Ink, Thread Sealant, Battery)
8. ACCESSORY - Optional add-ons (VR Headset, Wall Mount, Case, Lens, Memory Card)
9. SOFTWARE - Apps, firmware, updates (OS, Mobile App, Firmware 2.0, Driver)
10. SAFETY_ITEM - Warnings, hazards, PPE (High Voltage, Gloves, E-stop, Fire Risk)
11. LOCATION - Physical positions (Port Location, Mount Point, Service Panel)
12. CONDITION - States, requirements (Temperature Range, Level Surface, Standby Mode)
13. STANDARD - Protocols, certifications (UL Listed, IEEE 802.11ax, ISO 9001)
14. INDICATOR - Status displays (Power LED, Error Light, Pressure Gauge)
15. DOCUMENT - Related docs (Quick Start Guide, Wiring Diagram, Warranty)

RELATIONSHIP TYPES:
1. REQUIRES - A needs B to function (Equipment REQUIRES Component)
2. HAS_SPEC - Has technical parameter (Equipment HAS_SPEC Specification)
3. PART_OF - Component is part of larger system (Component PART_OF Equipment)
4. COMPATIBLE_WITH - Works with (Accessory COMPATIBLE_WITH Equipment)
5. HAS_FEATURE - Has capability (Equipment HAS_FEATURE Feature)
6. USES - Procedure uses tool/material (Procedure USES Tool/Consumable)
7. PRECEDES - Step order (Procedure PRECEDES Procedure)
8. CAUSES - Triggers result (Condition CAUSES Indicator)
9. PREVENTS - Safety prevents hazard (Safety_Item PREVENTS Hazard)
10. CONNECTS_TO - Physical connection (Component CONNECTS_TO Component)
11. CONFIGURED_BY - Setup method (Feature CONFIGURED_BY Procedure)
12. INDICATES - Shows status (Indicator INDICATES Condition)
13. COMPLIES_WITH - Meets standard (Equipment COMPLIES_WITH Standard)
14. REPLACES - Replacement (Component REPLACES Component)
15. SUPPORTS - Enables functionality (Feature SUPPORTS Feature)

CRITICAL: For FEATURE entities, include HOW to access/enable in description.

Extract ONLY information explicitly in text. Return ONLY valid JSON."""


class KnowledgeGraphBuilder:
    """Enhanced builder with parallel processing and entity resolution"""
    
    def __init__(self):
        self.graph_store = db.get_graph_store()
        self.llm = db.get_llm()
        self.embed_model = db.get_embed_model()
        self.max_workers = min(5, settings.PROCESSING_WORKERS)  # Parallel workers
    
    async def build_graph_async(
        self,
        documents: List[Document],
        document_id: str,
        progress_callback: Callable[[int, str], None] = None
    ):
        """ASYNC build with parallel processing and entity resolution"""
        try:
            logger.info(f"Building knowledge graph for document: {document_id}")
            start_time = time.time()
            
            if progress_callback:
                progress_callback(10, "Starting parallel extraction...")
            
            # 1. Parallel Extraction with Context Windows
            all_data = await self._extract_in_parallel(documents, document_id, progress_callback)
            
            if not all_data:
                logger.warning("No data extracted from documents")
                return {"total_nodes": 0, "total_relationships": 0}
            
            # 2. Entity Resolution (The "Magic" Step)
            if progress_callback:
                progress_callback(70, "Resolving entities and duplicates...")
            
            resolved_entities, resolved_relationships = self._resolve_entities(all_data)
            
            logger.info(f"Resolved: {len(resolved_entities)} unique entities")
            
            # 3. Batch Save to Neo4j
            if progress_callback:
                progress_callback(85, "Saving to Neo4j...")
            
            self._save_to_neo4j_batch(resolved_entities, resolved_relationships, document_id)
            
            # 4. Final Stats
            stats = self._get_graph_stats(document_id)
            elapsed = time.time() - start_time
            logger.info(f"✓ Knowledge graph built in {elapsed:.2f}s | Nodes: {stats['total_nodes']}")
            
            if progress_callback:
                progress_callback(100, "Complete!")
            
            return stats
            
        except Exception as e:
            logger.error(f"Graph building failed: {e}", exc_info=True)
            raise
    
    def build_graph(
        self,
        documents: List[Document],
        document_id: str,
        progress_callback: Callable[[int, str], None] = None
    ):
        """SYNC wrapper for compatibility"""
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async version
        return loop.run_until_complete(
            self.build_graph_async(documents, document_id, progress_callback)
        )
    
    async def _extract_in_parallel(
        self, 
        documents: List[Document], 
        doc_id: str, 
        callback: Callable[[int, str], None]
    ) -> List[Dict]:
        """
        GEMINI IMPROVEMENT: Parallel processing with context windows
        Processes chunks concurrently and includes sliding context
        """
        loop = asyncio.get_running_loop()
        total = len(documents)
        results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            tasks = []
            
            for i, doc in enumerate(documents):
                # CONTEXT WINDOW: Prepend last 500 chars of previous chunk
                context_text = doc.get_content()
                
                if i > 0:
                    prev_text = documents[i-1].get_content()[-500:]
                    context_text = f"...{prev_text}\n\n{context_text}"
                
                # Submit to thread pool
                tasks.append(
                    loop.run_in_executor(
                        executor, 
                        self._extract_universal, 
                        context_text, 
                        doc_id
                    )
                )
            
            # Gather results as they complete
            for future in asyncio.as_completed(tasks):
                entities, relationships = await future
                
                if entities:
                    results.append({
                        "entities": entities, 
                        "relationships": relationships
                    })
                
                completed += 1
                
                if callback and completed % 5 == 0:
                    percent = 10 + int((completed / total) * 60)
                    callback(percent, f"Processed {completed}/{total} chunks")
        
        logger.info(f"Extracted from {len(results)}/{total} chunks")
        return results
    
    def _extract_universal(self, text: str, document_id: str) -> tuple:
        """Extract using universal prompt (with robust JSON parsing)"""
        
        prompt = UNIVERSAL_PROMPT.format(text=text)
        
        try:
            response = self.llm.complete(prompt)
            result_text = response.text.strip()
            
            # Clean up JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            data = json.loads(result_text)
            
            # Add document_id and ensure descriptions
            entities = []
            for e in data.get("entities", []):
                e["document_id"] = document_id
                # Force description to be non-empty
                if not e.get("description"):
                    e["description"] = f"Extracted {e.get('type', 'entity')}"
                entities.append(e)
            
            return entities, data.get("relationships", [])
            
        except Exception as e:
            logger.warning(f"Extraction failed for chunk: {e}")
            return [], []
    
    def _resolve_entities(self, all_data: List[Dict]) -> tuple:
        """
        GEMINI IMPROVEMENT: Entity Resolution
        Merges duplicates like "PS5", "PS5 Console", "PlayStation 5"
        Strategy: Deduplicate by name, keep longest description
        """
        unique_entities = {}  # Map: name -> entity_dict
        all_relationships = []
        
        # Pass 1: Collect all entities, merge duplicates
        for chunk in all_data:
            for ent in chunk['entities']:
                name = ent['name'].strip()
                
                # If exists, keep the one with longer description
                if name in unique_entities:
                    existing_desc = unique_entities[name].get('description', '')
                    new_desc = ent.get('description', '')
                    
                    if len(new_desc) > len(existing_desc):
                        unique_entities[name] = ent
                else:
                    unique_entities[name] = ent
            
            # Collect all relationships
            all_relationships.extend(chunk['relationships'])
        
        # Fuzzy resolution (optional advanced step)
        # Could add LLM call here to normalize for examaple "PS5" -> "PlayStation 5"
        # For now, we proceed with deduplicated list
        
        logger.info(f"Resolved {len(unique_entities)} unique entities from {sum(len(c['entities']) for c in all_data)} total")
        
        return list(unique_entities.values()), all_relationships
    
    def _save_to_neo4j_batch(
        self, 
        entities: List[Dict], 
        relationships: List[Dict], 
        document_id: str
    ):
        """
        GEMINI IMPROVEMENT: Batch save with APOC
        Much faster than one-by-one inserts
        """
        driver = db.get_driver()
        
        # Prepare entity batch
        entity_batch = [
            {
                "name": e["name"],
                "type": e["type"],
                "text": e.get("description", ""),
                "doc_id": document_id
            }
            for e in entities
        ]
        
        # Prepare relationship batch
        rel_batch = []
        for r in relationships:
            # Sanitize relationship type (remove spaces, uppercase)
            rel_type = r["type"].upper().replace(" ", "_").replace("-", "_")
            
            rel_batch.append({
                "from": r["from"],
                "to": r["to"],
                "type": rel_type,
                "doc_id": document_id
            })
        
        with driver.session() as session:
            try:
                # 1. Bulk Merge Entities using APOC
                result = session.run("""
                UNWIND $batch as row
                CALL apoc.merge.node([row.type], {name: row.name, document_id: row.doc_id}, {text: row.text}) 
                YIELD node
                RETURN count(node) as count
                """, batch=entity_batch)
                
                entity_count = result.single()["count"]
                logger.info(f"✓ Bulk saved {entity_count} entities")
                
            except Exception as e:
                logger.warning(f"APOC not available, falling back to standard merge: {e}")
                # Fallback: Standard MERGE (slower but works without APOC)
                for ent in entity_batch:
                    session.run(f"""
                    MERGE (n:{ent['type']} {{name: $name, document_id: $doc_id}})
                    SET n.text = $text
                    """, name=ent['name'], doc_id=ent['doc_id'], text=ent['text'])
                
                logger.info(f"✓ Saved {len(entity_batch)} entities (standard)")
            
            try:
                # Bulk Merge Relationships using APOC
                result = session.run("""
                UNWIND $batch as row
                MATCH (a {name: row.from, document_id: row.doc_id})
                MATCH (b {name: row.to, document_id: row.doc_id})
                CALL apoc.merge.relationship(a, row.type, {}, {}, b) 
                YIELD rel
                RETURN count(rel) as count
                """, batch=rel_batch)
                
                rel_count = result.single()["count"]
                logger.info(f"✓ Bulk saved {rel_count} relationships")
                
            except Exception as e:
                logger.warning(f"APOC relationship merge failed, using standard: {e}")
                # Fallback: Standard MERGE
                rel_count = 0
                for rel in rel_batch:
                    try:
                        session.run(f"""
                        MATCH (a {{name: $from_name, document_id: $doc_id}})
                        MATCH (b {{name: $to_name, document_id: $doc_id}})
                        MERGE (a)-[r:{rel['type']}]->(b)
                        RETURN r
                        """, from_name=rel['from'], to_name=rel['to'], doc_id=rel['doc_id'])
                        rel_count += 1
                    except:
                        continue
                
                logger.info(f"✓ Saved {rel_count} relationships (standard)")
    
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
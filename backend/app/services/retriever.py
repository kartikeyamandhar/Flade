"""
PERFECT HYBRID RETRIEVER
- Gemini's Web Search (HTML backend, jitter, rewriting, thread pool)
- Our Advanced Graph Logic (proper Cypher, depth traversal, document isolation, confidence)
"""
import asyncio
import random
import logging
from typing import Dict, List, Any, Optional
from neo4j import Driver
from llama_index.llms.openai import OpenAI

from app.core.database import db
from app.core.config import settings

logger = logging.getLogger(__name__)


class SimpleAsyncRetriever:
    """
    PRODUCTION HYBRID:
    - FREE web search with Gemini's rate limit protection
    - ADVANCED graph traversal with our proven logic
    - Smart fallback chain: graph → graph overview → web
    """
    
    def __init__(self):
        self.driver: Optional[Driver] = None
        self.llm: Optional[OpenAI] = None
        logger.info("✓ SimpleAsyncRetriever initialized")
    
    def _ensure_connected(self):
        """Lazy initialization"""
        if self.driver is None:
            self.driver = db.get_driver()
            self.llm = db.get_llm()
            logger.info("✓ Database connections established")
    
    async def aquery(
        self,
        question: str,
        document_id: str,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """Main query orchestrator"""
        
        self._ensure_connected()
        logger.info(f"Query: {question[:50]}...")
        
        # Get document context for web search
        doc_name = await self._get_document_name(document_id)
        
        # Classify intent
        intent = await self._classify_intent(question)
        logger.info(f"Intent: {intent}")
        
        # Route to appropriate method
        if intent == "external":
            result = await self._web_fallback(question, doc_name)
        elif intent == "analytical":
            result = await self._analytical_query(question, document_id, doc_name)
        elif intent in ["procedural", "troubleshooting"]:
            result = await self._graph_first_query(question, document_id, intent, doc_name)
        else:  # conceptual
            result = await self._standard_query(question, document_id, intent, doc_name)
        
        # Add metadata
        result["intent"] = intent
        if not include_context:
            result.pop("context", None)
        
        return result
    
    # ========== GEMINI'S WEB SEARCH (GOLD!) ==========
    
    async def _get_document_name(self, document_id: str) -> str:
        """Extract product name from graph"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (n)
                WHERE n.document_id = $doc_id
                AND labels(n)[0] = 'EQUIPMENT'
                RETURN n.name as name
                LIMIT 1
                """, doc_id=document_id)
                
                record = result.single()
                if record and record["name"]:
                    return record["name"]
                
                return "Product Manual"
        except:
            return "Product Manual"
    
    async def _rewrite_query_for_web(self, question: str, context_name: str) -> str:
        """Gemini's query rewriting"""
        
        prompt = f"""Rewrite this user question into a specific search query.

User Question: "{question}"
Product/Document: "{context_name}"

Rules:
1. If question mentions specific product (PS5, iPhone, etc), USE IT
2. If question uses "it", "this", "the device", replace with product name
3. Keep it short (max 8 words)
4. Make it search-engine friendly
5. Output ONLY the rewritten query

Rewritten Query:"""
        
        try:
            response = await self.llm.acomplete(prompt)
            rewritten = response.text.strip().strip('"')
            logger.info(f"🔄 Rewrote: '{question}' → '{rewritten}'")
            return rewritten
        except:
            return f"{question} {context_name}"
    
    async def _perform_free_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Gemini's FREE web search:
        - HTML backend (bypasses rate limits)
        - Random jitter (prevents hammering)
        - Thread pool execution (async-friendly)
        """
        
        # Add random delay (Gemini's trick!)
        delay = random.uniform(2.0, 4.0)
        await asyncio.sleep(delay)
        
        def search_sync():
            try:
                from duckduckgo_search import DDGS
                
                # backend='html' is Gemini's secret sauce!
                results = DDGS().text(
                    query,
                    max_results=max_results,
                    backend="html"  # ← Gemini's fix!
                )
                return list(results)
            except Exception as e:
                logger.error(f"Web search failed: {e}")
                return []
        
        # Run in thread pool (Gemini's async pattern)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, search_sync)
    
    async def _web_search_enhancement(self, question: str, doc_name: str, partial_answer: str = "") -> str:
        """Enhance incomplete manual answer with web search"""
        
        search_query = await self._rewrite_query_for_web(question, doc_name)
        logger.info(f"🌐 Enhancing with web: {search_query}")
        
        results = await self._perform_free_search(search_query, max_results=2)
        
        if not results:
            return partial_answer or "I couldn't find additional information."
        
        # Build enhanced answer
        enhanced = ""
        if partial_answer:
            enhanced = f"**From your manual:**\n{partial_answer}\n\n"
            enhanced += "**📚 Additional information from web:**\n\n"
        else:
            enhanced = "**📚 Information from web sources:**\n\n"
        
        for r in results:
            title = r.get('title', 'Web Result')[:80]
            snippet = r.get('body', '')[:200]
            link = r.get('href', '#')
            
            enhanced += f"- **{title}**: {snippet}... [Link]({link})\n"
        
        enhanced += "\n💡 *Combined manual + web sources*"
        
        return enhanced
    
    async def _web_fallback(self, question: str, doc_name: str) -> Dict:
        """Pure web search for external questions"""
        
        search_query = await self._rewrite_query_for_web(question, doc_name)
        logger.info(f"🌐 Web search: {search_query}")
        
        results = await self._perform_free_search(search_query, max_results=4)
        
        if not results:
            return {
                "answer": "💡 This information isn't in the manual and web search is unavailable.",
                "sources": [],
                "retrieval_method": "web_fallback",
                "confidence": 0.0
            }
        
        # Synthesize answer from web results
        context_text = "\n\n".join([
            f"**{r.get('title', 'Source')}**\n{r.get('body', '')}"
            for r in results
        ])
        
        prompt = f"""Based on these web search results, answer the question concisely.

Question: {question}

Web Results:
{context_text}

Answer:"""
        
        try:
            ans_response = await self.llm.acomplete(prompt)
            answer = ans_response.text.strip()
        except:
            answer = "Web search returned results but synthesis failed."
        
        formatted_sources = [
            {"type": "web", "title": r.get('title'), "url": r.get('href')}
            for r in results
        ]
        
        return {
            "answer": f"🌐 **Web Search Result:**\n\n{answer}",
            "sources": formatted_sources,
            "retrieval_method": "web_search",
            "confidence": 0.7
        }
    
    # ========== OUR ADVANCED GRAPH LOGIC (PROVEN!) ==========
    
    async def _classify_intent(self, question: str) -> str:
        """Our original intent classification"""
        
        prompt = f"""Classify this question into ONE category:

1. "procedural" - How-to, steps, installation
2. "conceptual" - What-is, features, specifications  
3. "troubleshooting" - Problems, errors, fixes
4. "analytical" - Counting, listing with "how many", "count"
5. "external" - Price, availability, where to buy

Question: "{question}"

Rules:
- "What X are included/available?" → conceptual (items in manual)
- "Where to buy" or "current price" → external
- "How to" or "steps" → procedural
- "How many" or "count" → analytical

ONE WORD:"""
        
        try:
            response = await self.llm.acomplete(prompt)
            intent = response.text.strip().lower()
            
            valid = ["procedural", "conceptual", "troubleshooting", "analytical", "external"]
            return intent if intent in valid else "conceptual"
        except:
            return "conceptual"
    
    def _extract_keywords(self, question: str, intent: str) -> List[str]:
        """Our keyword extraction"""
        
        import nltk
        from nltk.corpus import stopwords
        
        try:
            stop_words = set(stopwords.words('english'))
        except:
            nltk.download('stopwords', quiet=True)
            stop_words = set(stopwords.words('english'))
        
        stop_words.update(['what', 'how', 'when', 'where', 'why', 'who', 'which', 'do', 'does', 'is', 'are'])
        
        words = question.lower().split()
        keywords = [w.strip('?.,!') for w in words if w.lower() not in stop_words and len(w) > 2]
        
        logger.info(f"Keywords: {keywords}")
        return keywords
    
    def _search_neo4j(
        self,
        keywords: List[str],
        document_id: str,
        depth: int = 2,
        limit: int = 6
    ) -> List[Dict]:
        """
        OUR ADVANCED Neo4j search with:
        - Proper depth traversal (depth=2 vs depth=3)
        - Relationship extraction
        - Overview fallback
        - Document isolation
        """
        
        try:
            flexible_keywords = [kw for kw in keywords if len(kw) > 2]
            
            if not flexible_keywords:
                flexible_keywords = ['overview', 'guide', 'manual']
            
            with self.driver.session() as session:
                if depth == 3:
                    # DEEP traversal for procedural
                    query = f"""
                    MATCH (n)
                    WHERE n.document_id = $doc_id
                    AND any(kw IN $keywords WHERE toLower(n.name) CONTAINS toLower(kw))
                    WITH n LIMIT {limit}
                    OPTIONAL MATCH (n)-[r1]->(m1)
                    WHERE m1.document_id = $doc_id
                    OPTIONAL MATCH (m1)-[r2]->(m2)
                    WHERE m2.document_id = $doc_id
                    WITH n,
                         collect(DISTINCT {{rel: type(r1), target: m1.name}}) +
                         collect(DISTINCT {{rel: type(r2), target: m2.name}}) as all_connections
                    RETURN n.name as name,
                           labels(n)[0] as type,
                           all_connections as connections,
                           n.name as _sort
                    ORDER BY _sort
                    """
                else:
                    # STANDARD single-hop
                    query = f"""
                    MATCH (n)
                    WHERE n.document_id = $doc_id
                    AND any(kw IN $keywords WHERE toLower(n.name) CONTAINS toLower(kw))
                    WITH n LIMIT {limit}
                    OPTIONAL MATCH (n)-[r]->(m)
                    WHERE m.document_id = $doc_id
                    RETURN n.name as name,
                           labels(n)[0] as type,
                           collect({{rel: type(r), target: m.name}}) as connections,
                           n.name as _sort
                    ORDER BY _sort
                    """
                
                result = session.run(query, doc_id=document_id, keywords=flexible_keywords)
                nodes = [dict(record) for record in result]
                
                if nodes:
                    logger.info(f"Found: {len(nodes)} nodes")
                    return nodes
                
                # CRITICAL: Fallback to overview (Gemini's code was missing this!)
                logger.info("Keyword search failed → Getting overview")
                
                fallback_query = f"""
                MATCH (n)
                WHERE n.document_id = $doc_id
                OPTIONAL MATCH (n)-[r]->()
                WITH n, count(r) as connections
                ORDER BY connections DESC
                LIMIT {limit + 4}
                RETURN n.name as name,
                       labels(n)[0] as type,
                       [] as connections
                """
                
                result = session.run(fallback_query, doc_id=document_id)
                nodes = [dict(record) for record in result]
                
                logger.info(f"Found: {len(nodes)} nodes (overview)")
                return nodes
                
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            return []
    
    def _calculate_confidence(self, nodes: List[Dict]) -> float:
        """Our top-3 confidence calculation"""
        
        if not nodes:
            return 0.0
        
        scores = [n.get("score", 0.5) for n in nodes]
        top_scores = sorted(scores, reverse=True)[:3]
        avg_top = sum(top_scores) / len(top_scores)
        coverage = min(len(nodes) / 6.0, 1.0)
        confidence = round(avg_top * 0.7 + coverage * 0.3, 2)
        
        return confidence
    
    def _is_insufficient(self, answer: str) -> bool:
        """Check if answer needs web enhancement"""
        
        if not answer or len(answer) < 15:
            return True
        
        incomplete_phrases = [
            "does not include",
            "does not specify",
            "does not provide",
            "not mentioned",
            "not available",
            "please refer to",
            "context does not"
        ]
        
        return any(p in answer.lower() for p in incomplete_phrases)
    
    async def _synthesize(self, question: str, nodes: List[Dict], intent: str) -> str:
        """Our detailed synthesis"""
        
        if not nodes:
            return "I couldn't find relevant information in the manual."
        
        # Build context
        context = "Relevant information:\n\n"
        for i, node in enumerate(nodes[:5], 1):
            context += f"{i}. {node['name']} ({node['type']})\n"
            if node.get('connections'):
                rels = node['connections'][:3]
                connections = ', '.join([f"{r['rel']} → {r['target']}" for r in rels if r.get('rel')])
                if connections:
                    context += f"   Connected to: {connections}\n"
            context += "\n"
        
        # Synthesis prompt
        prompt = f"""Based on this information from a technical manual, answer the question.

{context}

Question: {question}

Instructions:
- Provide a clear, concise answer
- If information is incomplete, acknowledge it explicitly
- Mention which components/items are relevant

Answer:"""
        
        try:
            response = await self.llm.acomplete(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return "Error generating answer."
    
    async def _standard_query(self, question: str, document_id: str, intent: str, doc_name: str) -> Dict:
        """Standard retrieval with web enhancement"""
        
        keywords = self._extract_keywords(question, intent)
        nodes = self._search_neo4j(keywords, document_id, depth=2, limit=6)
        
        # CRITICAL: Only fallback to web if NO nodes found
        if not nodes:
            logger.warning("No nodes found in graph → Web fallback")
            return await self._web_fallback(question, doc_name)
        
        confidence = self._calculate_confidence(nodes)
        answer = await self._synthesize(question, nodes, intent)
        
        # Check if incomplete and enhance
        if self._is_insufficient(answer):
            logger.info("📚 Answer incomplete, enhancing with web...")
            answer = await self._web_search_enhancement(question, doc_name, answer)
            confidence = min(confidence + 0.2, 0.9)
        
        return {
            "answer": answer,
            "sources": [{"name": n['name'], "type": n['type']} for n in nodes[:5]],
            "retrieval_method": "standard",
            "confidence": confidence,
            "context": nodes
        }
    
    async def _graph_first_query(self, question: str, document_id: str, intent: str, doc_name: str) -> Dict:
        """Graph-first with deeper traversal"""
        
        keywords = self._extract_keywords(question, intent)
        nodes = self._search_neo4j(keywords, document_id, depth=3, limit=6)
        
        # CRITICAL: Only fallback to web if NO nodes found
        if not nodes:
            logger.warning("No nodes found in graph → Web fallback")
            return await self._web_fallback(question, doc_name)
        
        confidence = min(self._calculate_confidence(nodes) * 1.1, 1.0)
        answer = await self._synthesize(question, nodes, intent)
        
        # Check if incomplete and enhance
        if self._is_insufficient(answer):
            logger.info("📚 Procedural answer incomplete, enhancing...")
            answer = await self._web_search_enhancement(question, doc_name, answer)
            confidence = min(confidence + 0.2, 0.9)
        
        return {
            "answer": answer,
            "sources": [{"name": n['name'], "type": n['type']} for n in nodes[:5]],
            "retrieval_method": "graph_first",
            "confidence": confidence,
            "context": nodes
        }
    
    async def _analytical_query(self, question: str, document_id: str, doc_name: str) -> Dict:
        """Analytical with Cypher"""
        
        logger.info("Intent: analytical")
        
        cypher = await self._generate_safe_cypher(question, document_id)
        
        if not cypher:
            logger.warning("Cypher generation failed → Standard query")
            return await self._standard_query(question, document_id, "conceptual", doc_name)
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher)
                records = [dict(record) for record in result]
            
            if not records:
                logger.warning("No Cypher results → Standard query")
                return await self._standard_query(question, document_id, "conceptual", doc_name)
            
            # Format results
            answer = "**Results:**\n\n"
            for i, record in enumerate(records[:20], 1):
                items = [f"{k}: {v}" for k, v in record.items()]
                answer += f"{i}. {', '.join(items)}\n"
            
            logger.info("✓ Success via analytical")
            
            return {
                "answer": answer,
                "sources": [{"name": "Unknown", "type": "Unknown"}],
                "retrieval_method": "analytical",
                "confidence": 0.8,
                "cypher_query": cypher
            }
            
        except Exception as e:
            logger.error(f"Cypher execution failed: {e}")
            return await self._standard_query(question, document_id, "conceptual", doc_name)
    
    async def _generate_safe_cypher(self, question: str, document_id: str) -> Optional[str]:
        """Generate document-safe Cypher"""
        
        schema = await self._get_schema(document_id)
        
        prompt = f"""Generate a Neo4j Cypher query to answer this question.

Schema:
{schema}

Question: {question}

CRITICAL RULES:
1. EVERY query MUST include: WHERE n.document_id = "{document_id}"
2. Use simple MATCH, WHERE, RETURN statements
3. Return ONLY the Cypher query (no explanations, no markdown)
4. Limit results to 20

Examples:
Q: "How many components are there?"
A: MATCH (n:COMPONENT) WHERE n.document_id = "{document_id}" RETURN count(n) as count

Q: "List all tools"
A: MATCH (n:TOOL) WHERE n.document_id = "{document_id}" RETURN n.name LIMIT 20

Now generate Cypher for: {question}

Cypher:"""
        
        try:
            response = await self.llm.acomplete(prompt)
            cypher = response.text.strip()
            cypher = cypher.replace("```cypher", "").replace("```", "").strip()
            
            # Verify document_id is in query
            if document_id not in cypher:
                logger.warning("LLM didn't include document_id, creating fallback")
                if "how many" in question.lower() or "count" in question.lower():
                    cypher = f'MATCH (n) WHERE n.document_id = "{document_id}" RETURN count(n) as total_count'
                else:
                    cypher = f'MATCH (n) WHERE n.document_id = "{document_id}" RETURN n.name, labels(n)[0] as type LIMIT 20'
            
            return cypher
            
        except Exception as e:
            logger.error(f"Cypher generation failed: {e}")
            return None
    
    async def _get_schema(self, document_id: str) -> str:
        """Get graph schema"""
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (n)
                WHERE n.document_id = $doc_id
                RETURN DISTINCT labels(n)[0] as label
                LIMIT 20
                """, doc_id=document_id)
                
                labels = [r['label'] for r in result if r['label']]
                
                result = session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) as rel_type
                LIMIT 20
                """)
                
                rel_types = [r['rel_type'] for r in result if r['rel_type']]
                
                schema = f"Node Labels: {', '.join(labels)}\n"
                schema += f"Relationship Types: {', '.join(rel_types)}"
                
                return schema
                
        except Exception as e:
            logger.error(f"Schema retrieval failed: {e}")
            return "Schema unavailable"
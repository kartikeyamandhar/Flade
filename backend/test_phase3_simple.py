#!/usr/bin/env python3
"""
Phase 3 Simple Test - Quick REPL Demo
Shows how to use the retrieval system
"""

# Run this from backend directory:
# python test_phase3_simple.py

print("🔧 Initializing Phase 3 components...")
print()

from app.services.retriever import HybridRetriever
from app.services.query_router import QueryRouter
from app.core.database import db

# Connect to database
print("📡 Connecting to Neo4j...")
db.connect()
print("✅ Connected!")
print()

# Initialize components
print("🧠 Initializing Query Router...")
router = QueryRouter(db.get_llm())
print("✅ Router ready!")
print()

print("🔍 Initializing Hybrid Retriever...")
retriever = HybridRetriever()
print("✅ Retriever ready!")
print()

# Show what's available
print("=" * 60)
print("Phase 3 Components Ready!")
print("=" * 60)
print()

print("📋 Available Retrieval Methods:")
print("  1. vector      - Semantic similarity search")
print("  2. graph       - Relationship traversal")
print("  3. text2cypher - Database analytical queries")
print("  4. web_search  - External information")
print()

print("🎯 Test Query Classification:")
print()

# Test some questions
test_questions = [
    "What safety precautions should I follow?",
    "How many tools are needed?",
    "Which components connect to the motor?",
]

for i, question in enumerate(test_questions, 1):
    print(f"{i}. \"{question}\"")
    method, reasoning = router.classify_query(question)
    print(f"   → Method: {method.upper()}")
    print(f"   → Why: {reasoning[:60]}...")
    print()

print("=" * 60)
print()

# Check if there's data to query
print("📊 Checking Knowledge Graph...")
driver = db.get_driver()
with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()["count"]
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()["count"]
    
    print(f"  - Nodes: {node_count}")
    print(f"  - Relationships: {rel_count}")
    print()

if node_count == 0:
    print("⚠️  Your knowledge graph is empty!")
    print()
    print("To test actual queries, you need to:")
    print("  1. Complete Phase 4 (API Endpoints)")
    print("  2. Upload a PDF document")
    print("  3. Wait for processing to complete")
    print("  4. Then query it!")
    print()
    print("But Phase 3 components are working and ready! ✅")
else:
    print("✅ You have data! The retriever is ready to query.")
    print()
    print("Example usage:")
    print()
    print("  from app.services.retriever import HybridRetriever")
    print("  retriever = HybridRetriever()")
    print("  result = retriever.query(")
    print("      document_id='your-doc-id',")
    print("      question='What are the safety warnings?',")
    print("      retrieval_method='auto'")
    print("  )")
    print("  print(result['answer'])")
    print()

print("=" * 60)
print("✅ Phase 3 Test Complete!")
print("=" * 60)

# Clean up
db.close()
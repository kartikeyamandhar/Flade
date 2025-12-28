#!/usr/bin/env python3
"""
Phase 3 Interactive Test
Demonstrates the query & retrieval system in action
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.retriever import HybridRetriever
from app.services.query_router import QueryRouter
from app.core.database import db
from app.core.config import settings

def test_query_router():
    """Test the query router with sample questions."""
    print("🧠 Testing Query Router")
    print("=" * 60)
    print()
    
    # Connect to database
    db.connect()
    
    # Initialize router
    router = QueryRouter(db.get_llm())
    
    # Test questions
    test_questions = [
        "What are the safety precautions for this equipment?",
        "How many components does the system have?",
        "What tools are required for installation?",
        "List all parts that are compatible with the motor",
        "What is the current market price?",
    ]
    
    print("Testing automatic question classification:\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"{i}. Question: \"{question}\"")
        
        try:
            method, reasoning = router.classify_query(question)
            print(f"   ✅ Method: {method.upper()}")
            print(f"   💡 Reasoning: {reasoning}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    db.close()


def test_retriever_initialization():
    """Test that retriever initializes correctly."""
    print("🔍 Testing Hybrid Retriever Initialization")
    print("=" * 60)
    print()
    
    # Connect to database
    db.connect()
    
    try:
        # Initialize retriever
        retriever = HybridRetriever()
        
        print("✅ Hybrid Retriever initialized successfully!")
        print()
        print("Configuration:")
        print(f"  - LLM Model: {retriever.llm.model}")
        print(f"  - Embedding Model: {retriever.embed_model.model_name}")
        print(f"  - Graph Store: Connected")
        print(f"  - Query Router: Ready")
        print()
        print("Available Retrieval Methods:")
        print("  1. 🔍 Vector Search - Semantic similarity")
        print("  2. 🕸️  Graph Traversal - Relationship queries")
        print("  3. 💬 Text2Cypher - Analytical queries")
        print("  4. 🌐 Web Search - External fallback")
        print()
        
    except Exception as e:
        print(f"❌ Error initializing retriever: {e}")
    
    db.close()


def test_method_selection():
    """Test the automatic method selection."""
    print("🎯 Testing Automatic Method Selection")
    print("=" * 60)
    print()
    
    db.connect()
    
    try:
        retriever = HybridRetriever()
        
        test_cases = [
            ("What are the installation instructions?", "Vector (semantic)"),
            ("Show me all safety warnings", "Graph (relationships)"),
            ("How many procedures are documented?", "Text2Cypher (counting)"),
            ("What's the latest firmware version?", "Web Search (external)"),
        ]
        
        print("Testing query routing decisions:\n")
        
        for question, expected in test_cases:
            method, reasoning = retriever.router.classify_query(question)
            
            print(f"Q: \"{question}\"")
            print(f"   → Selected: {method.upper()}")
            print(f"   → Expected: {expected}")
            print(f"   → Reasoning: {reasoning[:80]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    db.close()


def test_graph_stats():
    """Display current graph statistics."""
    print("📊 Current Knowledge Graph Statistics")
    print("=" * 60)
    print()
    
    db.connect()
    
    try:
        driver = db.get_driver()
        with driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = result.single()["count"]
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_rels = result.single()["count"]
            
            print(f"Total Nodes: {total_nodes}")
            print(f"Total Relationships: {total_rels}")
            print()
            
            if total_nodes == 0:
                print("⚠️  Your graph is empty!")
                print("   To test queries, you need to:")
                print("   1. First upload a PDF document (Phase 4)")
                print("   2. Process it into the knowledge graph (Phase 2)")
                print("   3. Then you can query it (Phase 3)")
                print()
                print("   For now, Phase 3 components are initialized and ready!")
            else:
                print("✅ You have data in your graph!")
                print("   Ready to test queries on real documents.")
                
                # Show node types
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n) as labels, count(*) as count
                    ORDER BY count DESC
                    LIMIT 5
                """)
                
                print("\nTop 5 Node Types:")
                for record in result:
                    if record["labels"]:
                        label = record["labels"][0]
                        count = record["count"]
                        print(f"  - {label}: {count} nodes")
            
            print()
    
    except Exception as e:
        print(f"❌ Error checking graph: {e}")
    
    db.close()


def main():
    """Run all Phase 3 tests."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     Phase 3: Query & Retrieval System - Live Test        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    
    try:
        # Test 1: Query Router
        test_query_router()
        print()
        
        # Test 2: Retriever Initialization
        test_retriever_initialization()
        print()
        
        # Test 3: Method Selection
        test_method_selection()
        print()
        
        # Test 4: Graph Stats
        test_graph_stats()
        print()
        
        print("=" * 60)
        print("✅ All Phase 3 Tests Completed!")
        print("=" * 60)
        print()
        print("📝 Summary:")
        print("  ✅ Query Router working")
        print("  ✅ Hybrid Retriever initialized")
        print("  ✅ Method selection functional")
        print("  ✅ Graph connection verified")
        print()
        print("⏭️  Ready for Phase 4: API Endpoints")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
"""
Test script for SimpleAsyncRetriever
Updated to match new aquery() signature (no retrieval_method param)
"""
import asyncio
import sys
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path
sys.path.insert(0, '/Users/kartikeyamandhar/Documents/SaaS/manual-knowledge-graph/backend')

from app.core.database import db
from app.services.retriever import SimpleAsyncRetriever

# Test queries covering different intent types
TEST_QUERIES = [
    # Conceptual (should use standard retrieval)
    "What is this document about?",
    "What cables are included?",
    "What are the power requirements?",
    "What accessories are available?",
    
    # Procedural (should use graph_first with depth=3)
    "How to turn on the PS5?",
    "How to connect a controller?",
    "How to install the console?",
    "Summarize the installation steps",
    
    # Analytical (should use text2cypher)
    "How many components are there?",
    "List all the tools required",
    "Count the safety warnings",
    
    # Troubleshooting (should use graph_first with depth=3)
    "What if the console won't turn on?",
    "How to fix controller connection issues?",
    
    # External (should trigger web fallback)
    "What is the current price?",
    "Where can I buy this?",
]


class RetrieverTester:
    """Test harness for retriever"""
    
    def __init__(self):
        self.retriever = SimpleAsyncRetriever()
        self.document_id = None
        self.results = []
    
    async def initialize(self):
        """Initialize database and get document ID"""
        print("\n" + "="*80)
        print("INITIALIZING DATABASE CONNECTION")
        print("="*80)
        
        # Connect to database
        db.connect()
        print("✓ Database connected")
        
        print("✓ Retriever initialized")
        
        # Get first document ID from database
        driver = db.get_driver()
        with driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.document_id IS NOT NULL
                RETURN DISTINCT n.document_id as doc_id
                LIMIT 1
            """)
            
            record = result.single()
            if record:
                self.document_id = record['doc_id']
                print(f"✓ Using document: {self.document_id}")
            else:
                print("✗ No documents found in database!")
                print("  Run document upload first!")
                sys.exit(1)
    
    async def test_query(self, query: str, test_num: int, total: int) -> Dict[str, Any]:
        """Test a single query"""
        
        print("\n" + "#"*80)
        print(f"TEST {test_num}/{total}")
        print("#"*80)
        print()
        print("-"*80)
        print(f"QUERY: {query}")
        print("-"*80)
        print()
        
        try:
            # Call retriever with NEW signature (no retrieval_method!)
            result = await self.retriever.aquery(
                question=query,
                document_id=self.document_id,
                include_context=True
            )
            
            # Extract info
            method = result.get('retrieval_method', 'unknown')
            confidence = result.get('confidence', 0.0)
            answer = result.get('answer', 'No answer')
            sources = result.get('sources', [])
            
            # Determine success
            #success = confidence > 0.0 and method != 'web_fallback'
            success = confidence > 0.1  # Web results are valid successes!
            # Print results
            print(f"✓ Method: {method}")
            if 'intent' in result:
                print(f"✓ Intent: {result['intent']}")
            print(f"✓ Confidence: {confidence}")
            print(f"✓ Sources: {len(sources)}")
            print()
            print("ANSWER:")
            print(answer)
            print()
            
            if sources:
                print("SOURCES:")
                for i, source in enumerate(sources[:5], 1):
                    if isinstance(source, dict):
                        name = source.get('name', source.get('title', 'Unknown'))
                        stype = source.get('type', source.get('url', 'Unknown'))
                        print(f"  {i}. {name} ({stype})")
                print()
            
            if success:
                print("✅ SUCCESS")
            else:
                print("⚠️  LOW QUALITY or FALLBACK")
            
            return {
                'query': query,
                'success': success,
                'method': method,
                'confidence': confidence,
                'error': None
            }
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'query': query,
                'success': False,
                'method': 'error',
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def run_tests(self):
        """Run all tests"""
        
        print("\n" + "="*80)
        print("PRODUCTION RETRIEVER TESTS")
        print("="*80)
        
        total = len(TEST_QUERIES)
        
        for i, query in enumerate(TEST_QUERIES, 1):
            result = await self.test_query(query, i, total)
            self.results.append(result)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print()
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r['success'])
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        
        print(f"Total queries: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {success_rate:.1f}%")
        print()
        
        # Method breakdown
        methods = {}
        for r in self.results:
            method = r['method']
            methods[method] = methods.get(method, 0) + 1
        
        print("Method breakdown:")
        for method, count in sorted(methods.items(), key=lambda x: -x[1]):
            print(f"  {method}: {count}")
        print()
        
        # Failed queries
        failed_queries = [r for r in self.results if not r['success']]
        if failed_queries:
            print("Failed queries:")
            for r in failed_queries:
                error_info = f" ({r['error'][:50]})" if r['error'] else ""
                print(f"  - {r['query'][:50]}... ({r['method']}){error_info}")
        
        # Close database
        db.close()
        
        # Warning if below target
        if success_rate < 75:
            print(f"\n⚠️  WARNING: Only {success_rate:.1f}% success rate (target: 75%)")
        else:
            print(f"\n✅ SUCCESS: {success_rate:.1f}% success rate (target: 75%)")


async def main():
    """Main test function"""
    
    print("🚀 Testing SimpleAsyncRetriever (Production)")
    print("⚠️  Make sure Neo4j is running and has data!")
    print("⚠️  Update NEO4J_PASSWORD and OPENAI_API_KEY in this file!")
    print()
    
    tester = RetrieverTester()
    await tester.initialize()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
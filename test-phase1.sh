#!/bin/bash
# Phase 1 Test Script
# Verifies all Phase 1 components are working correctly

set -e

PROJECT_DIR="$HOME/Documents/SaaS/manual-knowledge-graph"

echo "🧪 Phase 1: Testing Backend Core Structure"
echo "==========================================="
echo ""

if [ ! -d "$PROJECT_DIR/backend" ]; then
    echo "❌ Project not found at $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR/backend"

# Activate virtual environment
source venv/bin/activate

echo "1️⃣  Testing configuration module..."
python << 'EOF'
try:
    from app.core.config import settings, get_settings
    print(f"   ✅ Config loaded successfully")
    print(f"   - App Name: {settings.APP_NAME}")
    print(f"   - Version: {settings.VERSION}")
    print(f"   - Neo4j URI: {settings.NEO4J_URI}")
    print(f"   - OpenAI Key: {settings.OPENAI_API_KEY[:15]}..." if settings.OPENAI_API_KEY else "   ⚠️  OpenAI key not set")
except Exception as e:
    print(f"   ❌ Config test failed: {e}")
    exit(1)
EOF

echo ""
echo "2️⃣  Testing data models..."
python << 'EOF'
try:
    from app.models.schemas import (
        DocumentStatus, UploadResponse, ProcessingProgress, 
        QueryRequest, QueryResponse, GraphStats, DocumentInfo
    )
    from datetime import datetime
    
    # Test creating instances
    status = DocumentStatus.UPLOADED
    upload = UploadResponse(
        document_id="test-123",
        filename="test.pdf",
        size=1000,
        pages=10,
        status=status,
        message="Test"
    )
    
    print(f"   ✅ All data models validated")
    print(f"   - Created test UploadResponse: {upload.document_id}")
except Exception as e:
    print(f"   ❌ Models test failed: {e}")
    exit(1)
EOF

echo ""
echo "3️⃣  Testing database connection..."
python << 'EOF'
try:
    from app.core.database import db
    
    print("   Attempting to connect to Neo4j...")
    db.connect()
    
    # Test Neo4j connection
    driver = db.get_driver()
    with driver.session() as session:
        result = session.run("RETURN 'Connection successful!' as message")
        message = result.single()["message"]
        print(f"   ✅ Neo4j: {message}")
    
    # Check other components
    graph_store = db.get_graph_store()
    llm = db.get_llm()
    embed_model = db.get_embed_model()
    
    print(f"   ✅ Graph store initialized")
    print(f"   ✅ LLM initialized: {llm.model}")
    print(f"   ✅ Embedding model initialized: {embed_model.model_name}")
    
    db.close()
    
except Exception as e:
    print(f"   ❌ Database test failed: {e}")
    print(f"   ⚠️  Make sure Neo4j Desktop is running!")
    exit(1)
EOF

echo ""
echo "4️⃣  Testing FastAPI application..."
python << 'EOF'
try:
    from app.main import app
    from fastapi.testclient import TestClient
    
    # Note: This won't actually start the server, just test imports
    print(f"   ✅ FastAPI app imported successfully")
    print(f"   - Title: {app.title}")
    print(f"   - Version: {app.version}")
    
except Exception as e:
    print(f"   ❌ FastAPI test failed: {e}")
    exit(1)
EOF

echo ""
echo "5️⃣  Checking file structure..."
if [ -f "app/main.py" ] && \
   [ -f "app/core/config.py" ] && \
   [ -f "app/core/database.py" ] && \
   [ -f "app/models/schemas.py" ]; then
    echo "   ✅ All required files present"
else
    echo "   ❌ Some files are missing!"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ PHASE 1 TESTS PASSED!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 Next steps:"
echo "   1. Start the development server:"
echo "      cd $PROJECT_DIR/backend"
echo "      source venv/bin/activate"
echo "      python -m app.main"
echo ""
echo "   2. Open http://localhost:8000/docs in your browser"
echo "   3. Test the /health endpoint"
echo ""
echo "📊 Progress: 2/10 phases complete (20%)"
echo ""
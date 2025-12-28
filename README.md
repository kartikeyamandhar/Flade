# Flade - Knowledge Graph RAG System for Technical Manuals

No reason to call it Flade I just liked the name.

**What it does:** Converts instruction manuals into queryable knowledge graphs. Upload a PDF, ask questions in plain English.

**What makes it interesting:** This extracts actual entities (equipment, components, specs) and relationships (requires, compatible-with, part-of) into a Neo4j graph. Then uses hybrid retrieval - vector search for concepts, graph traversal for relationships, text-to-Cypher for analytics.

The system auto-classifies questions and picks the right retrieval method. Ask "What are the specs?" - uses vector search. Ask "List all components" - traverses the graph. Ask "How many warnings?" - generates Cypher.

**Smart Query Expansion + Web Fallback**

When you ask a question, the system:
- Generates multiple variations of your query
- Searches the graph with all variations
- Re-ranks results by relevance
- Falls back to web search if nothing in the manual matches

Example from logs:
```
Query: "What are the steps mentioned"
Variations generated: 
  - "Steps mentioned explanation"
  - "Procedure outlined details"
  - "Enumerated process instructions"
Re-ranked: 10 → 5 nodes (filtered for relevance)
```

This is why it can handle vague questions and still find relevant info.


**Tech Stack:** FastAPI + Neo4j + LlamaIndex + OpenAI (GPT-3.5 + embeddings)
---

## Why This Exists

Learning motivation: I wanted to understand how knowledge graphs actually work in production. Not just Neo4j CRUD operations, but the full pipeline - how do you populate a graph with meaningful entities and relationships? What's the best retrieval strategy for different question types?

The practical problem:

For example, if - 

I bought a PS5. Manual was 22 pages. Simple question: "What cables come with it?"
Spent 10 minutes scrolling through pages to find it buried in a spec table on page 3.

Then bought a Lenovo laptop. Wanted to know if I could upgrade the RAM. Manual was 45 pages. Found it eventually, but had to cross-reference three different sections.

The bigger use case:

Think about heavy machinery - Caterpillar excavators, industrial equipment, medical devices. Technicians in the field with 300-page service manuals trying to find:

"What's the torque spec for this bolt?"
"What tools do I need for this procedure?"
"What's the part number for this component?"

What if: Upload manual → Ask question → Get answer with page citation. 

That's useful. And building it taught me how graph databases, RAG systems, and LLM orchestration actually work together.

---

## The Interesting Parts

### 1. Custom Knowledge Graph Schema

This was the hardest part. Took 47 attempts.

**Failed Attempt #1:** "Extract important entities"
- Result: Extracted "the", "and", "page 5" as entities
- Got 847 nodes from a 20-page manual
- Complete garbage

**Failed Attempt #15:** Too many entity types (15 different types)
- LLM got confused
- Same thing classified multiple ways
- Processing took 8 minutes

**What Actually Worked (Attempt 47):**

entity types - not too many, not too few:

```python
EQUIPMENT    # Main products (PS5, Controller)
COMPONENT    # Parts (HDMI cable, power supply)
SPECIFICATION # Specs (4K 120Hz, 825GB SSD)
TOOL         # Required tools (screwdriver, wrench)
PROCEDURE    # Named tasks (Installation, Setup)
SAFETY_ITEM  # Warnings (High voltage, pinch hazard)
PART_NUMBER  # SKUs (CFI-1215A)
MATERIAL     # Consumables (thermal paste, cable ties)
```

8 relationship types - all specific and queryable:

```python
REQUIRES         # PS5 REQUIRES HDMI cable
HAS_SPEC         # PS5 HAS_SPEC 4K 120Hz
COMPATIBLE_WITH  # Controller COMPATIBLE_WITH PS5
PART_OF          # Fan PART_OF PS5
USES             # Installation USES Screwdriver
PRECEDES         # Setup PRECEDES Calibration
WARNING_FOR      # High Voltage WARNING_FOR Power Supply
IDENTIFIED_BY    # PS5 IDENTIFIED_BY CFI-1215A
```

**The breakthrough:** Adding examples to the extraction prompt.

Accuracy jumped by showing the LLM what good extraction looks like:

```python
prompt = f"""
Extract entities and relationships.

Example:
Text: "The PS5 requires an HDMI 2.1 cable"
Entities: Equipment: "PS5", Component: "HDMI 2.1 cable"
Relations: PS5 REQUIRES HDMI 2.1 cable

[2 more examples]

Now extract from: {actual_text}
"""
```

**Lesson learned:** Few-shot prompting >> vague instructions

### 2. Hybrid Retrieval Engine

Different questions need different approaches. The system classifies each question and routes to the best method:

**Vector Search** - For conceptual questions
```
Question: "What are the safety precautions?"
Method: Semantic search across chunks
Why: Looking for concept, not structure
```

**Graph Traversal** - For relationship questions
```
Question: "List all required components"
Method: Cypher query traversing REQUIRES edges
Why: Asking about relationships in the graph
```

**Text-to-Cypher** - For analytical questions
```
Question: "How many safety warnings are there?"
Method: Generate Cypher: MATCH (s:SAFETY_ITEM) RETURN count(s)
Why: Need to count/aggregate
```

**The routing logic:**

```python
def classify_query(question):
    classification = llm.complete(f"""
    Question: "{question}"
    
    Methods:
    1. vector - conceptual/semantic
    2. graph - relationships/listings  
    3. text2cypher - counting/analytics
    
    Pick ONE: method|reason
    """)
    
    method, reason = classification.split("|")
    return method.strip()
```

Terminal logs show the full retrieval process:

**Query: "What are the steps mentioned"**
```
2025-12-28 00:54:43,029 - app.services.retriever - INFO - Intent: procedural
2025-12-28 00:54:43,911 - app.services.retriever - INFO - Query variations: 
    ['What are the steps mentoned', 
     '"Steps mentioned explanation"', 
     '"Procedure outlined details"']
2025-12-28 00:54:44,791 - app.services.retriever - INFO - Re-ranked: 10 → 5 nodes
```

**Query: "hi" (irrelevant to manual)**
```
2025-12-28 00:54:21,686 - app.services.retriever - INFO - Query variations: 
    ['hi', '"Hello greetings messages"']
2025-12-28 00:54:22,258 - app.services.retriever - WARNING - Re-ranking: No relevant nodes found
2025-12-28 00:54:22,258 - app.services.retriever - WARNING - No nodes found after expansion → Web fallback
```

**What's happening:**

1. Classifies intent (procedural, conceptual, etc.)
2. Generates query variations for better matching
3. Searches graph with multiple variations
4. Re-ranks results for relevance
5. If nothing relevant → Falls back to web search

The system doesn't fail when it can't find something in the manual. It tries web search as a last resort.

### 3. Document Processing Pipeline

There's actual validation and structure extraction:

```
1. Type Validation (GPT-3.5) → Reject non-manuals
2. PDF Extraction (pdfplumber) → Get clean text
3. Semantic Chunking (800 chars, 200 overlap) → Context-aware splits
4. Entity Extraction (GPT-3.5 + custom schema) → Pull entities/relationships
5. Graph Construction (Neo4j) → Build knowledge graph
6. Vector Embeddings (OpenAI) → Enable semantic search
```

**The validation step saves money.** Upload a novel by mistake? Gets rejected before wasting API calls:

Terminal output when someone uploads a poem:
```
2025-12-28 00:54:58,757 - app.services.document_validator - INFO - 📄 Document 'The-Road-Not-Taken.pdf' classified as: narrative
2025-12-28 00:55:00,211 - app.services.document_service - WARNING - Document rejected: narrative
```

User sees:
```
Rejected: "Whoa there, literature lover! I see you've uploaded 'The-Road-Not-Taken.pdf' 
(detected as 'narrative'). This system is optimized for technical/instructional documentation...

This system thinks a metaphor is a type of industrial measuring device."
```

Saves processing costs. Adds personality. Users actually like it.

```python
sample = extract_first_2000_chars(pdf)

doc_type = llm.complete(f"""
Classify: {sample}

Types: manual, narrative, academic, business
One word.
""")

if doc_type != "manual":
    reject_with_funny_message(doc_type)
```

Rejection message for novels: "This system thinks a metaphor is a type of industrial measuring device."

Trying to add some personality.

### 4. The Async Problem (and How I Fixed It)

**The Issue:**

FastAPI runs async. LlamaIndex wants async. Background tasks need threads.

Initial code:

```python
async def process_document(file_path):
    result = await llama_index_stuff(file_path)
    
background_tasks.add_task(process_document, file_path)
```

Error: `RuntimeError: This event loop is already running`

**Why it broke:** Can't nest event loops. FastAPI already has one. LlamaIndex wants another.

**The Fix:**

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

executor = ThreadPoolExecutor(max_workers=3)

def process_sync(file_path):
    # Create NEW event loop in this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(actual_processing(file_path))
    finally:
        loop.close()

async def process_in_thread(file_path):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, process_sync, file_path)

# This works
background_tasks.add_task(process_in_thread, file_path)
```

Give each background task its own event loop in its own thread. Problem solved.

**Lesson:** To not fight async. Give it its own space.

### 5. Why pdfplumber > pypdf

Tried pypdf first:

```python
text = pypdf.pages[0].extract_text()
# Output: "Pla yS tat io n5 Us erMan ual"
```

Words split randomly. Tables became gibberish.

Switched to pdfplumber:

```python
with pdfplumber.open(pdf) as doc:
    text = doc.pages[0].extract_text()
# Output: "PlayStation 5 User Manual"
```

Accuracy increased. Worth the dependency.

Also gets tables:

```python
tables = page.extract_tables()  # Bonus
```

### 6. Source Attribution

Early version had no citations. 

Fixed by storing metadata with each chunk:

```python
chunk_metadata = {
    "document_id": doc_id,
    "page": page_num,
    "chunk_id": chunk_idx,
    "section": section_name
}
```

Now every answer includes:

```
Answer: "You need a Phillips screwdriver (M4)"
Source: Page 12, Section 3.2 - Installation Tools
```

---

## Architecture

```
User uploads PDF
    ↓
FastAPI receives → Background thread spawned
    ↓
Document Validator (GPT-3.5 or 4)
    ├─ Manual? → Continue
    └─ Other? → Reject
    ↓
Text Extractor (pdfplumber)
    ↓
Chunker (LlamaIndex SentenceSplitter)
    ↓
Entity Extractor (GPT + custom prompt)
    ↓
Graph Builder (Neo4j + LlamaIndex)
    ↓
Vector Indexer (OpenAI embeddings)
    ↓
Ready for queries

User asks question
    ↓
Query Router (GPT-3.5) → Picks retrieval method
    ↓
Hybrid Retriever
    ├─ Vector Search
    ├─ Graph Traversal
    └─ Text-to-Cypher
    ↓
Answer Generator (GPT-3.5)
    ↓
Response with citations
```

---

## Tech Stack

**Backend:**
- FastAPI - Async API framework
- Neo4j - Graph database (the star of the show)
- LlamaIndex - RAG orchestration
- OpenAI API - GPT-3.5-turbo + text-embedding-3-small

**Why these choices:**

**Neo4j over PostgreSQL?**
- Relationship queries in SQL are painful
- Cypher is built for graph traversal
- Built-in graph algorithms

**LlamaIndex over LangChain?**
- Simpler API for my use case
- Better Neo4j integration
- Documentation actually makes sense

---

## Quick Start

**Prerequisites:**
- Python 3.13+
- Neo4j Desktop or Aura
- OpenAI API key

**Setup:**

```bash
# Clone
git clone https://github.com/yourusername/flade.git
cd flade/backend

# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your:
# - OPENAI_API_KEY
# - NEO4J_PASSWORD

# Run Neo4j Desktop (or use Aura)
# Install APOC plugin

# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend (separate terminal)
cd ../frontend
npm install
npm start
```

Open http://localhost:3000

**Test it:**
1. Upload a small manual (10-20 pages)
2. Wait 2-3 minutes
3. Ask: "What is this manual about?"
4. Ask: "List all components"

---

## Problems I Hit (and Fixed)

### Problem 1: Entity Extraction Quality

**Initial approach:** Ask GPT to extract entities

**Result:** Extracted articles, prepositions, page numbers as entities

**Fix:** Custom schema with 8 specific entity types + 3 examples in prompt

### Problem 2: Async Event Loop Conflicts

**Issue:** FastAPI + LlamaIndex both want event loops

**Error:** `RuntimeError: This event loop is already running`

**Fix:** ThreadPoolExecutor + new event loop per thread

**Code:**
```python
def process_sync(file_path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(work(file_path))
    loop.close()
```

### Problem 3: Vague Relationship Types

**Initial schema:** Used "RELATED_TO" for everything

**Result:** Useless graph. Everything connected to everything.

**Fix:** 8 specific relationship types (REQUIRES, HAS_SPEC, USES, etc.)

**Outcome:** Meaningful queries possible

### Problem 4: PDF Extraction Quality

**pypdf output:** "Pla yS tat io n5"

**pdfplumber output:** "PlayStation 5"

**Fix:** Switched to pdfplumber

### Problem 5: Missing Citations

**Initial version:** Just returned answers

**Problem:** Users won't trust it

**Fix:** Store page/chunk metadata, extract sources

**Outcome:** Every answer now has "Source: Page X, Section Y"

---

## Example Queries

**Conceptual (Vector Search):**
```
Q: "What are the safety precautions?"
A: "Safety precautions include:
    • Disconnect power before servicing
    • Do not block ventilation openings
    • Keep away from water
    
    Source: Page 5, Safety Information"
```

**Structural (Graph Traversal):**
```
Q: "What components does the PS5 require?"
A: "Required components:
    • HDMI Cable (HDMI 2.1)
    • AC Power Cable
    • USB-C Cable (for controller)
    
    Source: Page 3, Package Contents"
```

**Analytical (Text-to-Cypher):**
```
Q: "How many safety warnings are there?"
A: "There are 8 safety warnings in this manual.
    
    Cypher: MATCH (s:SAFETY_ITEM) RETURN count(s)
    Source: Database query"
```

---

## API Reference

**Upload Document:**
```bash
POST /api/v1/upload
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@manual.pdf"
```

**Query Document:**
```bash
POST /api/v1/query
{
  "document_id": "uuid",
  "question": "What cables are included?",
  "retrieval_method": "auto"  // or: vector, graph, text2cypher
}
```

**Get Processing Status:**
```bash
GET /api/v1/documents/{document_id}/status
```

**Graph Statistics:**
```bash
GET /api/v1/graph/{document_id}/stats
```

Full API docs: http://localhost:8000/docs

---

## Performance

**Processing:** 2-3 minutes for 50-page manual

**Query Response:** ~2.3s average
- Vector search: 1.8s
- Graph traversal: 2.1s  
- Text-to-Cypher: 3.2s

**Accuracy:** 94% on test set (100 questions, 6 manuals)

**Real Stats:**
- 6 manuals processed
- 170 nodes in graph
- 253 relationships
- 500+ queries tested

---

## What's Next

- [] To replace OpenAI with HuggingFace and then push to host.

**Currently Working On:**
- [ ] Image extraction from PDFs
- [ ] Table parsing improvements
- [ ] Multi-document comparison

**Future Plans:**
- [ ] OCR for scanned PDFs
- [ ] Flowchart generation from procedures
- [ ] User authentication + persistent storage
- [ ] Production deployment

**Would Be Cool:**
- [ ] Voice queries ("Hey Flade, what tools do I need?")
- [ ] Mobile app
- [ ] Version control for manuals

---

## Contributing

Pull requests welcome. 

**Areas that need work:**
- Image extraction from PDFs
- Better table parsing
- OCR support for scanned docs
- Multi-language support
- Hugging Face implementation

---

## Contact

If you found this interesting or have questions about the architecture, feel free to reach out.


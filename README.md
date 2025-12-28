# Manual Knowledge Graph - AI-Powered Technical Manual Assistant

Transform technical instruction manuals into intelligent, queryable knowledge graphs.

## 🎯 Features

- 🤖 AI-powered entity extraction
- 📊 3D knowledge graph visualization 
- 💬 Natural language Q&A
- 🔍 Hybrid retrieval (vector + graph + text2cypher)
- 📈 Automatic flowchart generation
- 📌 Source citation and traceability

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, LlamaIndex
- **Database:** Neo4j
- **AI:** OpenAI GPT-3.5/4
- **Frontend:** React, TypeScript
- **Visualization:** react-force-graph-3d

## 📋 Prerequisites

- Python 3.10-3.13
- Node.js 18+
- Neo4j Desktop
- OpenAI API key

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.template .env
# Edit .env with your credentials:
# - OPENAI_API_KEY=sk-your-key
# - NEO4J_PASSWORD=your-password
```

### 3. Neo4j Setup

1. Open Neo4j Desktop
2. Create database: "manual-kg-db"
3. Install APOC plugin
4. Start the database

### 4. Frontend Setup (Phase 5)

```bash
cd frontend
npm install
npm start
```

## 📊 Project Status

- ✅ Phase 0: Environment Setup [COMPLETE]
- ⏳ Phase 1: Backend Core [NEXT]
- ⬜ Phase 2-8: In Progress

## 💡 Python 3.13 Note

This project is compatible with Python 3.13. Updated pydantic versions are used for compatibility.

## 📝 License

MIT

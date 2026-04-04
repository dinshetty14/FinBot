# 🤖 FinBot — Advanced RAG Application

**FinSolve Technologies Internal Q&A Assistant** with Role-Based Access Control (RBAC), Hierarchical Document Chunking, Semantic Query Routing, Input/Output Guardrails, and RAGAs Evaluation.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Demo Users](#demo-users)
- [RBAC Access Matrix](#rbac-access-matrix)
- [Evaluation](#evaluation)
- [Screenshots](#screenshots)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                        │
│           Login  │  Chat Interface  │  Admin Panel           │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API
┌─────────────────────────▼───────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────┐ │
│  │  Input    │→ │ Semantic │→ │   RBAC    │→ │    LLM    │ │
│  │Guardrails │  │  Router  │  │  Filter   │  │ Generator │ │
│  └──────────┘  └──────────┘  └─────┬─────┘  └─────┬─────┘ │
│                                    │               │        │
│  ┌──────────┐               ┌──────▼──────┐ ┌─────▼─────┐ │
│  │  Output   │←──────────── │   Qdrant    │ │  ChatGroq  │ │
│  │Guardrails │              │ Vector DB   │ │   (LLM)    │ │
│  └──────────┘               └─────────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### RAG Pipeline Flow

1. **Input Guardrails** → PII detection, prompt injection blocking, rate limiting
2. **Semantic Routing** → Classifies query to finance/engineering/marketing/general/cross-dept
3. **RBAC Intersection** → Verifies user role has access to the target collection
4. **RBAC-Filtered Retrieval** → Qdrant search with metadata filtering (RBAC enforced at DB level)
5. **LLM Generation** → ChatGroq generates response with retrieved context and citations
6. **Output Guardrails** → Citation enforcement, grounding check, cross-role leakage detection

---

## ✨ Key Features

| Component | Implementation |
|---|---|
| **Document Parsing** | Docling with `HierarchicalChunker` for structure-aware chunking |
| **Embeddings** | `Qwen/Qwen3-Embedding-0.6B` via sentence-transformers |
| **Vector Database** | Qdrant (Docker local) with RBAC metadata filtering |
| **RBAC** | Enforced at vector DB query level — unauthorized chunks are never retrieved |
| **Query Routing** | `semantic-router` with 7 routes (5 business + 2 guardrail) |
| **Input Guardrails** | Off-topic detection, prompt injection, PII scrubbing, rate limiting |
| **Output Guardrails** | Source citation enforcement, grounding check, cross-role leakage detection |
| **LLM** | Groq (`openai/gpt-oss-20b`) |
| **Auth** | JWT tokens + bcrypt password hashing |
| **Users** | SQLite with seeded demo accounts |
| **Evaluation** | RAGAs with 5 metrics + ablation study |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, LangChain, Groq
- **Frontend**: Next.js 15 (TypeScript), CSS Modules
- **Vector DB**: Qdrant (Docker)
- **Document Parsing**: Docling + Hierarchical Chunker
- **Routing**: semantic-router
- **Evaluation**: RAGAs
- **Auth**: JWT + bcrypt + SQLite

---

## 📁 Project Structure

```
FinBot/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── config.py           # Settings, access matrix
│   │   ├── main.py             # FastAPI app
│   │   ├── auth.py             # JWT + bcrypt auth
│   │   ├── rbac.py             # RBAC filter builder
│   │   ├── database.py         # SQLite user management
│   │   ├── models.py           # Pydantic schemas
│   │   ├── ingestion/          # Docling parsing + chunking
│   │   ├── routing/            # Semantic router (7 routes)
│   │   ├── guardrails/         # Input + output guardrails
│   │   ├── rag/                # Full RAG pipeline
│   │   └── admin/              # Admin API endpoints
│   ├── requirements.txt
│   ├── seed_users.py           # Seed 5 demo users
│   └── run_ingestion.py        # Document ingestion CLI
├── frontend/                   # Next.js chat application
│   └── src/app/
│       ├── page.tsx            # Login page
│       ├── chat/page.tsx       # Chat interface
│       └── admin/page.tsx      # Admin panel
├── evaluation/
│   ├── eval_dataset.json       # 43 QA pairs (ground truth)
│   └── run_ragas.py            # RAGAs evaluation + ablation
├── data/                       # Source documents
│   ├── general/
│   ├── finance/
│   ├── engineering/
│   ├── marketing/
│   └── hr/                     # Merged into "general"
├── docker-compose.yml          # Qdrant service
├── .env.example                # Environment template
└── README.md
```

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop

### 1. Clone & Configure Environment

```bash
git clone <your-repo-url>
cd FinBot

# Copy environment template
cp .env.example .env

# Edit .env and set your GROQ_API_KEY
```

### 2. Start Qdrant

```bash
docker-compose up -d
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Seed demo users
python seed_users.py

# Ingest documents into Qdrant
python run_ingestion.py --recreate

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

## 👤 Demo Users

| Username | Password | Role | Department | Collections |
|---|---|---|---|---|
| `john_employee` | `employee123` | employee | General | general |
| `jane_finance` | `finance123` | finance | Finance | general, finance |
| `bob_engineer` | `engineer123` | engineering | Engineering | general, engineering |
| `alice_marketing` | `marketing123` | marketing | Marketing | general, marketing |
| `ceo_sarah` | `clevel123` | c_level | Executive | ALL |

---

## 🔒 RBAC Access Matrix

| Role | General | Finance | Engineering | Marketing |
|---|:---:|:---:|:---:|:---:|
| **employee** | ✅ | ❌ | ❌ | ❌ |
| **finance** | ✅ | ✅ | ❌ | ❌ |
| **engineering** | ✅ | ❌ | ✅ | ❌ |
| **marketing** | ✅ | ❌ | ❌ | ✅ |
| **c_level** | ✅ | ✅ | ✅ | ✅ |

> **RBAC Enforcement**: Access control is applied at the Qdrant vector database query level using metadata filtering. Unauthorized documents are **never retrieved** — not filtered post-retrieval.

---

## 📊 Evaluation

### Running RAGAs Evaluation

```bash
cd backend
python ../evaluation/run_ragas.py
```

### Metrics

| Metric | Description |
|---|---|
| **Faithfulness** | Whether the answer is grounded in the retrieved context |
| **Answer Relevancy** | Whether the answer addresses the question |
| **Context Precision** | Whether retrieved chunks are relevant |
| **Context Recall** | Whether all necessary context was retrieved |
| **Answer Correctness** | Whether the answer matches ground truth |

### Ablation Study

The evaluation runs 4 configurations:
1. **Full Pipeline** — routing + guardrails
2. **Without Routing** — no semantic routing
3. **Without Guardrails** — no input/output guardrails
4. **Baseline** — no routing, no guardrails

Results are saved to `evaluation/results/`.

---

## 📄 License

This project is an assignment submission for the AI Bootcamp.

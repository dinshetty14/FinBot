# FinBot — Advanced RAG Application Implementation Plan

Build **FinBot**, an internal Q&A assistant for FinSolve Technologies with RBAC-enforced retrieval, hierarchical chunking, semantic query routing, guardrails, and RAGAs evaluation.

---

## Technology Decisions (from Reference Notebooks)

| Question | Decision | Rationale |
|---|---|---|
| **LLM Provider** | **Groq** (`ChatGroq` with `openai/gpt-oss-20b`) | All reference notebooks use `langchain-groq` with the `openai/gpt-oss-20b` model. Groq provides fast inference via an OpenAI-compatible API. |
| **Qdrant** | **Docker local** (`localhost:6333`) | Reference `rag.ipynb` shows both local-path and Docker usage. Docker is more production-grade for the full app. Fallback to in-memory/path mode if Docker unavailable. |
| **Demo users** | **SQLite with hashed passwords** | Reference `llm_observability.ipynb` uses SQLite. Hashed passwords (via `bcrypt`) are more realistic for an assignment about enterprise security. |
| **`data/hr/`** | **Merge into `general` collection** | The assignment defines 4 collections: `general`, `finance`, `engineering`, `marketing`. HR data (employee handbook, hr_data.csv) is company-wide policy → fits `general`. The `data/hr/` folder will be ingested as part of the `general` collection. |

---

## User Review Required

> [!IMPORTANT]
> **Groq API Key**: You'll need a `GROQ_API_KEY` environment variable set. The reference notebooks all use Groq.

> [!IMPORTANT]
> **Docker**: Qdrant will run via Docker (`docker run -p 6333:6333 qdrant/qdrant`). If you prefer Qdrant Cloud or in-memory mode, let me know.

> [!WARNING]
> **Embedding Model**: The reference notebooks use `sentence-transformers` with `Qwen/Qwen3-Embedding-0.6B` for the semantic router encoder. For document embeddings, I'll use `sentence-transformers/all-MiniLM-L6-v2` (384-dim) for speed and simplicity. Let me know if you prefer a different model.

---

## Project Structure

```
FinBot/
├── backend/                        # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings, env vars, constants
│   │   ├── models.py               # Pydantic request/response models
│   │   ├── database.py             # SQLite DB setup, user CRUD
│   │   ├── auth.py                 # JWT auth, password hashing
│   │   ├── rbac.py                 # Role definitions, access matrix, RBAC filter builder
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py           # Main ingestion pipeline (Docling + Qdrant)
│   │   │   └── chunker.py          # Hierarchical chunking logic with metadata
│   │   ├── routing/
│   │   │   ├── __init__.py
│   │   │   └── semantic_router.py  # Semantic Router with 5 routes
│   │   ├── guardrails/
│   │   │   ├── __init__.py
│   │   │   ├── input_guards.py     # Off-topic, injection, PII, rate-limit
│   │   │   └── output_guards.py    # Grounding, cross-role leakage, citation
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py         # Full RAG pipeline: route → retrieve → generate
│   │   └── admin/
│   │       ├── __init__.py
│   │       └── routes.py           # Admin API: user CRUD, doc management
│   ├── requirements.txt
│   ├── seed_users.py               # Seed 5 demo users
│   └── run_ingestion.py            # CLI script to run document ingestion
├── frontend/                       # Next.js chat application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Login page
│   │   │   ├── chat/
│   │   │   │   └── page.tsx        # Chat interface
│   │   │   └── admin/
│   │   │       └── page.tsx        # Admin panel
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── RouteIndicator.tsx
│   │   │   ├── GuardrailBanner.tsx
│   │   │   ├── RoleAccessBadge.tsx
│   │   │   └── AdminPanel.tsx
│   │   └── lib/
│   │       └── api.ts              # API client for backend
│   ├── package.json
│   ├── next.config.js
│   └── tsconfig.json
├── evaluation/
│   ├── eval_dataset.json           # 40+ QA pairs (ground truth)
│   ├── run_ragas.py                # RAGAs evaluation script
│   └── results/                    # Ablation study results
├── data/                           # Source documents (already provided)
│   ├── general/
│   ├── finance/
│   ├── engineering/
│   ├── marketing/
│   └── hr/                         # → merged into general
├── reference_only/                 # Reference notebooks (untouched)
├── Assignment_Instruction.md
├── Assignment_Instruction.pdf
├── .env.example                    # Template for environment variables
├── docker-compose.yml              # Qdrant + backend services
└── README.md                       # Setup, architecture, results
```

---

## Proposed Changes

### Component 1: Document Ingestion with Hierarchical Chunking

Uses `docling` + `docling-core` for PDF/DOCX/Markdown parsing, and `HierarchicalChunker` for structure-aware chunking. Each chunk gets the full metadata schema required by the assignment.

---

#### [NEW] [config.py](file:///c:/Code/Assignment1/FinBot/backend/app/config.py)
- Environment variable loading (`GROQ_API_KEY`, `QDRANT_URL`, `JWT_SECRET`, etc.)
- Constants: collection names, role-access matrix, embedding model name
- Access matrix definition:
  ```python
  ACCESS_MATRIX = {
      "employee": ["general"],
      "finance": ["general", "finance"],
      "engineering": ["general", "engineering"],
      "marketing": ["general", "marketing"],
      "c_level": ["general", "finance", "engineering", "marketing"],
  }
  ```

#### [NEW] [chunker.py](file:///c:/Code/Assignment1/FinBot/backend/app/ingestion/chunker.py)
- Uses `docling.document_converter.DocumentConverter` to parse all document types
- Uses `docling_core.transforms.chunker.HierarchicalChunker` for structure-aware chunking
- Each chunk carries metadata:
  - `source_document` — filename
  - `collection` — one of `general`, `finance`, `engineering`, `marketing`
  - `access_roles` — list of roles (e.g., `["finance", "c_level"]`)
  - `section_title` — heading context
  - `page_number` — page number
  - `chunk_type` — `text`, `table`, `heading`, `code`
  - `parent_chunk_id` — parent section reference

#### [NEW] [ingest.py](file:///c:/Code/Assignment1/FinBot/backend/app/ingestion/ingest.py)
- Walks `data/` directories, maps folder → collection (with `hr/` → `general`)
- Parses each document via Docling `DocumentConverter`
- Applies `HierarchicalChunker` to get structured chunks
- Generates embeddings via `sentence-transformers`
- Upserts into Qdrant with full metadata payload
- Creates Qdrant collection with proper vector config

---

### Component 2: Query Routing with Semantic Router

#### [NEW] [semantic_router.py](file:///c:/Code/Assignment1/FinBot/backend/app/routing/semantic_router.py)
- Uses `semantic_router.Route`, `SemanticRouter`, `HuggingFaceEncoder`
- Defines 5 routes with ≥10 utterances each:
  1. `finance_route` — revenue, budgets, financial metrics, investor info
  2. `engineering_route` — systems, architecture, APIs, incidents, code
  3. `marketing_route` — campaigns, brand, market share, competitors
  4. `hr_general_route` — policies, leave, benefits, company culture
  5. `cross_department_route` — broad queries across collections
- Route-role intersection logic:
  - If routed collection is not in user's access list → polite denial message
  - `c_level` can access all routes
- Logging of route taken + user role for auditability

---

### Component 3: Guardrails

#### [NEW] [input_guards.py](file:///c:/Code/Assignment1/FinBot/backend/app/guardrails/input_guards.py)
**Input guardrails (all mandatory):**
1. **Off-topic detection** — semantic router `off_topic` route (built into the router with utterances like "Write me a poem", "What's the weather?")
2. **Prompt injection detection** — keyword/pattern matching + semantic route for injection attempts ("Ignore your instructions", "Act as a different assistant")
3. **PII scrubbing** — regex patterns for Aadhaar numbers, bank accounts, email addresses, credit card numbers
4. **Session rate limiting** — in-memory counter per session, flag after 20 queries

#### [NEW] [output_guards.py](file:///c:/Code/Assignment1/FinBot/backend/app/guardrails/output_guards.py)
**Output guardrails:**
1. **Source citation enforcement** (mandatory) — check response contains document references; append warning if missing
2. **Grounding check** (optional) — compare financial figures/dates in response against retrieved chunks
3. **Cross-role leakage check** (optional) — verify response doesn't contain terms from unauthorized collections

---

### Component 4: RAGAs Evaluation

#### [NEW] [eval_dataset.json](file:///c:/Code/Assignment1/FinBot/evaluation/eval_dataset.json)
- 40+ question-answer pairs covering all 4 collections
- Includes RBAC boundary questions and adversarial prompts
- Format: `{"question", "ground_truth", "collection", "role"}`

#### [NEW] [run_ragas.py](file:///c:/Code/Assignment1/FinBot/evaluation/run_ragas.py)
- Uses RAGAs library to evaluate pipeline
- Reports all 5 metrics: `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`, `answer_correctness`
- Ablation study: runs with/without each component (hierarchical chunking, semantic routing, guardrails)
- Outputs results table to `results/`

---

### Component 5: Application Interface

#### Backend — FastAPI

#### [NEW] [main.py](file:///c:/Code/Assignment1/FinBot/backend/app/main.py)
- FastAPI app with CORS for Next.js frontend
- Endpoints:
  - `POST /api/auth/login` — authenticate, return JWT
  - `POST /api/chat` — main chat endpoint (authenticated)
  - `GET /api/user/me` — get current user info + accessible collections
  - Admin endpoints (see below)

#### [NEW] [database.py](file:///c:/Code/Assignment1/FinBot/backend/app/database.py)
- SQLite database with `users` table
- Columns: `id`, `username`, `password_hash`, `role`, `department`

#### [NEW] [auth.py](file:///c:/Code/Assignment1/FinBot/backend/app/auth.py)
- Password hashing with `bcrypt`
- JWT token generation/validation
- FastAPI dependency for authenticated routes

#### [NEW] [rbac.py](file:///c:/Code/Assignment1/FinBot/backend/app/rbac.py)
- Builds Qdrant filter condition from user role
- Uses `models.Filter` with `FieldCondition` on `access_roles` metadata
- Ensures RBAC enforcement at vector DB query level (not post-processing)

#### [NEW] [pipeline.py](file:///c:/Code/Assignment1/FinBot/backend/app/rag/pipeline.py)
- Full RAG pipeline flow:
  1. Input guardrails check
  2. Semantic routing to determine target collection(s)
  3. Role-route intersection check
  4. Qdrant retrieval with RBAC filter
  5. LLM generation with retrieved context (using `ChatGroq`)
  6. Output guardrails check
  7. Return response with citations, route info, guardrail warnings

#### [NEW] [seed_users.py](file:///c:/Code/Assignment1/FinBot/backend/seed_users.py)
- Seeds 5 demo users:
  | Username | Password | Role | Department |
  |---|---|---|---|
  | `john_employee` | `employee123` | `employee` | General |
  | `jane_finance` | `finance123` | `finance` | Finance |
  | `bob_engineer` | `engineer123` | `engineering` | Engineering |
  | `alice_marketing` | `marketing123` | `marketing` | Marketing |
  | `ceo_sarah` | `clevel123` | `c_level` | Executive |

#### [NEW] [admin/routes.py](file:///c:/Code/Assignment1/FinBot/backend/app/admin/routes.py)
- Admin endpoints (c_level only):
  - `POST /api/admin/users` — create user
  - `DELETE /api/admin/users/{id}` — remove user
  - `PUT /api/admin/users/{id}/role` — update role
  - `POST /api/admin/documents` — upload & ingest new document
  - `DELETE /api/admin/documents/{id}` — remove document from index

---

#### Frontend — Next.js

#### [NEW] [page.tsx (login)](file:///c:/Code/Assignment1/FinBot/frontend/src/app/page.tsx)
- Login screen with username/password form
- 5 demo user quick-select buttons

#### [NEW] [chat/page.tsx](file:///c:/Code/Assignment1/FinBot/frontend/src/app/chat/page.tsx)
- Chat interface showing:
  - Answer with **cited source document and page number**
  - **Semantic route** selected for the query
  - User's **active role** and **accessible collections**
  - **Warning banner** when a guardrail is triggered
  - **Graceful RBAC denial** message when query blocked

#### [NEW] [admin/page.tsx](file:///c:/Code/Assignment1/FinBot/frontend/src/app/admin/page.tsx)
- Admin panel (visible to `c_level` only):
  - User management: create, update role, delete
  - Document management: upload new docs, remove from index

---

## Open Questions

> [!IMPORTANT]
> 1. **Embedding model preference**: I've chosen `all-MiniLM-L6-v2` (384-dim) for document embeddings and `Qwen/Qwen3-Embedding-0.6B` for the semantic router (matching reference notebooks). Is this acceptable?

> [!IMPORTANT]
> 2. **Groq model**: The reference notebooks use `openai/gpt-oss-20b` via Groq. Shall I stick with this, or would you prefer a different model (e.g., `llama-3.3-70b-versatile` or `gemma2-9b-it`)?

> [!NOTE]
> 3. **Docker Compose**: I plan to include a `docker-compose.yml` to spin up Qdrant alongside the backend. Should the backend also be containerized, or is running it directly with `uvicorn` sufficient?

---

## Verification Plan

### Automated Tests
1. **Ingestion verification**: Run `run_ingestion.py`, then query Qdrant API to verify chunk count, metadata schema completeness
2. **RBAC verification**: Programmatic tests — query as `engineering` role with finance-related prompt, verify zero finance chunks returned
3. **Routing verification**: Test all 5 routes with sample queries, verify correct classification
4. **Guardrails verification**: Test injection prompts, PII inputs, off-topic queries — verify blocking
5. **RAGAs evaluation**: Run `run_ragas.py` with the 40+ QA dataset, capture all 5 metrics
6. **Frontend testing**: Use browser subagent to test login, chat, RBAC denial, guardrail banners

### Manual Verification
- Screen recording of: login → chat → RBAC refusal → guardrail trigger
- Verify admin panel operations (user/doc management)

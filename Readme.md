# LawLens — Seek the Law. Know Your Rights.

> An AI-powered legal research assistant for Indian law with verified citations, section-level retrieval, scenario-based legal information, and multilingual support.

---

## 📌 Overview

**LawLens** is an AI-powered legal research assistant designed to help users understand Indian laws through **retrievable, verifiable legal sources**.

Users can ask legal questions in natural language, describe a situation, or look up a particular legal section. LawLens retrieves relevant provisions from its legal knowledge base and generates an understandable response with citations.

The system is designed around one core principle:

> **The LLM handles language. Tools handle facts, retrieval, validation, and decisions.**

LawLens is intended for **legal information and research support**, not personalized legal advice.

---

## 🎯 Problem Statement

Legal information can be difficult to search and understand because:

* Legal provisions are written in formal language.
* Users may not know which Act or section is relevant.
* Finding the correct section manually can be time-consuming.
* AI systems can hallucinate legal provisions or citations.
* Users may ask questions using everyday language rather than legal terminology.
* Access to legal information can be harder for users who prefer regional languages.

LawLens addresses these challenges using **Retrieval-Augmented Generation (RAG)**, deterministic section lookup, citation validation, and multilingual interaction.

---

## 🚀 Features

### 1. Legal Question Answering

Users can ask questions about supported Indian laws using natural language.

Example:

```text
What does Section 123 of BNS deal with?
```

LawLens retrieves the relevant legal provision and provides an explanation with its source.

### 2. Scenario → Relevant Legal Provisions

Users can describe a situation in everyday language.

Example:

```text
Someone threatened me repeatedly and sent threatening messages.
Which provisions may be relevant?
```

LawLens retrieves potentially relevant provisions from its supported legal corpus.

The system does **not** make a definitive legal determination. It presents retrieved provisions as potentially relevant based on the information provided.

### 3. Section Lookup

Users can request a specific section.

Example:

```text
BNS Section 123
```

The system performs a deterministic lookup against the structured legal database.

This prevents the LLM from inventing section numbers.

### 4. Semantic Legal Search

LawLens uses semantic retrieval to find relevant legal provisions even when the user's wording does not exactly match the wording of the Act.

### 5. Citation Verification

Every generated citation is validated against the available legal corpus before the response is returned.

### 6. English + Malayalam Support

LawLens is designed to support interaction in:

* English
* Malayalam

The legal knowledge base remains grounded in authoritative source material while the user-facing explanation can be generated in the requested language.

### 7. Conversation Memory

LawLens maintains session-based conversation history using MySQL.

### 8. Legal Safety Guardrails

LawLens provides **legal information**, not personalized legal advice.

The system avoids definitive legal conclusions about a user's specific case and grounds legal claims in retrieved sources.

---

## 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │        USER         │
                         │ English / Malayalam │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Django REST API  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   LangGraph Agent   │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
          │   Section    │ │  Semantic    │ │    Citation      │
          │    Lookup    │ │  Retrieval   │ │    Validator     │
          └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘
                 │                │                  │
                 ▼                ▼                  │
          ┌──────────────┐ ┌──────────────┐          │
          │    MySQL     │ │ Vector Store │          │
          │   Database   │ │ FAISS/Qdrant │          │
          └──────────────┘ └──────────────┘          │
                                   │                  │
                                   └────────┬─────────┘
                                            ▼
                                  ┌──────────────────┐
                                  │ Pydantic Output  │
                                  │    Validation    │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │  Verified Legal  │
                                  │     Response     │
                                  │ + Citations      │
                                  └──────────────────┘
```

---

## 🧠 Core Design Principle

LawLens separates **language generation** from **legal facts**.

### LLM

Responsible for:

* Understanding user questions
* Explaining retrieved provisions
* Generating natural-language responses
* Translating/explaining information in Malayalam

### Tools / Retrieval System

Responsible for:

* Section lookup
* Semantic retrieval
* Legal facts
* Citation verification
* Checking whether a cited provision exists

This reduces the risk of hallucinated legal provisions.

---

## 📚 Knowledge Base

LawLens uses **public and synthetic data only**, as required by the hackathon.

### Public Sources

The initial legal corpus will focus on official/public Indian legal sources.

Planned corpus:

* Bharatiya Nyaya Sanhita (BNS)
* Bharatiya Nagarik Suraksha Sanhita (BNSS)
* Bharatiya Sakshya Adhiniyam (BSA)

Additional public legal material may be added later.

Potential sources include official India Code material and publicly available Indian Supreme Court / High Court judgment datasets identified in the hackathon starter resources.

### Synthetic Data

Synthetic scenarios may be used for:

* Evaluation
* Testing
* Adversarial cases
* Scenario-based questions
* Multilingual testing

Synthetic scenarios will not be treated as sources of legal truth.

---

## 🔍 RAG Pipeline

```text
Official Legal Documents
          │
          ▼
   Document Extraction
          │
          ▼
     Text Cleaning
          │
          ▼
 Section-level Chunking
          │
          ▼
 Metadata Generation
          │
          ▼
      Embeddings
          │
          ▼
    Vector Database
          │
          ▼
   Semantic Retrieval
          │
          ▼
   Relevant Sections
```

Each retrieved legal document/section contains metadata such as:

```json
{
  "act": "BNS",
  "section": "123",
  "title": "Section title",
  "source": "Official source",
  "text": "Legal provision text"
}
```

---

## 🛠️ Tools

LawLens uses multiple tools rather than relying solely on the LLM.

### Tool 1 — Section Lookup

Deterministically retrieves a section using:

```text
Act + Section Number
```

### Tool 2 — Semantic Retrieval

Searches the vector database for provisions semantically related to the user's question.

### Tool 3 — Citation Validator

Checks whether:

1. The cited Act exists in the supported corpus.
2. The cited section exists.
3. The response has supporting retrieved content.
4. Unsupported citations are rejected.

---

## 🤖 Agent Workflow

```text
User Question
      │
      ▼
Understand Query
      │
      ▼
Choose Tool
      │
      ├───────────────┐
      ▼               ▼
Section Lookup   Semantic Retrieval
      │               │
      └───────┬───────┘
              ▼
      Generate Explanation
              │
              ▼
      Citation Validation
              │
        ┌─────┴─────┐
        │           │
      Valid       Invalid
        │           │
        ▼           ▼
     Return      Reject /
     Answer      Regenerate
```

---

## 🗄️ Database Design

### Act

```text
id
name
short_name
description
source_url
```

### Section

```text
id
act_id
section_number
title
text
source_url
```

### Conversation

```text
id
session_id
created_at
```

### Message

```text
id
conversation_id
role
content
created_at
```

---

## 🧾 Pydantic Validation

All AI-generated structured outputs are validated using Pydantic before being returned to the client.

Example:

```python
class Citation(BaseModel):
    act: str
    section: str
    source_text: str


class LegalAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    supported: bool
```

The exact schema may evolve during implementation.

---

## 🛡️ Safety & Guardrails

LawLens is designed as an **informational legal research assistant**.

The system should:

* Avoid fabricating legal sections.
* Reject nonexistent citations.
* Clearly identify unsupported questions.
* Avoid presenting uncertain information as fact.
* Avoid personalized legal advice.
* Avoid definitive legal conclusions about a user's specific case.
* Provide supporting citations for legal claims.
* Safely handle requests that ask for assistance in evading law enforcement or committing wrongdoing.

---

## 🧪 Evaluation

LawLens will be evaluated using a minimum **20-question evaluation set**.

### Evaluation Categories

* Legal question answering
* Section lookup
* Semantic retrieval
* Scenario-based queries
* Citation accuracy
* Nonexistent sections
* Unsupported laws
* Adversarial questions
* Malayalam queries
* Follow-up questions

### Metrics

| Metric             | Description                                                |
| ------------------ | ---------------------------------------------------------- |
| Citation Accuracy  | Whether citations point to valid supporting provisions     |
| Answer Correctness | Whether the answer is supported by retrieved legal content |
| Retrieval Accuracy | Whether relevant sections are retrieved                    |
| Failure Rate       | Percentage of failed/unsafe requests                       |
| P50 Latency        | Median response latency                                    |
| P95 Latency        | High-percentile response latency                           |
| Cost / Query       | Estimated model/tool cost per query                        |

Citation accuracy will be treated as a key metric.

---

## 📁 Project Structure

```text
lawlens/
│
├── backend/
│   ├── manage.py
│   ├── config/
│   ├── api/
│   ├── conversations/
│   ├── legal/
│   └── users/
│
├── ai/
│   ├── agent/
│   ├── tools/
│   ├── rag/
│   ├── prompts/
│   ├── validators/
│   └── multilingual/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── metadata/
│
├── eval/
│   ├── questions.json
│   ├── expected_answers.json
│   └── results/
│
├── scripts/
│   ├── ingest.py
│   ├── embed.py
│   └── evaluate.py
│
├── docs/
│   ├── architecture.md
│   └── evaluation.md
│
├── docker/
│
├── tests/
│
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## ⚙️ Technology Stack

| Component           | Technology                               |
| ------------------- | ---------------------------------------- |
| Backend             | Django + Django REST Framework           |
| Database            | MySQL                                    |
| Agent               | LangGraph                                |
| LLM                 | TBD                                      |
| Embeddings          | Multilingual embedding model             |
| Vector DB           | FAISS / Qdrant                           |
| Validation          | Pydantic                                 |
| Document Processing | Docling / equivalent                     |
| Evaluation          | Custom evaluation + RAG evaluation tools |
| Containerization    | Docker                                   |
| Version Control     | Git + GitHub                             |

The final choice of individual technologies may be adjusted during implementation.

---

## 🔐 Data Policy

LawLens will use:

* Public legal documents
* Public datasets with appropriate terms/licenses
* Synthetic test scenarios

LawLens will **not** use:

* Real client documents
* Private case files
* Real patient records
* Scraped personal information
* Confidential legal documents

All data sources and applicable licenses/terms will be documented.

---

## 🐳 Running Locally

### 1. Clone the repository

```bash
git clone <REPOSITORY_URL>
cd lawlens
```

### 2. Create environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create `.env`:

```env
DEBUG=True

SECRET_KEY=<YOUR_SECRET_KEY>

DATABASE_NAME=lawlens
DATABASE_USER=<YOUR_DB_USER>
DATABASE_PASSWORD=<YOUR_DB_PASSWORD>
DATABASE_HOST=localhost
DATABASE_PORT=3306

LLM_API_KEY=<YOUR_API_KEY>

VECTOR_DB_PATH=<VECTOR_DB_PATH>
```

Never commit `.env` or API keys to Git.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Start the server

```bash
python manage.py runserver
```

---

## 🐳 Docker

The project is intended to support Docker-based deployment.

```bash
docker compose up --build
```

The final Docker configuration will include the required application and database services.

---

## 🔌 API

Example endpoint:

```http
POST /api/chat/
```

Request:

```json
{
  "session_id": "demo-session",
  "message": "What does BNS section 123 deal with?",
  "language": "en"
}
```

Example response:

```json
{
  "answer": "....",
  "language": "en",
  "supported": true,
  "citations": [
    {
      "act": "BNS",
      "section": "123",
      "source_text": "...."
    }
  ]
}
```

The final API schema will be documented once implementation is complete.

---

## 📊 Project Status

### Phase 1 — Foundation

* [ ] Django project
* [ ] MySQL setup
* [ ] Git repository
* [ ] Basic API

### Phase 2 — Knowledge Base

* [ ] Collect official legal documents
* [ ] Extract sections
* [ ] Clean and structure data
* [ ] Populate MySQL
* [ ] Build embeddings
* [ ] Configure vector database

### Phase 3 — AI

* [ ] Semantic retrieval
* [ ] Section lookup tool
* [ ] Citation validator
* [ ] LLM integration
* [ ] LangGraph agent
* [ ] Pydantic validation

### Phase 4 — Features

* [ ] Legal Q&A
* [ ] Scenario → relevant provisions
* [ ] Conversation memory
* [ ] Malayalam support
* [ ] Safety guardrails

### Phase 5 — Evaluation & Deployment

* [ ] 20-question evaluation
* [ ] Citation accuracy measurement
* [ ] Latency measurement
* [ ] Failure-rate measurement
* [ ] Docker
* [ ] Deployment
* [ ] Structured logging
* [ ] Architecture diagram
* [ ] Final README
* [ ] Demo

---

## ⚠️ Disclaimer

LawLens is an **AI-powered legal information and research support system**.

It is not a substitute for a qualified legal professional and does not provide personalized legal advice or determine the legal outcome of a specific case.

Information shown by the system is limited to the supported legal corpus and should be verified against the cited authoritative source.

---

## 📜 Hackathon Context

LawLens is being developed as part of the:

**AI & Agentic Systems Hackathon — Legal Track**

The project follows the hackathon requirements around:

* Retrieval-Augmented Generation
* Agentic tool use
* Verified citations
* Django REST API
* MySQL-backed memory
* Pydantic validation
* Public/synthetic data
* Evaluation
* Deployment
* Documentation

---

## 👥 Team

**Team:** `<TEAM_NAME>`

**Hackathon:** `<HACKATHON_NAME>`

**Repository:** `<GITHUB_URL>`

**Live Demo:** `<DEPLOYMENT_URL>`

---

## ⭐ Vision

> **Seek the Law. Know Your Rights.**

LawLens aims to make Indian legal information easier to discover and understand while keeping the system grounded in **verifiable legal sources rather than unsupported AI-generated claims**.

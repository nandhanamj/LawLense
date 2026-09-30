# LawLens — System Architecture

> **LawLens — Seek the Law. Know Your Rights.**

## 1. Overview

LawLens is an AI-powered legal research assistant designed to help users discover and understand supported Indian legal provisions using **retrieval-backed, citation-verified information**.

The system supports:

* Natural-language legal questions
* Section-level legal lookup
* Semantic legal retrieval
* Scenario-based retrieval of potentially relevant provisions
* English and Malayalam interaction
* Conversation/session memory
* Citation validation
* Structured AI output validation

The system is designed around the principle:

> **The LLM handles language. Tools handle facts, retrieval, validation, and decisions.**

LawLens provides legal information and research support. It is not designed to provide personalized legal advice or make definitive legal determinations.

---

# 2. Architecture Goals

The architecture is designed to satisfy the core requirements of the Legal Track while allowing the four team members to develop components concurrently.

### Primary goals

1. Ground legal answers in the supported knowledge base.
2. Prevent hallucinated legal sections and citations.
3. Separate legal facts from LLM-generated language.
4. Support deterministic section lookup.
5. Support semantic retrieval.
6. Validate citations before returning answers.
7. Validate every structured AI output with Pydantic.
8. Maintain conversation memory using MySQL.
9. Support English and Malayalam interaction.
10. Allow scenario descriptions to retrieve potentially relevant provisions.
11. Support evaluation and measurable system performance.
12. Allow independent development through stable component interfaces.

---

# 3. High-Level Architecture

```text
                         ┌──────────────────────────┐
                         │          USER            │
                         │                          │
                         │ English / Malayalam      │
                         │ Question / Scenario      │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       Django REST API    │
                         │                          │
                         │ Request / Session Layer  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │      LangGraph Agent     │
                         │                          │
                         │ Query Understanding      │
                         │ Tool Selection           │
                         │ Workflow Orchestration   │
                         └────────────┬─────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  │                   │                   │
                  ▼                   ▼                   ▼
       ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
       │  Section Lookup  │ │ Semantic Retrieval│ │ Citation Validator│
       │      Tool        │ │      Tool         │ │       Tool        │
       └────────┬─────────┘ └────────┬─────────┘ └─────────┬────────┘
                │                    │                     │
                ▼                    ▼                     │
       ┌──────────────────┐ ┌──────────────────┐           │
       │      MySQL       │ │   Vector Store   │           │
       │                  │ │                  │           │
       │ Acts             │ │ FAISS / Qdrant   │           │
       │ Sections         │ │ Embeddings       │           │
       └──────────────────┘ └──────────────────┘           │
                                    │                      │
                                    └──────────┬───────────┘
                                               ▼
                                    ┌──────────────────────┐
                                    │     LLM Generation   │
                                    │                      │
                                    │ Explanation          │
                                    │ Language Generation  │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │   Pydantic Validator │
                                    │                      │
                                    │ Structured Output    │
                                    │ Validation           │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │    Verified Answer   │
                                    │                      │
                                    │ Answer + Citations   │
                                    └──────────────────────┘
```

---

# 4. Request Flow

A typical user request follows this pipeline:

```text
User
 ↓
Django API
 ↓
Session / Conversation Context
 ↓
LangGraph Agent
 ↓
Query Understanding
 ↓
Tool Selection
 ↓
Legal Retrieval
 ↓
LLM Explanation
 ↓
Citation Validation
 ↓
Pydantic Validation
 ↓
Final Response
```

The exact tools used depend on the request.

---

# 5. Request Types

LawLens primarily handles three types of requests.

## 5.1 Legal Question

Example:

```text
What does BNS Section 123 deal with?
```

Flow:

```text
Question
   ↓
Section Lookup
   ↓
Retrieve Section
   ↓
LLM Explanation
   ↓
Citation Validation
   ↓
Response
```

---

## 5.2 Natural-Language Legal Search

Example:

```text
What law applies when someone intentionally damages another person's property?
```

Flow:

```text
Question
   ↓
Semantic Retrieval
   ↓
Relevant Sections
   ↓
LLM Explanation
   ↓
Citation Validation
   ↓
Response
```

---

## 5.3 Scenario-Based Query

Example:

```text
Someone repeatedly threatened me through messages.
Which legal provisions may be relevant?
```

Flow:

```text
Scenario
   ↓
Query Understanding
   ↓
Semantic Retrieval
   ↓
Candidate Provisions
   ↓
Citation Validation
   ↓
LLM Explanation
   ↓
Pydantic Validation
   ↓
Response
```

The output should describe provisions as **potentially relevant based on the provided information**, rather than making a definitive legal determination.

---

# 6. Backend Architecture

The backend uses:

* Django
* Django REST Framework
* MySQL

The backend provides the interface between the user-facing application and the AI system.

```text
Client
  │
  ▼
Django REST Framework
  │
  ├── Chat API
  ├── Section API
  └── Session API
  │
  ▼
Application Services
  │
  ├── Agent Service
  ├── Section Lookup
  └── Conversation Memory
  │
  ▼
MySQL
```

---

# 7. Database Architecture

MySQL stores structured legal data and conversation/session information.

## 7.1 Act

```text
Act
--------------------
id
name
short_name
description
source_url
```

Example:

```text
Bharatiya Nyaya Sanhita
BNS
```

---

## 7.2 Section

```text
Section
--------------------
id
act_id
section_number
title
text
source_url
```

Relationship:

```text
Act
 │
 └───< Section
```

Each Act can contain multiple sections.

---

## 7.3 Conversation

```text
Conversation
--------------------
id
session_id
created_at
```

---

## 7.4 Message

```text
Message
--------------------
id
conversation_id
role
content
created_at
```

Relationship:

```text
Conversation
 │
 └───< Message
```

---

# 8. Knowledge Base Architecture

The legal knowledge base uses public legal sources and synthetic data for testing/evaluation.

The initial corpus is planned around:

* BNS
* BNSS
* BSA

Additional supported legal material can be added later.

The hackathon brief specifically identifies official India Code bare acts and publicly available Indian Supreme Court/High Court judgment datasets among possible resources.

---

# 9. Document Processing Pipeline

```text
Official Legal Document
          │
          ▼
   Document Extraction
          │
          ▼
      Text Cleaning
          │
          ▼
   Section Identification
          │
          ▼
   Metadata Generation
          │
          ▼
   Structured Legal Data
          │
          ├───────────────► MySQL
          │
          ▼
       Chunking
          │
          ▼
      Embeddings
          │
          ▼
     Vector Store
```

Legal sections should remain associated with their source metadata throughout the pipeline.

---

# 10. Semantic Retrieval

Semantic retrieval allows the system to find relevant legal provisions even when the user's wording differs from the wording used in the Act.

The retrieval pipeline is:

```text
User Query
    │
    ▼
Query Embedding
    │
    ▼
Vector Search
    │
    ▼
Top-K Results
    │
    ▼
Relevant Sections
```

Each result should contain sufficient metadata for citation generation.

Example:

```json
{
  "act": "BNS",
  "section": "123",
  "title": "Section title",
  "text": "Legal provision text",
  "source_url": "..."
}
```

---

# 11. Retrieval Interface

The RAG component exposes a stable interface so that other components do not depend directly on the vector database implementation.

Conceptual interface:

```python
retrieve(
    query: str,
    top_k: int = 5
) -> list[RetrievedSection]
```

Example result:

```json
[
  {
    "act": "BNS",
    "section": "123",
    "title": "...",
    "text": "...",
    "source_url": "..."
  }
]
```

The underlying vector database may be FAISS or Qdrant.

---

# 12. Section Lookup Tool

Section lookup is deterministic.

Conceptual interface:

```python
get_section(
    act: str,
    section_number: str
) -> Section | None
```

Example:

```python
get_section("BNS", "123")
```

The LLM should not independently determine whether a section exists.

Instead:

```text
Requested Section
       ↓
Section Lookup
       ↓
Database
       ↓
Section exists?
   ↙           ↘
 YES           NO
  ↓             ↓
Return       Safe fallback
section
```

This supports the hackathon requirement for deterministic section lookup.

---

# 13. Agent Architecture

LangGraph manages the agent workflow.

The agent is responsible for deciding which available tool should be used based on the user's request.

```text
                 ┌──────────────────┐
                 │    User Query    │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Query Understand │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   Tool Router    │
                 └────────┬─────────┘
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
        Section       Semantic      Other
        Lookup        Retrieval     Tools
             │            │
             └──────┬─────┘
                    ▼
             Retrieved Facts
                    │
                    ▼
             LLM Explanation
                    │
                    ▼
            Citation Validation
                    │
                    ▼
            Structured Output
```

---

# 14. Tool Architecture

LawLens contains at least three core tools.

## Tool 1 — Section Lookup

Purpose:

> Retrieve a specific legal section deterministically.

Source:

> MySQL

---

## Tool 2 — Semantic Retrieval

Purpose:

> Find provisions relevant to a natural-language query.

Source:

> Vector database

---

## Tool 3 — Citation Validator

Purpose:

> Verify that citations in the generated answer correspond to supported legal content.

The hackathon requires a citation validator that checks cited sections against the corpus before the response reaches the client.

---

# 15. Citation Validation Pipeline

Citation validation is one of the most important reliability components.

```text
Generated Answer
       │
       ▼
Extract Citations
       │
       ▼
Check Act
       │
       ▼
Check Section
       │
       ▼
Check Corpus
       │
       ▼
Check Supporting Content
       │
       ├───────────────┐
       │               │
      VALID          INVALID
       │               │
       ▼               ▼
 Continue         Reject / Regenerate
       │
       ▼
Pydantic Validation
       │
       ▼
Return Response
```

Example:

```text
User:
Tell me about BNS Section 999.

       ↓

Section Lookup

       ↓

Section not found

       ↓

Citation Validator

       ↓

Unsupported citation

       ↓

Safe response
```

The system must not fabricate Section 999.

---

# 16. LLM Responsibilities

The LLM is responsible for language-related tasks.

### The LLM may:

* Understand natural-language questions.
* Summarize retrieved legal provisions.
* Explain legal terminology.
* Generate user-friendly responses.
* Respond in Malayalam.
* Transform retrieved information into structured output.

### The LLM should not independently:

* Invent legal sections.
* Invent citations.
* Treat unsupported information as legal fact.
* Decide whether a specific legal outcome applies with certainty.

The underlying legal information must come from retrieval/database tools.

---

# 17. Pydantic Validation

Every structured AI output must pass Pydantic validation before being returned to the client.

Example conceptual schema:

```python
class Citation(BaseModel):
    act: str
    section: str
    source_text: str


class LegalAnswer(BaseModel):
    answer: str
    language: str
    citations: list[Citation]
    supported: bool
```

Pipeline:

```text
LLM Output
    ↓
Parse
    ↓
Pydantic Validation
    ↓
Valid?
 ↙      ↘
YES      NO
 ↓        ↓
Return   Reject /
         Regenerate
```

---

# 18. Multilingual Architecture

LawLens supports English and Malayalam interaction.

```text
English Query ───────┐
                     │
Malayalam Query ─────┼──► Query Understanding
                     │
                     ▼
              Semantic Retrieval
                     │
                     ▼
              Verified Legal Data
                     │
                     ▼
              LLM Explanation
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      English                Malayalam
      Response               Response
```

The retrieval system should use multilingual embeddings where appropriate.

The hackathon brief specifically suggests `intfloat/multilingual-e5-base` as a possible model for Indian-language support.

The exact embedding model remains an implementation decision.

---

# 19. Conversation Memory

Conversation history is stored in MySQL.

```text
Session
  │
  ▼
Conversation
  │
  ├── Message 1
  ├── Message 2
  ├── Message 3
  └── ...
```

Example:

```text
User:
What does Section X mean?

Assistant:
[Explanation]

User:
Explain that in simple Malayalam.

Assistant:
[Malayalam explanation]
```

The agent can use relevant previous messages as conversational context while legal facts continue to come from the supported knowledge base.

---

# 20. Safety Architecture

LawLens is an informational legal research system.

The system should handle:

### Unsupported law

```text
Question
   ↓
No relevant corpus content
   ↓
Inform user that the requested law is outside
the supported corpus
```

### Nonexistent section

```text
Section Lookup
      ↓
Not Found
      ↓
No fabricated citation
```

### Evasion request

For questions asking how to evade law enforcement or commit wrongdoing, the system should avoid providing operational assistance and instead respond safely.

The hackathon brief explicitly identifies adversarial/evasion-style questions as evaluation cases.

---

# 21. Scenario Feature

The scenario feature extends semantic retrieval.

```text
User Scenario
      │
      ▼
Query Understanding
      │
      ▼
Semantic Retrieval
      │
      ▼
Candidate Provisions
      │
      ▼
Citation Validation
      │
      ▼
LLM Explanation
```

The system should use language such as:

> "Based on the information provided, the following provisions may be relevant."

rather than:

> "You committed an offence under Section X."

This keeps the feature focused on legal information rather than a definitive legal determination.

---

# 22. API Architecture

The initial API design includes:

```text
POST /api/chat/
```

Purpose:

> Send a user question or scenario and receive a verified response.

Example request:

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
  "answer": "...",
  "language": "en",
  "supported": true,
  "citations": [
    {
      "act": "BNS",
      "section": "123",
      "source_text": "..."
    }
  ]
}
```

Additional endpoints may include:

```text
GET /api/sections/{act}/{section}/
POST /api/session/
```

The API contract may evolve during implementation.

---

# 23. Error Handling

The system should fail safely when required information is unavailable.

Possible cases:

```text
Invalid Request
       ↓
400 Response
```

```text
Section Not Found
       ↓
Safe Informational Response
```

```text
No Supporting Retrieval
       ↓
Unsupported Response
```

```text
Invalid LLM Output
       ↓
Pydantic Failure
       ↓
Retry / Safe Fallback
```

```text
Citation Validation Failure
       ↓
Reject Response
       ↓
Regenerate / Safe Fallback
```

---

# 24. Observability

The deployed system should collect structured logs.

Logs should support:

* Request tracking
* Correlation IDs
* Tool execution tracking
* Errors
* Retrieval latency
* LLM latency
* Total request latency
* Validation failures

Example:

```text
Request
  │
  ├── correlation_id
  ├── retrieval_time
  ├── tool_time
  ├── llm_time
  ├── validation_time
  └── total_time
```

This supports measurement of P50 and P95 latency.

---

# 25. Evaluation Architecture

The evaluation system uses a fixed test set.

```text
Evaluation Questions
        │
        ▼
      LawLens
        │
        ▼
     Responses
        │
        ▼
   Evaluation Engine
        │
        ├── Citation Accuracy
        ├── Answer Correctness
        ├── Retrieval Accuracy
        ├── Failure Rate
        ├── P50 Latency
        ├── P95 Latency
        └── Cost / Query
```

The hackathon requires at least 20 test questions.

---

# 26. Deployment Architecture

The system is intended to be containerized.

Conceptual deployment:

```text
                    Internet
                       │
                       ▼
                ┌─────────────┐
                │   Django    │
                │   API       │
                └──────┬──────┘
                       │
          ┌────────────┼─────────────┐
          │            │             │
          ▼            ▼             ▼
       MySQL       Vector DB      AI/LLM
          │            │             │
          └────────────┼─────────────┘
                       │
                       ▼
                 Validation
```

Docker Compose will be used for local multi-service development.

The final deployment platform is to be decided.

---
# 27. Component Dependency

```text
                    ┌──────────────┐
                    │   Frontend   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Django API   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ LangGraph    │
                    │ Agent        │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Section          Semantic        Citation
       Lookup           Retrieval       Validator
          │                │                │
          ▼                ▼                │
        MySQL          Vector DB            │
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                         LLM
                           │
                           ▼
                      Pydantic
                           │
                           ▼
                    Verified Response
```

---

# 28. Technology Stack

| Layer               | Technology                               |
| ------------------- | ---------------------------------------- |
| Backend             | Django                                   |
| API                 | Django REST Framework                    |
| Database            | MySQL                                    |
| Agent               | LangGraph                                |
| LLM                 | TBD                                      |
| Embeddings          | Multilingual embedding model             |
| Vector Store        | FAISS / Qdrant                           |
| Validation          | Pydantic                                 |
| Document Processing | Docling / equivalent                     |
| Evaluation          | Custom evaluation + RAG evaluation tools |
| Containers          | Docker                                   |
| Version Control     | Git + GitHub                             |

Technology choices may be finalized during implementation.

---

# 29. Project Structure

```text
lawlens/
│
├── backend/
│   ├── manage.py
│   ├── config/
│   ├── api/
│   ├── legal/
│   ├── conversations/
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
├── tests/
│
├── docker/
│
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# 30. Core Reliability Principle

The architecture intentionally separates:

```text
             LANGUAGE
                │
                ▼
               LLM
                │
                │
       ─────────┼─────────
                │
             FACTS
                │
        ┌───────┴────────┐
        ▼                ▼
   Structured DB     Vector Store
        │                │
        └───────┬────────┘
                ▼
          Citation Validator
                │
                ▼
           Verified Output
```

The LLM is therefore not the authoritative source of legal facts.

The supported legal corpus and validation tools provide the factual grounding.

---

# 31. Architecture Success Criteria

The architecture will be considered complete when:

* [ ] Legal questions can be answered using retrieved legal content.
* [ ] A specific section can be deterministically looked up.
* [ ] Semantic retrieval returns relevant provisions.
* [ ] At least two real tools are integrated into the agent.
* [ ] Citations are validated before responses reach the client.
* [ ] AI outputs pass Pydantic validation.
* [ ] Conversation history is stored in MySQL.
* [ ] Malayalam interaction works.
* [ ] Scenario-based retrieval works.
* [ ] Unsupported sections are not fabricated.
* [ ] The 20-question evaluation can be executed.
* [ ] Latency and failure metrics can be measured.
* [ ] The system can be containerized and deployed.

---

# 32. Guiding Principle

> **LawLens does not ask the LLM to know the law.**
>
> **LawLens retrieves the law, verifies it, and asks the LLM to explain it.**

**Seek the Law. Know Your Rights.**

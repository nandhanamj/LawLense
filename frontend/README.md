# LawLens Frontend

Evidence-backed legal research interface for the **Bharatiya Nyaya Sanhita, 2023 (BNS)**.

The frontend is a lightweight, responsive single-page application built with **React**, **TypeScript**, **Vite**, and **Lucide React**. It communicates with the LawLens Django REST API to provide deterministic section lookups, semantic statutory retrieval, verified citations, and refusal guardrails.

---

## Architecture Overview

- **Framework**: React 19 + TypeScript
- **Bundler / Dev Server**: Vite 8
- **Iconography**: Lucide React
- **Design System**: Bespoke legal-tech design tokens (deep navy `#0B132B`, warm slate, off-white surfaces, high-contrast readable typography)
- **Zero Heavy UI Frameworks**: Pure modern CSS with responsive containers, accessible focus outlines, and `prefers-reduced-motion` compliance.

---

## Quick Start

### 1. Prerequisites

- **Node.js**: v18+ (tested on v24)
- **npm**: v9+ (tested on v11)
- **LawLens Backend**: Running at `http://localhost:8000` (or `http://127.0.0.1:8000`)

### 2. Installation

Navigate to the `frontend/` directory and install dependencies:

```bash
cd frontend
npm install
```

*(On Windows PowerShell, use `npm.cmd install` if script execution policies are restricted).*

### 3. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

The default configuration expects the backend at:

```env
VITE_API_BASE_URL=http://localhost:8000
```

> **Note on Local Development**: In development mode (`npm run dev`), Vite is pre-configured with a reverse proxy for `/api/*` pointing to `VITE_API_BASE_URL` (default: `http://127.0.0.1:8000`). This completely eliminates cross-origin resource sharing (CORS) friction during local development without requiring any backend modifications.

### 4. Run Development Server

```bash
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## Production Build & Quality Checks

### Production Build

```bash
npm run build
```

Compiles TypeScript using `tsc -b` and builds optimized production bundles into `dist/`.

### Linting

```bash
npm run lint
```

Runs static code inspection via `oxlint`.

---

## API Integration

The frontend communicates with the LawLens Django backend endpoint:

- **Endpoint**: `POST /api/chat/`
- **Initial Request**:
  ```json
  {
    "query": "What is Section 103 of the BNS?"
  }
  ```
- **Follow-up Request (Session Context)**:
  ```json
  {
    "query": "What is the punishment?",
    "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
  ```

### Response Handling

The UI dynamically adapts to the backend's structured `LegalResponse` contract:

1. **Supported Responses (`supported: true`)**:
   - Renders answer text in readable paragraphs.
   - Highlights verified statutory grounding with an integrity badge.
   - Displays expandable citation cards for each referenced BNS section with direct statutory excerpts and source details.
   - Appends legal disclaimer.

2. **Refusal / Out-of-Scope Queries (`is_refusal: true` or `supported: false`)**:
   - Displays a neutral, professional statutory scope notice.
   - Accurately renders the backend's `refusal_reason` (e.g. for unsupported statutes like IPC or out-of-range sections like Section 999).
   - Omits citations cleanly without errors.

3. **Conversational Memory**:
   - Persists the active `conversation_id` in React state.
   - Seamlessly threads follow-up questions to backend MySQL conversation memory.
   - Offers a **New Conversation** button in the header that resets state and returns to the initial exploration screen.

4. **Legal Compliance Notice**:
   - Prominently clarifies that LawLens provides objective legal information from the statutory text of the Bharatiya Nyaya Sanhita, 2023, and does not constitute formal legal advice.

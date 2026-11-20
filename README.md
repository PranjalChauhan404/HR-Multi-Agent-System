# HR Multi-Agent System

An AI-powered Human Resources assistant built using a Multi-Agent Architecture to automate HR workflows, retrieve company policies, validate employee requests, and assist with HR-related operations.

## Overview

The HR Multi-Agent System uses specialized AI agents to handle different HR responsibilities. A central coordinator routes incoming requests to the appropriate agents, ensuring structured processing, authorization, and accurate responses.

## Architecture

The system consists of the following agents:

- **Router / Coordinator Agent:** Understands incoming requests and delegates tasks to specialized agents.
- **Policy Agent:** Retrieves and answers questions using company HR policies through Retrieval-Augmented Generation (RAG).
- **Leave Agent:** Handles leave-related queries and workflows.
- **Onboarding Agent:** Assists with employee onboarding and checklist generation.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | Gradio |
| Backend | Python |
| Agent Framework | CrewAI |
| LLM | OpenAI |
| Embeddings | Sentence Transformers (MiniLM) |
| Vector Database | Weaviate |
| Relational Database | PostgreSQL |
| Observability | Langfuse |
| Guardrails | Custom Python Implementation |

## Key Features

- Multi-agent orchestration using CrewAI.
- HR policy retrieval using RAG.
- Semantic search through Weaviate.
- Employee and leave management workflows.
- Role-based access validation.
- Manager authorization checks.
- Onboarding checklist generation.
- Custom guardrails for request validation.
- Observability and execution monitoring through Langfuse.

## Project Structure

```text
HR-MAS/
│
├── data/
│   └── policies/
│
├── diagnostics/
│
├── frontend/
│
├── src/
│   ├── agents.py
│   ├── audit.py
│   ├── config.py
│   ├── db.py
│   ├── guardrails.py
│   ├── ingest.py
│   ├── observability.py
│   ├── rag.py
│   ├── router.py
│   ├── tools.py
│   └── vector_store.py
│
├── tests/
│
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/PranjalChauhan404/HR-Multi-Agent-System.git
cd HR-Multi-Agent-System
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

Windows:
```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and configure the required API credentials and database connection settings according to `src/config.py`.

Never commit your `.env` file.

### 5. Start the application

```bash
python app.py
```

## Testing

Run the test suite using:

```bash
pytest
```

## Future Enhancements

- Docker-based deployment.
- Cloud hosting and public application access.
- Enhanced authentication and authorization.
- Improved scalability and monitoring.

## Author

**Pranjal Chauhan**

AI & Machine Learning | Generative AI | Agentic AI
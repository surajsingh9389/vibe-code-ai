# ⚡ Vibe Code AI

An AI-powered web app generator — describe your idea in plain English and get a fully functional single-page application in seconds. Think of it as a lightweight, open-source alternative to tools like [Lovable](https://lovable.dev).

---

## 📌 What is this project?

Vibe Code AI is an **AI agent pipeline** that takes a natural-language prompt (e.g. *"Create an expense tracker app"*) and automatically:

1. **Plans** the project — features, file structure, tech decisions.
2. **Architects** the implementation — breaks the plan into ordered, self-contained tasks.
3. **Codes** the entire app — produces a complete, working `index.html` with Tailwind CSS and vanilla JavaScript.

The generated app ships with state management, localStorage persistence, full CRUD operations, and input validation — all in a single file, ready to open in any browser.

A **Streamlit UI** wraps the pipeline so you can interact with it visually: type a prompt, watch the agent progress through each stage, and preview / download the result — all from your browser.

---

## 🏗️ Architecture

```
User Prompt
     │
     ▼
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│ Planner  │────▶│  Architect   │────▶│   Coder     │
│ (LLM)   │     │  (LLM)       │     │   (LLM)     │
└──────────┘     └──────────────┘     └─────────────┘
     │                  │                    │
  Produces:          Produces:           Produces:
  Plan object        TaskPlan object     index.html
  (name, features,   (ordered impl       (complete SPA)
   tech stack,        steps with
   file list)         file paths)
                                             │
                                             ▼
                                     ┌──────────────┐
                                     │  Preview UI  │
                                     │ (Streamlit)  │
                                     └──────────────┘
```

The pipeline is built with **LangGraph** — each agent is a graph node connected by edges that pass state forward. The graph compiles into a single executable chain:

```
START ──▶ planner ──▶ architect ──▶ coder ──▶ END
```

### Key modules

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — prompt input, progress display, HTML preview |
| `agents/graph.py` | LangGraph pipeline — defines nodes, edges, and the `run_agent_async()` entry point |
| `agents/prompts.py` | System & user prompts for each agent stage |
| `agents/states.py` | Pydantic models — `Plan`, `TaskPlan`, `ImplementationTask` |
| `agents/tools.py` | File I/O tools used by the coder agent (`write_file`, `read_file`, etc.) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Agent framework** | [LangGraph](https://github.com/langchain-ai/langgraph) |
| **LLM provider** | [Groq](https://groq.com) (via `langchain-groq`) |
| **Models** | `llama-3.1-8b-instant` (planner), `llama-3.3-70b-versatile` (architect), `openai/gpt-oss-120b` (coder) |
| **Data validation** | [Pydantic](https://docs.pydantic.dev) |
| **Frontend UI** | [Streamlit](https://streamlit.io) |
| **Generated apps** | HTML5 + [Tailwind CSS](https://tailwindcss.com) (CDN) + Vanilla JS |
| **Package manager** | [uv](https://docs.astral.sh/uv/) |
| **Language** | Python 3.12+ |

---

## 🚀 Local Setup

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **Groq API key** — get one free at [console.groq.com](https://console.groq.com)

### 1. Clone the repository

```bash
git clone https://github.com/surajsingh9389/vibe-code-ai.git
cd vibe-code-ai
```

### 2. Create the environment file

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Install dependencies

```bash
uv sync
```

This installs everything defined in `pyproject.toml` into a local `.venv`.

### 4. Run the app

```bash
uv run streamlit run app.py
```

The app will start at **http://localhost:8501**. Open it in your browser, type a prompt, and hit **⚡ Generate App**.

### 5. (Optional) Run the agent from CLI

You can also run the agent directly without the UI:

```bash
uv run python -m agents.graph
```

This will generate a project in the `generated_project/` directory.

---

## 📁 Project Structure

```
vibe-code-ai/
├── .env                    # API keys (not committed)
├── .streamlit/
│   └── config.toml         # Streamlit theme & server config
├── agents/
│   ├── __init__.py         # Package exports
│   ├── graph.py            # LangGraph pipeline (async)
│   ├── prompts.py          # LLM prompts for each stage
│   ├── states.py           # Pydantic state models
│   └── tools.py            # File I/O tools
├── app.py                  # Streamlit UI entry point
├── generated_projects/     # Output directory (auto-created)
├── pyproject.toml          # Dependencies & project metadata
└── uv.lock                 # Lockfile
```

---


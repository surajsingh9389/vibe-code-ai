from .prompts import planner_prompt, architect_prompt, coder_system_prompt
from .states import Plan, TaskPlan
from .tools import write_file, set_project_root

from langgraph.graph import StateGraph, START
from langchain_groq import ChatGroq

from dotenv import load_dotenv
import pathlib
import asyncio
import httpx


class RateLimitError(Exception):
    """Raised when the LLM API hits a rate or token limit."""
    pass


def _check_rate_limit(exc: Exception):
    """Inspect an exception and raise RateLimitError if it's a 429 / rate-limit issue."""
    msg = str(exc).lower()
    rate_keywords = ["rate_limit", "rate limit", "429", "too many requests",
                     "token limit", "tokens per minute", "requests per minute",
                     "quota exceeded", "resource_exhausted"]
    if any(kw in msg for kw in rate_keywords):
        raise RateLimitError(
            "⚠️ Agent rate limit exceeded"
            "Please try again Sometime later."
        ) from exc

load_dotenv()

# Initialize two different models

# 'Instant' model for the planner to save tokens/rate limits
planner_llm = ChatGroq(model="llama-3.1-8b-instant") 

# 'Versatile' model for the architect and coder (higher reasoning)
architect_llm = ChatGroq(model="llama-3.3-70b-versatile")

# High-capacity OSS model for the actual coding logic
coder_llm = ChatGroq(model="openai/gpt-oss-120b")



# --- ASYNC AGENT NODES ---
async def planner_agent(state: dict) -> dict:
    user_prompt = state["user_prompt"]
    plan_prompt_text = planner_prompt(user_prompt)
    
    try:
        resp = await planner_llm.with_structured_output(Plan).ainvoke(plan_prompt_text)
    except Exception as exc:
        _check_rate_limit(exc)
        raise
    
    if resp is None:
        raise ValueError("Planner failed to return a valid plan.")
    
    # Call progress callback if available
    if state.get("on_progress"):
        state["on_progress"]("planner", resp)
    
    return {'plan': resp}


async def architect_agent(state: dict) -> dict:
    plan: Plan = state['plan']
    arch_prompt = architect_prompt(plan)
    
    try:
        resp = await architect_llm.with_structured_output(TaskPlan).ainvoke(arch_prompt)
    except Exception as exc:
        _check_rate_limit(exc)
        raise
    
    if resp is None:
        raise ValueError("Architect failed to return a valid task plan.")
    
    resp.plan = plan
    
    # Call progress callback if available
    if state.get("on_progress"):
        state["on_progress"]("architect", resp)
    
    return {'plan_architecture': resp}


def clean_html(output: str) -> str:
    output = output.strip()

    # Remove markdown code fences like ```html ... ```
    if output.startswith("```"):
        parts = output.split("```")
        if len(parts) >= 2:
            output = parts[1]

    return output.strip()


def is_valid_html(html: str) -> bool:
    html_lower = html.lower()
    return "<html" in html_lower and "</html>" in html_lower


async def coder_agent(state: dict) -> dict:
    plan = state["plan_architecture"]
    
    user_prompt = f"""
Build a COMPLETE working web app:

{plan}

The app must behave like a real product, not a demo:
- persistent data
- full CRUD
- proper UI feedback
"""

    system_prompt = coder_system_prompt()
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    html = ""
    
    for _ in range(2):
        try:
            response = await coder_llm.ainvoke(messages)
        except Exception as exc:
            _check_rate_limit(exc)
            raise
        html = clean_html(response.content)

        if is_valid_html(html):
            break
 
    if not is_valid_html(html):
        raise ValueError("Failed to generate valid project")

    write_file.run({
        "path": "index.html",
        "content": html
    })
    
    # Call progress callback if available
    if state.get("on_progress"):
        state["on_progress"]("coder", "done")
         
    return {"status": "DONE", "generated_html": html}


def build_graph():
    """Build and compile the LangGraph agent pipeline."""
    graph = StateGraph(dict)

    graph.add_node('planner', planner_agent)
    graph.add_node('architect', architect_agent)
    graph.add_node('coder', coder_agent)

    graph.add_edge(START, 'planner')
    graph.add_edge('planner', 'architect')
    graph.add_edge('architect', 'coder')

    return graph.compile()


async def run_agent_async(user_prompt: str, project_dir: str = None, on_progress=None):
    """
    Run the full agent pipeline asynchronously and return the result.
    
    Args:
        user_prompt: The user's project description
        project_dir: Optional directory to save generated files
        on_progress: Optional callback fn(stage, data) for progress updates
    
    Returns:
        dict with the agent result including generated HTML
    """
    if project_dir:
        set_project_root(project_dir)
    
    agent = build_graph()
    
    result = await agent.ainvoke(
        {
            'user_prompt': user_prompt,
            'on_progress': on_progress,
        },
        {"recursion_limit": 50}
    )
    return result


def run_agent(user_prompt: str, project_dir: str = None, on_progress=None):
    """Sync wrapper around run_agent_async for backwards compatibility."""
    return asyncio.run(run_agent_async(user_prompt, project_dir, on_progress))


# Allow running directly for testing
if __name__ == "__main__":
    user_prompt = "Create a expense tracker app"
    resp = run_agent(user_prompt)
    print("\nProject generated successfully.")
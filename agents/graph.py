import time 
import os 
from typing import Dict, Any
from tenacity import retry, wait_exponential, stop_after_attempt

from prompts import planner_prompt, architect_prompt, coder_system_prompt
from states import Plan, TaskPlan, CoderState
from tools import read_file, write_file, list_files, get_current_directory


from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

from dotenv import load_dotenv
load_dotenv()

# Initialize two different models

# Fast model for planning/routing
planner_llm = ChatGroq(model="llama-3.1-8b-instant") 

# For the Coder, we bind the tools directly to the model
coder_tools = [read_file, write_file, list_files, get_current_directory]
coder_llm = ChatGroq(model="openai/gpt-oss-120b").bind_tools(coder_tools)

# --- RESILIENCY WRAPPER ---
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(5),
    reraise=True
)
def safe_llm_call(llm, messages, structured_output=None):
    """Adds a small delay and retry logic to handle 429 errors gracefully."""
    time.sleep(2.0) # Proactive cooldown for the TPM bucket
    if structured_output:
        return llm.with_structured_output(structured_output).invoke(messages)
    return llm.invoke(messages)


# --- AGENT NODES ---
def planner_agent(state: dict) -> dict:
    user_prompt = state['user_prompt']
    plan_prompt = planner_prompt(user_prompt)
    resp = safe_llm_call(planner_llm, plan_prompt, structured_output=Plan)
    
    if resp is None:
        raise ValueError("Planner failed to return a valid plan.")
    
    return {'plan': resp}


def architect_agent(state: dict) -> dict:
    plan: Plan = state['plan']
    arch_prompt = architect_prompt(plan)
    
    resp = safe_llm_call(planner_llm, arch_prompt, structured_output=TaskPlan)
    
    if resp is None:
        raise ValueError("Architect failed to return a valid task plan.")
    
    return {'plan_architecture': resp}


def coder_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    coder_state = state.get('coder_state')
    
    # Initialize state on first run
    if coder_state is None:
        coder_state = CoderState(task_plan=state['plan_architecture'], current_step_idx=0)
    
    steps = coder_state.task_plan.implementation_steps
    
    # Check if all tasks are finished
    if coder_state.current_step_idx >= len(steps):
        return { "coder_state": coder_state, "status": "DONE"}
    
    current_task = steps[coder_state.current_step_idx]
    
    existing_content = read_file.run(current_task.filepath)
    
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing content:\n{existing_content}\n"
        f"Use write_file(path, content) to save your changes"
    )
    
    system_prompt = coder_system_prompt()
    
    messages = [
        {"role": "system", "content": system_prompt}, 
        {"role": "user", "content": user_prompt}
    ]
    
    # Invoke the model that has tools bound to it
    response = safe_llm_call(coder_llm, messages)
    
    
    # Handle the Tool Calls manually (Token-efficient ReAct)
    if response.tool_calls:
        tool_map = {
            "read_file": read_file,
            "write_file": write_file,
            "list_files": list_files,
            "get_current_directory": get_current_directory
        }
        for tool_call in response.tool_calls:
            # Execute the tool
            selected_tool = tool_map[tool_call["name"]]
            print(f"--- [TOOL] Executing {tool_call['name']} ---")
            selected_tool.invoke(tool_call["args"])
    
    coder_state.current_step_idx +=1
    
    return {"coder_state": coder_state}

graph = StateGraph(dict)


graph.add_node('planner', planner_agent)
graph.add_node('architect', architect_agent)
graph.add_node('coder', coder_agent)

graph.add_edge(START, 'planner')
graph.add_edge('planner', 'architect')
graph.add_edge('architect', 'coder')
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get('status') == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)

agent = graph.compile()


# --- EXECUTION ---
if __name__ == "__main__":
    user_prompt = "create a simple calculator web app"
    # recursion_limit higher than the number of files expected
    resp = agent.invoke({'user_prompt': user_prompt}, {"recursion_limit": 50})
    print("\nProject generated successfully.")
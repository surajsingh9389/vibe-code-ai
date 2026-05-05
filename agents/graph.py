from langchain_groq import ChatGroq 
from agents.prompts import planner_prompt
from agents.states import Plan
from dotenv import load_dotenv
load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b")

user_prompt = "create a simple calculator web app"

prompt = planner_prompt(user_prompt)

res = llm.llm_with_structure_output(Plan).invoke(prompt)

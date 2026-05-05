
def planner_prompt(user_prompt: str):
    prompt = f"""
    You are a PLANNER agent. Convert the user prompt into a COMPLETE Engineering Project Plan
    
    User Request: 
    {user_prompt}
    """
    return prompt
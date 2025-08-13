import os
# --- THIS IS THE CORRECTED IMPORT SECTION ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import initialize_agent, AgentType

# --- Configuration ---
# IMPORTANT: Set your Gemini API Key here
os.environ["GOOGLE_API_KEY"] = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"

def run_math_agent(user_question):
    """
    Initializes and runs an AI agent that can solve math problems.
    """
    print("--- Initializing Math Agent ---")

    # 1. Load the Language Model (LLM)
    # We'll use Gemini, the same model from our dashboard
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)

    # 2. Load the Tool(s)
    # LangChain has a built-in tool that uses a Python interpreter to solve math.
    # It's safer than a full Python shell.
    tools = load_tools(["llm-math"], llm=llm)

    # 3. Initialize the Agent
    # We specify the tools, the LLM, and the type of agent.
    # ZERO_SHOT_REACT_DESCRIPTION is a standard agent type that reasons step-by-step.
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True  # verbose=True lets us see the agent's "thinking" process
    )

    print(f"\n--- Asking the agent: '{user_question}' ---")

    # 4. Run the Agent
    # We use agent.invoke() to ask the question.
    result = agent.invoke({"input": user_question})

    return result['output']

# --- Main execution block to test the agent ---
if __name__ == '__main__':
    question = "If a pizza has 8 slices and you eat 3, what percentage is left?"
    final_answer = run_math_agent(question)

    print("\n--- Final Answer ---")
    print(final_answer)
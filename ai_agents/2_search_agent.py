import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# --- Configuration ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"
os.environ["SERPAPI_API_KEY"] ="89a3e27d3a4c6b6886b29ef57ab20f4d2aa829c7dfeda0f56cac860dae2f1fb4"

def run_search_agent(user_question):
    """
    Initializes and runs a modern AI agent that can search the internet.
    """
    print("--- Initializing Final Search Agent ---")
    
    # 1. Load the Language Model (LLM)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)

    # 2. Load the Tool(s)
    tools = load_tools(["serpapi"], llm=llm)

    # 3. Create a very explicit prompt template to prevent loops
    # This gives the AI direct instructions on how to behave.
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a helpful assistant. Your job is to answer the user's question. "
            "You have access to a search tool. "
            "Use the search tool ONLY ONCE to find the answer. "
            "After you get the result from the search tool, you MUST provide the final answer immediately."
        )),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # 4. Create the Tool Calling Agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 5. Create the Agent Executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    print(f"\n--- Asking the agent: '{user_question}' ---")
    
    # 6. Run the Agent
    result = agent_executor.invoke({"input": user_question})
    
    return result['output']

# --- Main execution block to test the agent ---
if __name__ == '__main__':
    question = "Who is the current prime minister of the UK?"
    
    final_answer = run_search_agent(question)
    
    print("\n--- Final Answer ---")
    print(final_answer)
import os
from langchain_google_genai import ChatGoogleGenerativeAI
# --- THIS IS THE NEW, MORE RELIABLE IMPORT SECTION ---
# We are importing the specific tools directly from their stable location.
from langchain_community.tools.file_management import ListDirectoryTool, ReadFileTool, WriteFileTool
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# --- Configuration ---
# IMPORTANT: Set your Gemini API Key here
os.environ["GOOGLE_API_KEY"] = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"

def run_filesystem_agent(user_question):
    """
    Initializes and runs a modern AI agent that can interact with the local file system.
    """
    print("--- Initializing File System Agent ---")
    
    # 1. Load the Language Model (LLM)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)

    # 2. Load the Tool(s)
    # We create a list of the specific tools the agent can use.
    tools = [ListDirectoryTool(), ReadFileTool()]

    # 3. Get a reliable prompt from LangChain Hub
    prompt = hub.pull("hwchase17/react")

    # 4. Create the Agent
    agent = create_react_agent(llm, tools, prompt)

    # 5. Create the Agent Executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    print(f"\n--- Asking the agent: '{user_question}' ---")
    
    # 6. Run the Agent
    result = agent_executor.invoke({"input": user_question})
    
    return result['output']

# --- Main execution block to test the agent ---
if __name__ == '__main__':
    # First, let's create a test file for the agent to find and read.
    with open("test_document.txt", "w") as f:
        f.write("This is a test file for the Orion AI agent.")
    
    # Now, ask a question that requires the agent to use its tools
    question = "list the all folder in d drive "
    
    final_answer = run_filesystem_agent(question)
    
    print("\n--- Final Answer ---")
    print(final_answer)
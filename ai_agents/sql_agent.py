import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain

# --- Configuration ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"
DB_PATH = "company_database.db"

def run_sql_agent(user_question):
    """
    Initializes and runs an AI agent that can query a SQL database.
    """
    print("--- Initializing SQL Database Agent ---")

    # 1. Connect to the database
    db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

    # 2. Load the Language Model (LLM)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)

    # 3. Create the SQL Database Chain
    # This is a specialized chain that knows how to interact with SQL databases.
    db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

    print(f"\n--- Asking the agent: '{user_question}' ---")

    # 4. Run the Chain
    result = db_chain.invoke(user_question)

    return result['result']

# --- Main execution block to test the agent ---
if __name__ == '__main__':
    question = "How many employees are in the Engineering department, and what is their average salary?"

    final_answer = run_sql_agent(question)

    print("\n--- Final Answer ---")
    print(final_answer)
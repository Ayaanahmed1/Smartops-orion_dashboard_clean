import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document

# --- Configuration ---
# IMPORTANT: Set your Gemini API Key here
os.environ["GOOGLE_API_KEY"] = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"

def run_summarizer_agent(long_text):
    """
    Initializes and runs an AI agent that summarizes long text.
    """
    print("--- Initializing Text Summarizer Agent ---")

    # 1. Load the Language Model (LLM)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)

    # 2. Create a LangChain Document
    # LangChain's summarizer works best with a special 'Document' object.
    docs = [Document(page_content=long_text)]

    # 3. Create and Run the Summarization Chain
    # The "map_reduce" chain is excellent for summarizing. It summarizes small parts
    # of the text first and then combines those summaries into a final one.
    chain = load_summarize_chain(llm, chain_type="map_reduce")

    print("\n--- Summarizing the provided text... ---")

    result = chain.invoke(docs)

    return result['output_text']

# --- Main execution block to test the agent ---
if __name__ == '__main__':
    # Here is a long piece of text for the agent to summarize.
    # This is a paragraph about the planet Jupiter.
    text_to_summarize = """
    Jupiter is the fifth planet from the Sun and the largest in the Solar System. 
    It is a gas giant with a mass more than two and a half times that of all the 
    other planets in the Solar System combined, but slightly less than one-thousandth 
    the mass of the Sun. Jupiter is the third brightest natural object in the Earth's 
    night sky after the Moon and Venus. It has been known to astronomers since antiquity.
    The planet is primarily composed of hydrogen, but helium constitutes one-quarter 
    of its mass and one-tenth of its volume. It likely has a rocky core of heavier 
    elements, but like the other giant planets, Jupiter lacks a well-defined solid 
    surface. The ongoing contraction of its interior generates heat greater than the 
    amount of heat it receives from the Sun. Because of its rapid rotation, the planet's 
    shape is that of an oblate spheroid; it has a slight but noticeable bulge around 
    the equator. The outer atmosphere is visibly segregated into several bands at 
    different latitudes, resulting in turbulence and storms along their interacting 
    boundaries. A prominent result is the Great Red Spot, a giant storm that is known 
    to have existed since at least the 17th century when it was first seen by telescope.
    """

    summary = run_summarizer_agent(text_to_summarize)

    print("\n--- Final Summary ---")
    print(summary)
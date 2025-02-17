from dotenv import load_dotenv
import os
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader

# Load environment variables from .env.local file
load_dotenv()

# Print the API key to verify it is loaded correctly
# print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
response = OpenAI().complete("Paul Graham is ")
print(response)

# Set up settings with your OpenAI API key
Settings.llm = OpenAI(
    # api_key=os.getenv("OPENAI_API_KEY"),  # Use os.getenv to get the API key from the environment variable
    temperature=0.2,
    model="gpt-4"
)

documents = SimpleDirectoryReader("../data").load_data()
index = VectorStoreIndex.from_documents(documents)
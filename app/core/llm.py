from dotenv import load_dotenv
import os


load_dotenv()
path_to_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
os.environ['GOOGLE_APPLICATION_CREDENTIALS']=path_to_json

from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
import json
from dotenv import load_dotenv
import os
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.language_models.chat_models import SimpleChatModel

load_dotenv()

token = os.getenv("GITHUB_ACCESS_TOKEN")
endpoint = "https://models.github.ai/inference"
model = "openai/gpt-5-nano"

mock_data = {
                    "roles": ["Senior Backend Engineer", "Frontend Developer"],
                    "count": 2,
                    "budget": "$150k-180k",
                    "timeline": "6 weeks",
                    "skills": ["Python", "FastAPI", "React", "AWS"],
                    "location": "San Francisco, CA",
                    "experience_level": "Senior"
                }

mock_jd = """
**About the Role**
We're seeking an exceptional engineer to join our early-stage startup and help build our core platform.

**Key Responsibilities**
- Design and build scalable backend systems
- Architect database schemas and APIs
- Lead technical decisions and mentor team members
- Deploy and maintain production infrastructure

**Required Qualifications**
- 5+ years backend development experience
- Strong Python and FastAPI expertise
- Experience with PostgreSQL and cloud platforms
- Excellent system design skills

**Nice-to-Have**
- Startup experience
- Open source contributions

**What We Offer**
- Competitive salary and equity
- Flexible work environment
- Opportunity to shape product direction
"""


def get_llm():
    # Use mock in development
    if os.getenv("USE_MOCK_LLM", "false").lower() == "true":
        def mock_invoke(input_data):
            # Check if this is for the parser (hiring info extraction)
            if isinstance(input_data, dict) and "input" in input_data:
                user_input = input_data.get("input", "")
                
                return AIMessage(content=json.dumps(mock_data))
            
            # For job description generation
            elif isinstance(input_data, str) and "job description" in input_data.lower():
                return AIMessage(content=mock_jd)
            
            # Default response
            content = str(input_data)
            return AIMessage(content=f"[MOCK] Response for: {content[:50]}...")
        
        return RunnableLambda(mock_invoke)
    
    return ChatOpenAI(
        base_url=endpoint,
        api_key=token,
        model=model,
        max_retries=0
    )

class MockChatOpenAI(SimpleChatModel):
    """Mock LLM for testing without API calls"""
    
    @property
    def _llm_type(self) -> str:
        return "mock"
    
    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        # Extract the last message content
        if messages:
            last_msg = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            return f"[MOCK RESPONSE] Generated content for: {last_msg[:100]}..."
        return "[MOCK RESPONSE] No input provided"
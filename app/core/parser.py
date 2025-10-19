from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.llm import get_llm
from app.core.logger import log

class HiringInfo(BaseModel):
    """Structured hiring information extracted from user input"""
    roles: List[str] = Field(description="List of roles to hire for")
    count: Optional[int] = Field(description="Number of people to hire", default=None)
    budget: Optional[str] = Field(description="Budget for hiring (e.g., '$120k', '100-150k')", default=None)
    timeline: Optional[str] = Field(description="Hiring timeline (e.g., '1 month', '6 weeks')", default=None)
    skills: List[str] = Field(description="Required skills", default_factory=list)
    location: Optional[str] = Field(description="Job location or remote", default=None)
    experience_level: Optional[str] = Field(description="Experience level (junior, mid, senior)", default=None)

llm = get_llm()
parser = JsonOutputParser(pydantic_object=HiringInfo)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert HR assistant. Extract hiring information from user requests.
    
    Extract as much detail as possible:
    - roles: What positions are they hiring for?
    - count: How many people?
    - budget: What's the budget? (extract numbers and format)
    - timeline: How quickly do they need to hire?
    - skills: What skills or qualifications are mentioned?
    - location: Remote, office location, or hybrid?
    - experience_level: Junior, mid-level, senior?
    
    If information isn't mentioned, leave it as null or empty.
    
    {format_instructions}
    """),
    ("human", "{input}")
])

chain = prompt | llm | parser

def parse_hiring_request(user_input):

    try:
        result = chain.invoke({
            "input" : user_input,
            "format_instructions" : parser.get_format_instructions()
        })
        # print(f"Parsed hiring request: {result}")
        log.info(f"Parsed hiring request: {result}")
        return result
    except Exception as e:
        # print(f"Error parsing hiring request: {e}")
        log.info(f"Error parsing hiring request: {e}")
        return e
    

def update_hiring_data(existing_data: Dict, new_input: str) -> Dict:
    """
    Update existing hiring data with new information from user
    """
    parsed = parse_hiring_request(new_input)
    
    # Merge with existing data (new data takes precedence)
    updated = existing_data.copy()
    
    for key, value in parsed.items():
        if value is not None:  # Only update if new value exists
            if key == "roles" and value:
                # Append new roles to existing
                existing_roles = set(updated.get("roles", []))
                existing_roles.update(value)
                updated["roles"] = list(existing_roles)
            elif key == "skills" and value:
                # Append new skills to existing
                existing_skills = set(updated.get("skills", []))
                existing_skills.update(value)
                updated["skills"] = list(existing_skills)
            else:
                # Replace with new value
                updated[key] = value
    
    return updated

# Optimize with only one prompt calling
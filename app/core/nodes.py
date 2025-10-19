from langchain_core.messages import BaseMessage, AIMessage
from typing import Dict, Any
from app.core.logger import log
from app.core.parser import update_hiring_data
from app.core.llm import get_llm
from app.utils.save_to_notion import upload_to_notion
import concurrent.futures
import re
from dotenv import load_dotenv
import os
load_dotenv()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)    

llm = get_llm()

NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")


def parse_input_node(state) -> Dict[str, Any]:
    last_message = state["messages"][-1]
    user_input = last_message.content

    existing_data = state.get("hiring_data", {})
    updated_data = update_hiring_data(existing_data, user_input)

    has_roles = updated_data.get("roles")
    has_budget = updated_data.get("budget")
    has_timeline = updated_data.get("timeline")

    if has_roles and has_budget and has_timeline:
        # next_step = "research"
        next_step = "create_jd"
        response = f"Got it! I'll help you hire {', '.join(updated_data['roles'])}. Let me research some details..."
    else:
        next_step = "clarify"
        missing = []
        if not has_budget:
            missing.append("your_budget")
        if not has_timeline:
            missing.append("your_timeline")
        
        response = f"I need a bit more information. Could you tell me about: {', '.join(missing)}?"

    return {
    "hiring_data": updated_data,
    "current_step": next_step,
    "messages": [AIMessage(content=response)]
    }

def research_node(state) -> Dict[str, Any]:
    """ Implement tools fist - next step """
    pass



def _strip_fences(text: str) -> str:
    """
    If the model returns fenced blocks (```md / ```markdown / ```), extract the inner text.
    Otherwise, return as-is.
    """
    m = re.search(r"```(?:md|markdown|text)?\s*(.*?)\s*```", text, flags=re.S | re.I)
    return m.group(1) if m else text.strip()

def create_jd_node(state: Dict[str, Any]):
    """Generate ONE job description via LLM (markdown) and upload to Notion."""
    hiring_data = state.get("hiring_data", {}) or {}

    # Role can be either `role` (str) or `roles` (list with one item)
    role = hiring_data.get("role")
    if not role:
        roles = hiring_data.get("roles") or []
        role = roles[0] if roles else "Job Role"

    experience = hiring_data.get("experience_level", "Mid-level")
    location = hiring_data.get("location", "Remote")
    skills = hiring_data.get("skills", [])
    company = hiring_data.get("company", "Early-stage startup")

    # Target Notion page
    page_id_or_url = hiring_data.get("notion_page_id") or NOTION_PAGE_ID
    if not page_id_or_url:
        raise ValueError("Missing Notion page id/url. Set NOTION_PAGE_ID or provide hiring_data['notion_page_id'].")

    # Prompt (light guidance only). If you already supply a prompt elsewhere, you can replace this.
    prompt = f"""
Write a compelling, concise job description in **markdown** for the role: {role}.
Context:
- Experience Level: {experience}
- Location: {location}
- Company: {company}
- Key Skills: {', '.join(skills) if skills else 'to be determined'}

Sections:
1) Role Overview (2-3 sentences)
2) Key Responsibilities (3-5 bullets)
3) Required Qualifications (3-5 bullets)
4) Nice-to-Have (2-3 bullets)
5) What We Offer (2-3 bullets)

Return ONLY the markdown for the JD (no preface or commentary).
""".strip()

    # 1) Get JD markdown from the LLM
    jd_raw = llm.invoke(prompt).content
    jd_md = _strip_fences(jd_raw)

    # 2) Append to Notion (role becomes the Notion heading_2 inside the uploader)
    # NOTE: upload_to_notion should be your fixed PATCH /v1/blocks/{id}/children version.
    _executor.submit(
        upload_to_notion,
        jd_md,
        page_id_or_url=page_id_or_url,
        title=role
    )

    # 3) Chat preview (optional: include a top-level header just for the chat view)
    chat_preview = f"## {role}\n\n{jd_md}"

    return {
        "hiring_data": hiring_data,
        "current_step": "create_plan",
        "messages": [
            AIMessage(content=f"Here is your job description:\n\n{chat_preview}\n\nShould I create a hiring plan now?")
        ]
    }

### Use LLM call for every hiring plan is different

def create_hiring_plan_node(state) -> Dict[str, Any]:
    """Create a structured hiring plan"""
    
    hiring_data = state["hiring_data"]
    timeline = hiring_data.get("timeline", "4-6 weeks")
    budget = hiring_data.get("budget", "TBD")
    roles = hiring_data.get("roles", [])
    
    plan = f"""# Hiring Plan

                ## Roles
                {chr(10).join(f'- {role}' for role in roles)}

                ## Timeline: {timeline}

                ## Budget: {budget}

                ## Hiring Checklist

                ### Week 1: Preparation
                - [ ] Finalize job descriptions
                - [ ] Set up interview process
                - [ ] Post on job boards (LinkedIn, Indeed, AngelList)
                - [ ] Reach out to network for referrals

                ### Week 2-3: Sourcing & Screening
                - [ ] Review applications daily
                - [ ] Conduct initial phone screens
                - [ ] Shortlist candidates for technical rounds

                ### Week 3-4: Interviews
                - [ ] Technical/skills assessment
                - [ ] Team fit interviews
                - [ ] Final round with leadership

                ### Week 4-5: Closing
                - [ ] Reference checks
                - [ ] Prepare offers
                - [ ] Negotiate and close

                ## Next Steps
                1. Review and customize job descriptions
                2. Set up tracking in ATS or spreadsheet
                3. Activate job postings
                4. Begin outreach to your network
            """
    # filepath = save(plan, "hiring_plan.md")
    # log.info(f"Saved job descriptions to {filepath}")
    
    return {
        "hiring_data": hiring_data,
        "current_step": "post_notion",
        "messages": [AIMessage(content=f"{plan}\n\nWould you like me to post these job descriptions to Notion?")]
    }

def post_notion_node(state) -> Dict[str, Any]:
    """
    Post job descriptions to Notion

    Only done for JD not for hiring plan

    """

    hiring_data = state.get("hiring_data", {})
    
    try:
        # future = _executor.submit(upload_to_notion, hiring_data, "Job Descriptions")
        # log.info("Notion Upload started")
        response_text = "Job descriptions have been posted to Notion successfully!"
    except Exception as e:
        log.error(f"Failed to upload to Notion: {e}")
        response_text = "There was an error posting to Notion. Please check the logs."


    return {
        "hiring_data": hiring_data,
        "current_step": "done",
        "messages": [AIMessage(content=response_text)]
    }

# def create_jd_node(state):
#     """Generate job descriptions using LLM"""
    
#     hiring_data = state["hiring_data"]
    
#     roles = hiring_data.get("roles", [])
    
#     # MOCK DATA - Replace LLM calls
#     mock_jds = {
#         "Senior Backend Engineer": """### **Senior Backend Engineer**

#         **Location:** Remote
#         **Company:** Early-Stage Startup

#         #### **Role Overview**

#         We're seeking a Senior Backend Engineer to architect and build scalable, high-performance systems that power our core product. You'll work directly with the founding team to establish technical foundations and make critical architectural decisions.

#         #### **Key Responsibilities**

#         * Design and implement robust, scalable backend services and APIs
#         * Build and optimize database schemas and data pipelines
#         * Establish engineering best practices and code quality standards
#         * Collaborate with cross-functional teams to ship features rapidly
#         * Own critical systems end-to-end from design to deployment

#         #### **Required Qualifications**

#         * 5+ years of backend development experience with production systems
#         * Strong proficiency in Python, Go, or similar backend languages
#         * Deep understanding of distributed systems, databases, and API design
#         * Experience with cloud platforms (AWS, GCP, or Azure)
#         * Track record of building scalable systems from the ground up

#         #### **Nice-to-Have Skills**

#         * Experience in early-stage startup environments
#         * Familiarity with containerization (Docker, Kubernetes)
#         * Knowledge of microservices architecture

#         #### **What We Offer**

#         * Significant equity stake in a high-growth startup
#         * Opportunity to shape core technical decisions and architecture
#         * Competitive salary and comprehensive benefits"""
#     }
    
#     job_descriptions = []
#     for role in mock_jds.keys():
#         # Use mock data instead of LLM call
#         print("_"*20)
#         print(role)
#         jd_content = mock_jds.get(role, f"Mock job description for {role}")
#         print(jd_content)
#         print("_"*20)
#         job_descriptions.append(jd_content)
#         try:
#             future = _executor.submit(upload_to_notion, jd_content, page_id_or_url="Job Descriptions", title=role)
#         except Exception as e:
#             log.error(f"Failed to upload {role} to Notion: {e}")


#     full_jd = "\n\n---\n\n".join(job_descriptions)
    
#     return {
#         "hiring_data" : hiring_data,
#         "current_step": "create_plan",
#         "messages": [AIMessage(content=f"Here are your job descriptions:\n\n{full_jd}\n\nShould I create a hiring plan now?")]
#     }

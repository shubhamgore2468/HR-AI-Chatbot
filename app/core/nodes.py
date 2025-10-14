from langchain_core.messages import BaseMessage, AIMessage

from app.core.logger import log
from app.utils.utils import save_to_markdown as save
from app.core.parser import update_hiring_data
from app.core.llm import get_llm


llm = get_llm()

def parse_input_node(state):
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

def research_node(state):
    """ Implement tools fist - next step """
    pass

def create_jd_node(state):
    """Generate job descriptions using LLM"""
    
    
    hiring_data = state["hiring_data"]
    
    roles = hiring_data.get("roles", [])
    skills = hiring_data.get("skills", [])
    experience = hiring_data.get("experience_level", "mid-level")
    location = hiring_data.get("location", "Remote")
    
    job_descriptions = []
    
    for role in roles:
        prompt = f"""Create a compelling job description for a {role} position.

                    Details:
                    - Experience Level: {experience}
                    - Location: {location}
                    - Key Skills: {', '.join(skills) if skills else 'to be determined'}
                    - Company: Early-stage startup

                    Include:
                    1. Role overview (2-3 sentences)
                    2. Key responsibilities (3-5 points)
                    3. Required qualifications (3-5 points)
                    4. Nice-to-have skills (2-3 points)
                    5. What we offer (2-3 points)

                    Keep it concise and exciting.
                """

        jd = llm.invoke(prompt)
        job_descriptions.append(f"## {role}\n\n{jd.content}")
    
    full_jd = "\n\n---\n\n".join(job_descriptions)

    filepath = save(full_jd, "job_descriptions.md")
    log.info(f"Saved job descriptions to {filepath}")
    
    return {
        "current_step": "create_plan",
        "messages": [AIMessage(content=f"Here are your job descriptions:\n\n{full_jd}\n\nShould I create a hiring plan now?")]
    }

def create_hiring_plan_node(state):
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
    filepath = save(plan, "hiring_plan.md")
    log.info(f"Saved job descriptions to {filepath}")
    
    return {
        "current_step": "post_notion",
        "messages": [AIMessage(content=f"{plan}\n\nWould you like me to post these job descriptions to Notion?")]
    }

def post_notion_node(state):
    """Post job descriptions to Notion"""
    pass


from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
from pathlib import Path
from utils import print_out_md
import uuid

from app.core.nodes import parse_input_node, research_node, create_jd_node, create_hiring_plan_node, post_notion_node


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    hiring_data: dict
    current_step: str
    session_id: uuid.UUID

def route_next_step(state: AgentState):
    """ Determine the next step based on the current state."""

    step = state.get("current_step", "start")
    if step == "start" or step=="clarify":
        return "parse_input"
    elif step == "research":
        return "research"
    elif step == "create_jd":
        return "create_jd"
    elif step == "create_plan":
        return "create_plan"
    elif step == "post_notion":
        return "post_notion"
    elif step == "complete":
        return "end"
    
    return "end"

def build_graph():

    workflow = StateGraph(AgentState)

    workflow.add_node("parse_input", parse_input_node)
    workflow.add_node("research", research_node)
    workflow.add_node("create_jd", create_jd_node)
    workflow.add_node("create_plan", create_hiring_plan_node)
    workflow.add_node("post_notion", post_notion_node)

    workflow.set_entry_point("parse_input")

    workflow.add_conditional_edges(
        "parse_input",
        route_next_step,
        {
            "parse_input": "parse_input",
            "create_jd": "create_jd",
            "end": END,
        }
    )
    # Update above step to have research after tools implementation
    # workflow.add_conditional_edges(
    #     "research",
    #     route_next_step,
    #     {
    #         "create_jd": "create_jd",
    #         "end": END
    #     }
    # )
    
    workflow.add_conditional_edges(
        "create_jd",
        route_next_step,
        {
            "create_plan": "create_plan",
            "end": END
        }
    )
    
    # workflow.add_conditional_edges(
    #     "create_plan",
    #     route_next_step,
    #     {
    #         "post_notion": "post_notion",
    #         "end": END
    #     }
    # )
    
    # workflow.add_edge("post_notion", END)
    
    return workflow.compile()

def run_agent():
    g = build_graph()
    initial_state = {
        "messages" : [HumanMessage(content="I need to hire a founding engineer and a GenAI intern")],
        "hiring_data" : {
            "roles" : ["Founding Engineer", "GenAI Intern"],
            "budget": "$150k for engineer, $50k for intern",
            "timeline": "6 weeks",
            "skills": ["Python", "LangChain", "System Design", "ML/AI"]
        },
        "current_step": "start"
    }

    result = g.invoke(initial_state)
    print("\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    for msg in result["messages"]:
        print(f"\n{msg.content}")

    
    print_out_md(Path("output/final_results.md"), result)


if __name__ == "__main__":
    run_agent()



import os
import json
import asyncio
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from typing import Literal, TypedDict

load_dotenv(Path(__file__).parent / ".env")
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from database import add_task, get_tasks, delete_task, complete_task, add_event, get_events

logger = logging.getLogger(__name__)

gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=gemini_key)

def llm_call(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return response.text

class AgentState(TypedDict):
    user_id: int
    message: str
    intent: str
    response: str
    params: dict

def classify_intent(state: AgentState) -> dict:
    msg = state["message"].lower()
    prompt = f"""Classify this message into exactly one intent:
- add_task: user wants to add a task or to-do
- list_tasks: user wants to see tasks
- complete_task: user wants to mark a task done
- delete_task: user wants to delete a task
- add_event: user wants to schedule an event or reminder with a date/time
- list_events: user wants to see scheduled events
- chat: anything else

Message: "{state["message"]}"
Respond with just the intent name."""
    
    intent = llm_call(prompt).strip().lower()
    valid = {"add_task", "list_tasks", "complete_task", "delete_task", "add_event", "list_events", "chat"}
    if intent not in valid:
        intent = "chat"
    
    params = {}
    if intent == "add_task":
        params["title"] = state["message"]
    elif intent == "add_event":
        params["title"] = state["message"]
    
    return {"intent": intent, "params": params}

def handle_add_task(state: AgentState) -> dict:
    title = state["params"].get("title", state["message"])
    task_id = add_task(state["user_id"], title)
    return {"response": f"Task added! (ID: {task_id})"}

def handle_list_tasks(state: AgentState) -> dict:
    tasks = get_tasks(state["user_id"])
    if not tasks:
        return {"response": "No tasks found. Add one with /addtask"}
    lines = ["Your tasks:"]
    for t in tasks:
        status = "✅" if t["completed"] else "⬜"
        lines.append(f"{status} {t['id']}. {t['title']}")
    return {"response": "\n".join(lines)}

def handle_chat(state: AgentState) -> dict:
    result = llm_call(f"You are ABDI AI assistant. Answer this: {state['message']}")
    return {"response": result}

import dateparser

def handle_add_event(state: AgentState) -> dict:
    msg = state["message"]
    prompt = f"""Extract event info from this message. Return JSON:
{{"title": "event name", "date_description": "description of when", "time": "HH:MM" or null}}
- date_description: the date info (e.g. 'tomorrow', 'next Monday', '2025-12-25', or null)
- time: time in 24h format (e.g. '15:00') or null
If no date/time found, use date_description=null, time=null.

Message: "{msg}"
Return ONLY the JSON."""
    
    result = llm_call(prompt)
    try:
        data = json.loads(result.strip().strip("```json").strip("```").strip())
        title = data.get("title", msg)
        date_desc = data.get("date_description")
        time_str = data.get("time")

        event_date = None
        if date_desc:
            parsed = dateparser.parse(date_desc)
            if parsed:
                event_date = parsed.strftime("%Y-%m-%d")

        event_id = add_event(state["user_id"], title, event_date, time_str)
        parts = [f"Event scheduled! (ID: {event_id})"]
        if event_date:
            parts.append(f"on {event_date}")
        if time_str:
            parts.append(f"at {time_str}")
        return {"response": " ".join(parts)}
    except:
        event_id = add_event(state["user_id"], msg)
        return {"response": f"Event added! (ID: {event_id})"}

def handle_list_events(state: AgentState) -> dict:
    events = get_events(state["user_id"])
    if not events:
        return {"response": "No events scheduled."}
    lines = ["Your events:"]
    for e in events:
        date_str = f" on {e['event_date']}" if e["event_date"] else ""
        time_str = f" at {e['event_time']}" if e["event_time"] else ""
        lines.append(f"- {e['id']}. {e['title']}{date_str}{time_str}")
    return {"response": "\n".join(lines)}

def router(state: AgentState) -> Literal["add_task", "list_tasks", "complete_task", "delete_task", "add_event", "list_events", "chat"]:
    return state["intent"]

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_intent)
    graph.add_node("add_task", handle_add_task)
    graph.add_node("list_tasks", handle_list_tasks)
    graph.add_node("complete_task", handle_add_task)
    graph.add_node("delete_task", handle_add_task)
    graph.add_node("add_event", handle_add_event)
    graph.add_node("list_events", handle_list_events)
    graph.add_node("chat", handle_chat)

    graph.set_entry_point("classify")
    graph.add_conditional_edges("classify", router, {
        "add_task": "add_task",
        "list_tasks": "list_tasks",
        "complete_task": "complete_task",
        "delete_task": "delete_task",
        "add_event": "add_event",
        "list_events": "list_events",
        "chat": "chat",
    })
    graph.add_edge("add_task", END)
    graph.add_edge("list_tasks", END)
    graph.add_edge("complete_task", END)
    graph.add_edge("delete_task", END)
    graph.add_edge("add_event", END)
    graph.add_edge("list_events", END)
    graph.add_edge("chat", END)

    return graph.compile()

executor = ThreadPoolExecutor(max_workers=2)
agent = build_agent()

async def process_message(user_id: int, message: str) -> str:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, lambda: agent.invoke({
        "user_id": user_id,
        "message": message,
        "intent": "",
        "response": "",
        "params": {},
    }))
    return result["response"]

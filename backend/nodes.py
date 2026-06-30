import json
from datetime import date
from groq import Groq
from .config import Config
from .database import SessionLocal
from .models import Task

# Initialize Groq client
client = Groq(api_key=Config.GROQ_API_KEY)

def classify_tasks(state):
    """Classify tasks using Groq llama-3.1-8b"""
    tasks = state.get("tasks", [])
    if not tasks:
        return state
    
    task_text = "\n".join([f"- {t.get('description', '')}" for t in tasks])
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": """Classify each task. Return JSON array with:
                description, category (work/personal/health/learning), urgency (high/medium/low)"""},
                {"role": "user", "content": task_text}
            ],
            temperature=0.1
        )
        
        result = json.loads(response.choices[0].message.content)
        if isinstance(result, dict) and "tasks" in result:
            state["tasks"] = result["tasks"]
        else:
            state["tasks"] = result
    except Exception as e:
        print(f"Classification error: {e}")
        # Fallback classification
        state["tasks"] = [
            {"description": t.get("description", ""), "category": "work", "urgency": "medium"}
            for t in tasks
        ]
    
    return state

def surface_overdue(state):
    """Find overdue tasks from database"""
    db = SessionLocal()
    today = date.today()
    
    try:
        overdue = db.query(Task).filter(
            Task.user_id == int(state["user_id"]),
            Task.due_date <= today,
            Task.completed_at.is_(None)
        ).all()
        
        state["overdue_items"] = [
            {"id": t.id, "description": t.description, "due_date": str(t.due_date)}
            for t in overdue
        ]
    except Exception as e:
        print(f"Overdue surfacing error: {e}")
        state["overdue_items"] = []
    finally:
        db.close()
    
    return state

def generate_eod_summary(state):
    """Generate EOD summary using Groq llama-3.3-70b"""
    tasks = state.get("tasks", [])
    overdue = state.get("overdue_items", [])
    completed = [t for t in tasks if t.get("completed", False)]
    
    prompt = f"""
    Today's tasks:
    - Planned: {len(tasks)}
    - Completed: {len(completed)}
    - Overdue: {len(overdue)}
    
    Overdue items: {[o['description'] for o in overdue]}
    
    Write a 1-paragraph EOD summary: what got done, what slipped.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You write concise, actionable daily summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        state["eod_summary"] = response.choices[0].message.content
    except Exception as e:
        print(f"EOD summary error: {e}")
        state["eod_summary"] = f"Completed {len(completed)} of {len(tasks)} tasks. {len(overdue)} overdue."
    
    return state

def plan_tomorrow(state):
    """Generate tomorrow's plan"""
    overdue = state.get("overdue_items", [])
    tasks = state.get("tasks", [])
    
    prompt = f"""
    Overdue tasks: {[o['description'] for o in overdue]}
    Today's planned tasks: {[t.get('description', '') for t in tasks]}
    
    Suggest tomorrow's task list (max 5 items). Include urgent overdue items first.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        state["tomorrow_plan"] = response.choices[0].message.content
    except Exception as e:
        print(f"Planning error: {e}")
        state["tomorrow_plan"] = "Review overdue tasks and prioritize them."
    
    return state
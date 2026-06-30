from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, List, Dict, Any
import sqlite3
import json
import re
import time
from groq import Groq
from .config import Config
from .database import SessionLocal
from .models import Task
from datetime import datetime, date

class AgentState(TypedDict):
    user_id: str
    tasks: List[Dict[str, Any]]
    overdue_items: List[Dict[str, Any]]
    eod_summary: str
    tomorrow_plan: str
    messages: List[str]

class ProductivityAgent:
    def __init__(self):
        self.conn = sqlite3.connect("./checkpoints.db", check_same_thread=False)
        self.checkpointer = SqliteSaver(self.conn)
        self.graph = self._build_graph()
        self.client = Groq(api_key=Config.GROQ_API_KEY)
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("classifier", self.classifier)
        workflow.add_node("overdue_surfacer", self.surface_overdue)
        workflow.add_node("eod_summarizer", self.eod_summarizer)
        workflow.add_node("next_day_planner", self.plan_tomorrow)
        
        workflow.set_entry_point("classifier")
        workflow.add_edge("classifier", "overdue_surfacer")
        workflow.add_edge("overdue_surfacer", "eod_summarizer")
        workflow.add_edge("eod_summarizer", "next_day_planner")
        workflow.add_edge("next_day_planner", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def classifier(self, state: AgentState) -> AgentState:
        """Classify tasks using Groq llama-3.1-8b"""
        tasks = state.get("tasks", [])
        if not tasks:
            return state
        
        task_text = "\n".join([f"- {t.get('description', '')}" for t in tasks])
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": """Classify each task. Return ONLY a JSON array with:
                    description, category (work/personal/health/learning), urgency (high/medium/low)
                    
                    Example: [{"description": "Write report", "category": "work", "urgency": "high"}]
                    
                    IMPORTANT: Return ONLY the JSON, no other text."""},
                    {"role": "user", "content": task_text}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            print(f"LLM Response: {content}")
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            
            if isinstance(result, dict) and "tasks" in result:
                state["tasks"] = result["tasks"]
            else:
                state["tasks"] = result
                
        except Exception as e:
            print(f"Classification error: {e}")
            state["tasks"] = [
                {"description": t.get("description", ""), "category": "work", "urgency": "medium"}
                for t in tasks
            ]
        
        return state
    
    def surface_overdue(self, state: AgentState) -> AgentState:
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
    
    def eod_summarizer(self, state: AgentState) -> AgentState:
        """Generate EOD summary using ACTUAL data from state (NO LLM)"""
        
        tasks = state.get("tasks", [])
        
        print(f"📊 eod_summarizer received: {tasks}")
        
        # Count completed and incomplete
        completed = [t for t in tasks if t.get("completed", False) is True]
        incomplete = [t for t in tasks if not t.get("completed", False)]
        
        total = len(tasks)
        completed_count = len(completed)
        incomplete_count = len(incomplete)
        
        print(f"📊 Completed: {completed_count}, Incomplete: {incomplete_count}")
        
        # Generate summary based on ACTUAL data
        if total == 0:
            state["eod_summary"] = "No tasks were planned for today."
            return state
        
        if completed_count == total and total > 0:
            task_names = ", ".join([t.get('description', '') for t in completed])
            state["eod_summary"] = f"🎉 AMAZING! You completed ALL {total} tasks today: {task_names}. You're on fire!"
        
        elif completed_count > 0 and incomplete_count > 0:
            completed_names = ", ".join([t.get('description', '') for t in completed])
            incomplete_names = ", ".join([t.get('description', '') for t in incomplete])
            state["eod_summary"] = f"Today you completed {completed_count} out of {total} tasks. ✅ Done: {completed_names}. ⏳ Pending: {incomplete_names}. Tackle these tomorrow."
        
        elif completed_count == 0 and total > 0:
            task_names = ", ".join([t.get('description', '') for t in tasks])
            state["eod_summary"] = f"Today you had {total} tasks planned but completed none: {task_names}. Let's make a fresh start tomorrow!"
        
        else:
            state["eod_summary"] = f"Today you completed {completed_count} of {total} tasks."
        
        return state
    
    def plan_tomorrow(self, state: AgentState) -> AgentState:
        """Generate tomorrow's plan using ACTUAL data (NO LLM)"""
        
        tasks = state.get("tasks", [])
        overdue = state.get("overdue_items", [])
        
        # Get incomplete tasks
        incomplete = [t for t in tasks if not t.get("completed", False)]
        
        # Build tomorrow's plan based on ACTUAL data
        if not incomplete and not overdue:
            state["tomorrow_plan"] = "🎉 All tasks completed! Great job! Plan tomorrow's tasks fresh."
        elif incomplete:
            task_names = "\n- ".join([t.get('description', '') for t in incomplete])
            state["tomorrow_plan"] = f"📋 Carry over these {len(incomplete)} tasks to tomorrow:\n- {task_names}\n\nStart with the most important one first!"
        else:
            state["tomorrow_plan"] = "Review your tasks and set new priorities for tomorrow."
        
        return state
    
    # ==================== RUN METHOD (FIXED) ====================
    def run(self, user_id: str, input_state: dict) -> dict:
        """Execute agent - FORCES fresh state each time"""
        
        # ✅ CRITICAL: Use timestamp to create fresh thread_id
        # This prevents LangGraph from using cached state
        fresh_thread_id = f"{user_id}_{int(time.time())}"
        
        config = {"configurable": {"thread_id": fresh_thread_id}}
        input_state["user_id"] = user_id
        
        print(f"🔍 Running agent with thread_id: {fresh_thread_id}")
        print(f"🔍 Input state tasks: {input_state.get('tasks', [])}")
        
        result = self.graph.invoke(input_state, config)
        
        print(f"🔍 Result summary: {result.get('eod_summary', 'No summary')}")
        
        return result
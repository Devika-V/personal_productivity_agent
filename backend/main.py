from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import json
from pydantic import BaseModel

from .database import get_db, engine
from .models import Base, User, Task, DailyLog, EODSummary, UserStreak
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .graph import ProductivityAgent
from .scheduler import start_scheduler
from .config import Config

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Productivity Agent")

# CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8502"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Initialize agent
agent = ProductivityAgent()

# Start scheduler
start_scheduler()

# ==================== PYDANTIC MODELS ====================

class MorningCheckin(BaseModel):
    tasks: List[str]

class EveningCheckin(BaseModel):
    completed_task_ids: List[int]
    notes: Optional[str] = ""

# ==================== AUTH ENDPOINTS ====================

@app.post("/auth/signup")
def signup(email: str, password: str, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

# ==================== CHECK-IN ENDPOINTS ====================

@app.post("/checkin/morning")
def morning_checkin(
    checkin: MorningCheckin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tasks = checkin.tasks
    
    # Save tasks
    saved_tasks = []
    for task_desc in tasks:
        task = Task(
            user_id=current_user.id,
            description=task_desc,
            created_at=datetime.utcnow()
        )
        db.add(task)
        saved_tasks.append({"description": task_desc})
        db.flush()
    
    # Save daily log
    log = DailyLog(
        user_id=current_user.id,
        morning_plan="\n".join(tasks),
        date=datetime.utcnow()
    )
    db.add(log)
    
    # Update streak
    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()
    if not streak:
        streak = UserStreak(
            user_id=current_user.id,
            current_streak=0,
            longest_streak=0,
            total_checkins=0
        )
        db.add(streak)
    
    # Initialize values if None
    if streak.current_streak is None:
        streak.current_streak = 0
    if streak.longest_streak is None:
        streak.longest_streak = 0
    if streak.total_checkins is None:
        streak.total_checkins = 0
    
    today = datetime.utcnow().date()
    last_checkin = streak.last_checkin_date.date() if streak.last_checkin_date else None
    
    if last_checkin == today - timedelta(days=1):
        streak.current_streak += 1
        streak.total_checkins += 1
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
    elif last_checkin != today:
        streak.current_streak = 1
        streak.total_checkins += 1
    
    streak.last_checkin_date = datetime.utcnow()
    db.commit()
    
    # Run agent classification (optional - skip for speed)
    agent_state = {"tasks": [{"description": t} for t in tasks]}
    result = agent.run(str(current_user.id), agent_state)
    
    # Update tasks with classification
    for i, task_data in enumerate(result.get("tasks", [])):
        if i < len(tasks):
            db_tasks = db.query(Task).filter(
                Task.user_id == current_user.id,
                Task.description == tasks[i],
                Task.completed_at.is_(None)
            ).order_by(Task.created_at.desc()).first()
            if db_tasks:
                db_tasks.category = task_data.get("category", "work")
                db_tasks.priority = task_data.get("urgency", "medium")
    
    db.commit()
    
    return {
        "message": "Morning check-in saved",
        "tasks_saved": len(saved_tasks),
        "streak": streak.current_streak,
        "tasks": result.get("tasks", [])
    }

@app.post("/checkin/evening")
def evening_checkin(
    completed_task_ids: List[int],
    notes: Optional[str] = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"📝 Evening check-in - User: {current_user.id}, Task IDs: {completed_task_ids}")
    
    # Mark tasks as complete
    updated_count = 0
    for task_id in completed_task_ids:
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == current_user.id
        ).first()
        
        if task:
            if task.completed_at is None:
                task.completed_at = datetime.utcnow()
                updated_count += 1
                print(f"✅ Marked task {task_id} as complete")
            else:
                print(f"⚠️ Task {task_id} was already completed")
        else:
            print(f"❌ Task {task_id} NOT found")
    
    # Save evening log
    log = db.query(DailyLog).filter(
        DailyLog.user_id == current_user.id,
        DailyLog.date >= datetime.utcnow().date()
    ).order_by(DailyLog.date.desc()).first()
    
    if log:
        log.evening_completions = str(completed_task_ids)
        log.notes = notes
    else:
        log = DailyLog(
            user_id=current_user.id,
            evening_completions=str(completed_task_ids),
            notes=notes,
            date=datetime.utcnow()
        )
        db.add(log)
    
    db.commit()
    
    return {
        "message": "Evening check-in saved",
        "completed": updated_count,
        "task_ids": completed_task_ids
    }

# ==================== EOD ENDPOINT (SIMPLIFIED - NO AGENT) ====================

@app.post("/eod/run")
def run_eod(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get today's tasks
    today = datetime.utcnow().date()
    
    tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.created_at >= today,
        Task.created_at < today + timedelta(days=1)
    ).all()
    
    if not tasks:
        return {"message": "No tasks found for today"}
    
    # Count completed and incomplete
    completed = [t for t in tasks if t.completed_at is not None]
    incomplete = [t for t in tasks if t.completed_at is None]
    
    total = len(tasks)
    completed_count = len(completed)
    incomplete_count = len(incomplete)
    
    # ✅ Generate summary based on ACTUAL data (NO AGENT, NO LLM)
    if completed_count == total and total > 0:
        task_names = ", ".join([t.description for t in completed])
        summary = f"🎉 AMAZING! You completed ALL {total} tasks today: {task_names}. You're on fire!"
    elif completed_count > 0 and incomplete_count > 0:
        completed_names = ", ".join([t.description for t in completed])
        incomplete_names = ", ".join([t.description for t in incomplete])
        summary = f"Today you completed {completed_count} out of {total} tasks. ✅ Done: {completed_names}. ⏳ Pending: {incomplete_names}. Tackle these tomorrow."
    elif completed_count == 0 and total > 0:
        task_names = ", ".join([t.description for t in tasks])
        summary = f"Today you had {total} tasks planned but completed none: {task_names}. Let's make a fresh start tomorrow!"
    else:
        summary = f"Today you completed {completed_count} of {total} tasks."
    
    # ✅ Generate tomorrow's plan (NO AGENT, NO LLM)
    if not incomplete:
        tomorrow_plan = "🎉 All tasks completed! Great job! Plan tomorrow's tasks fresh."
    else:
        task_names = "\n- ".join([t.description for t in incomplete])
        tomorrow_plan = f"📋 Carry over these {len(incomplete)} tasks to tomorrow:\n- {task_names}\n\nStart with the most important one first!"
    
    # Save to database
    eod_summary = EODSummary(
        user_id=current_user.id,
        summary=summary,
        tomorrow_plan=tomorrow_plan,
        date=datetime.utcnow()
    )
    db.add(eod_summary)
    db.commit()
    
    return {
        "summary": summary,
        "tomorrow_plan": tomorrow_plan,
        "overdue": [],
        "_debug": {
            "total_tasks": total,
            "completed": completed_count,
            "incomplete": incomplete_count
        }
    }

# ==================== GET ENDPOINTS ====================

@app.get("/tasks/today")
def get_today_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = datetime.utcnow().date()
    tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.created_at >= today,
        Task.created_at < today + timedelta(days=1)
    ).all()
    
    return {
        "tasks": [
            {
                "id": t.id,
                "description": t.description,
                "category": t.category or "uncategorized",
                "priority": t.priority or "medium",
                "completed": t.completed_at is not None,
                "due_date": t.due_date
            }
            for t in tasks
        ]
    }

@app.get("/summary/{user_id}")
def get_summary(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    summary = db.query(EODSummary).filter(
        EODSummary.user_id == user_id
    ).order_by(EODSummary.date.desc()).first()
    
    if not summary:
        return {"message": "No summary found"}
    
    return {
        "summary": summary.summary,
        "tomorrow_plan": summary.tomorrow_plan,
        "date": summary.date
    }

# ==================== STRETCH FEATURES ====================

@app.post("/voice/extract")
def extract_tasks_from_voice(
    transcript: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from groq import Groq
    client = Groq(api_key=Config.GROQ_API_KEY)
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """
            Extract structured tasks from casual speech.
            Return JSON array with: description, category (work/personal/health/learning), 
            urgency (high/medium/low)
            """},
            {"role": "user", "content": transcript}
        ],
        temperature=0.1
    )
    
    try:
        tasks = json.loads(response.choices[0].message.content)
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks["tasks"]
        return {"tasks": tasks}
    except:
        return {"tasks": [{"description": transcript, "category": "work", "urgency": "medium"}]}

@app.post("/calendar/import")
def import_calendar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        with open("mock_calendar.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"message": "No calendar file found. Create mock_calendar.json", "count": 0}
    
    imported = 0
    for event in data.get("events", []):
        task = Task(
            user_id=current_user.id,
            description=event.get("summary", "Calendar event"),
            category=event.get("category", "work"),
            priority=event.get("priority", "medium"),
            due_date=datetime.fromisoformat(event.get("start", datetime.utcnow().isoformat())),
            created_at=datetime.utcnow()
        )
        db.add(task)
        imported += 1
    
    db.commit()
    return {"message": f"Imported {imported} calendar events", "count": imported}

@app.get("/streak/current")
def get_streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()
    if not streak:
        return {"current_streak": 0, "longest_streak": 0, "total_checkins": 0}
    
    return {
        "current_streak": streak.current_streak or 0,
        "longest_streak": streak.longest_streak or 0,
        "total_checkins": streak.total_checkins or 0
    }

@app.get("/streak/message")
def get_streak_message(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()
    
    if not streak or streak.current_streak < 3:
        return {"message": "Keep going! Consistency is key! 💪"}
    
    return {"message": f"🔥 {streak.current_streak} days! You're on fire! Keep it up!"}

# ==================== HEALTH CHECK ====================

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Productivity Agent is running!"}
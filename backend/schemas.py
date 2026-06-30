from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

# --- Task Schemas ---
class TaskCreate(BaseModel):
    description: str
    category: Optional[str] = "work"
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    completed: bool

class TaskResponse(BaseModel):
    id: int
    description: str
    category: str
    priority: str
    completed_at: Optional[datetime]
    due_date: Optional[datetime]

# --- Check-in Schemas ---
class MorningCheckin(BaseModel):
    tasks: List[str]

class EveningCheckin(BaseModel):
    completed_task_ids: List[int]
    notes: Optional[str] = ""

# --- Voice & Calendar Schemas ---
class VoiceExtract(BaseModel):
    transcript: str

class CalendarImportResponse(BaseModel):
    message: str
    count: int

# --- Streak Schemas ---
class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_checkins: int

# --- EOD Schemas ---
class EODSummaryResponse(BaseModel):
    summary: str
    tomorrow_plan: str
    date: datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    description = Column(String)
    category = Column(String, default="work")  # work/personal/health/learning
    priority = Column(String, default="medium")  # high/medium/low
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_overdue = Column(Boolean, default=False)
    estimated_minutes = Column(Integer, default=30)  # For focus timer
    actual_minutes = Column(Integer, default=0)  # Actual time spent

class DailyLog(Base):
    __tablename__ = "daily_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    morning_plan = Column(Text)
    evening_completions = Column(Text)
    notes = Column(Text)

class EODSummary(Base):
    __tablename__ = "eod_summaries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)
    tomorrow_plan = Column(Text)

class UserStreak(Base):
    __tablename__ = "user_streaks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_checkin_date = Column(DateTime, nullable=True)
    total_checkins = Column(Integer, default=0)

class FocusSession(Base):
    __tablename__ = "focus_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    completed = Column(Boolean, default=False)

class Habit(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    frequency = Column(String, default="daily")  # daily, weekly
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_check_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
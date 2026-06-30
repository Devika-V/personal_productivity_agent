import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Groq API
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # JWT
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prod.db")
    
    # Email (for reminders)
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
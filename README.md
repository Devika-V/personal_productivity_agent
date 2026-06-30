# Personal Productivity Agent

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.20+-1C3C6C.svg?style=flat&logo=langchain&logoColor=white)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-LLM-FF6B00.svg?style=flat&logo=groq&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **A stateful AI agent that remembers your tasks, classifies them intelligently, and helps you stay productive with a focus timer, habit tracking, and daily insights.**

---

## 📌 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**The Problem:** Most people don't have a productivity problem — they have a memory and prioritization problem. They forget what was due, how long things take, and end every day unsure if they got the important things done.

**The Solution:** A stateful AI agent you check in with twice daily. It remembers your history, surfaces patterns, classifies tasks, and generates personalized EOD summaries with tomorrow's plan.

### What Makes This Project Unique

| Aspect | Description |
|--------|-------------|
| **Stateful Memory** | LangGraph agent with SQLite checkpointer remembers context across sessions |
| **AI Classification** | Groq LLM categorizes tasks into 4 categories with urgency tags |
| **Focus Timer** | Pomodoro technique with time tracking and analytics |
| **Habit Tracker** | Gamification with streaks and milestones |
| **Voice Input** | Natural language task extraction via Web Speech API |

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **JWT Authentication** | Secure signup/login with bcrypt hashing |
| **Morning Check-in** | Log tasks with AI classification |
| **Evening Check-in** | Mark tasks complete and add notes |
| **EOD Summary** | AI-generated summary of what got done and what slipped |
| **Tomorrow's Plan** | Prioritized task list based on what slipped |
| **Streak Tracking** | Gamification to build daily habits |

### Advanced Features

| Feature | Description |
|---------|-------------|
| **Focus Timer** | Pomodoro technique with session tracking |
| **Habit Tracker** | Build daily habits with streaks and milestones |
| **AI Insights** | Weekly pattern analysis and recommendations |
| **Voice Input** | Natural language task entry via speech |
| **Weekly Review** | Automatic pattern detection every Sunday |

---

## Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| **Streamlit** | Interactive UI |
| **Requests** | HTTP client |

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **Python 3.10+** | Core language |

### AI & Agent
| Technology | Purpose |
|------------|---------|
| **LangGraph** | Stateful agent orchestration |
| **SqliteSaver** | Persistent agent memory |
| **Groq (llama-3.1-8b)** | Task classification |
| **Groq (llama-3.3-70b)** | EOD summaries |

### Database
| Technology | Purpose |
|------------|---------|
| **SQLAlchemy** | ORM |
| **SQLite** | Embedded database |

### Authentication & Scheduling
| Technology | Purpose |
|------------|---------|
| **PyJWT + bcrypt** | Authentication |
| **APScheduler** | Weekly reviews |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Groq API Key (free at [console.groq.com](https://console.groq.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/Devika-V/personal_productivity_agent.git
cd personal_productivity_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your GROQ_API_KEY to .env

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from .database import SessionLocal
from .models import Task, User, EODSummary

def run_weekly_review():
    """Run every Sunday at 9 AM"""
    db = SessionLocal()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    try:
        # Get all users
        users = db.query(User).all()
        
        for user in users:
            # Get incomplete tasks from last 7 days
            tasks = db.query(Task).filter(
                Task.user_id == user.id,
                Task.created_at >= week_ago,
                Task.completed_at.is_(None)
            ).all()
            
            # Group by category
            categories = {}
            for task in tasks:
                cat = task.category or "uncategorized"
                categories[cat] = categories.get(cat, 0) + 1
            
            # Generate review
            review = "📊 Weekly Review\n\n"
            if categories:
                for cat, count in categories.items():
                    review += f"- {cat}: {count} tasks unfinished\n"
                
                # Find patterns - tasks pushed repeatedly
                pushed_tasks = []
                for task in tasks:
                    if task.created_at.date() < datetime.utcnow().date():
                        pushed_tasks.append(task.description)
                
                if pushed_tasks:
                    review += f"\n⚠️ Tasks you've been pushing: {', '.join(pushed_tasks[:3])}"
            else:
                review += "✅ All tasks completed this week! Great job!"
            
            # Save review as EOD summary
            summary = EODSummary(
                user_id=user.id,
                summary=review,
                tomorrow_plan="Weekly review completed",
                date=datetime.utcnow()
            )
            db.add(summary)
        
        db.commit()
    except Exception as e:
        print(f"Weekly review error: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # Weekly review - Sunday 9 AM
    scheduler.add_job(
        run_weekly_review,
        CronTrigger(day_of_week="sun", hour=9, minute=0),
        id="weekly_review"
    )
    
    scheduler.start()
    print("✅ Scheduler started! Weekly reviews will run every Sunday at 9 AM")
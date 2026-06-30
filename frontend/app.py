import streamlit as st
import requests
import json
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Personal Productivity Agent",
    page_icon="✅",
    layout="wide"
)

# Constants
API_URL = "https://personal-productivity-agent-7vd6.onrender.com"

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "focus_session" not in st.session_state:
    st.session_state.focus_session = None

# ==================== AUTH FUNCTIONS ====================

def login():
    st.title("🔐 Login")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            response = requests.post(
                f"{API_URL}/auth/login",
                data={"username": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state.token = data["access_token"]
                st.session_state.user_id = 1
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

def signup():
    st.title("📝 Sign Up")
    
    with st.form("signup_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Sign Up")
        
        if submitted:
            if password != confirm:
                st.error("Passwords don't match")
            else:
                response = requests.post(
                    f"{API_URL}/auth/signup",
                    params={"email": email, "password": password}
                )
                if response.status_code == 200:
                    st.success("Account created! Please login.")
                else:
                    st.error("Email already exists")

# ==================== STREAK DISPLAY ====================

def show_streak_badge():
    if st.session_state.token:
        response = requests.get(
            f"{API_URL}/streak/current",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            data = response.json()
            if data["current_streak"] > 0:
                cols = st.columns([1, 1, 2])
                with cols[0]:
                    st.metric("🔥 Streak", data["current_streak"])
                with cols[1]:
                    st.metric("🏆 Best", data["longest_streak"])
                
                if data["current_streak"] >= 3:
                    msg_response = requests.get(
                        f"{API_URL}/streak/message",
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )
                    if msg_response.status_code == 200:
                        st.info(f"💬 {msg_response.json()['message']}")

# ==================== MAIN APP ====================

def main():
    # Check if user is logged in
    if not st.session_state.token:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            login()
        with tab2:
            signup()
        return
    
    # Sidebar
    st.sidebar.title("📋 Navigation")
    st.sidebar.markdown("---")
    
    view = st.sidebar.radio(
        "Choose View",
        [
            "🌅 Morning Check-in",
            "🌇 Evening Check-in",
            "📋 My Tasks",
            "⏱️ Focus Timer",
            "🔥 Habits",
            "📊 Insights",
            "📊 Profile"
        ]
    )
    
    st.sidebar.markdown("---")
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        st.session_state.token = None
        st.session_state.user_id = None
        st.rerun()
    
    # Route to selected view
    if view == "🌅 Morning Check-in":
        morning_checkin()
    elif view == "🌇 Evening Check-in":
        evening_checkin()
    elif view == "📋 My Tasks":
        show_tasks()
    elif view == "⏱️ Focus Timer":
        show_focus_timer()
    elif view == "🔥 Habits":
        show_habits()
    elif view == "📊 Insights":
        show_insights()
    elif view == "📊 Profile":
        show_profile()

# ==================== MORNING CHECK-IN ====================

def morning_checkin():
    st.header("🌅 Morning Check-in")
    st.markdown("---")
    
    # Show streak
    show_streak_badge()
    
    # Voice input (stretch)
    with st.expander("🎤 Voice Input (Beta - Chrome Only)"):
        st.info("Click 'Start Recording' and speak your tasks clearly")
        
        voice_text = st.text_area(
            "Your spoken text will appear here",
            placeholder="I need to finish the report, call mom, and go to the gym",
            key="voice_text",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎙️ Start Recording"):
                st.markdown("""
                <script>
                const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.lang = 'en-US';
                recognition.continuous = false;
                recognition.interimResults = false;
                
                recognition.onresult = function(event) {
                    const transcript = event.results[0][0].transcript;
                    document.getElementById('voice_result').value = transcript;
                    document.getElementById('voice_status').innerHTML = '✅ Captured!';
                };
                
                recognition.onerror = function(event) {
                    document.getElementById('voice_status').innerHTML = '❌ Error: ' + event.error;
                };
                
                recognition.start();
                document.getElementById('voice_status').innerHTML = '🎤 Listening...';
                </script>
                
                <input id="voice_result" style="width:100%; padding:10px; margin:10px 0;" 
                       placeholder="Your spoken text will appear here...">
                <div id="voice_status" style="font-weight:bold;"></div>
                """, unsafe_allow_html=True)
        
        with col2:
            if st.button("✨ Extract Tasks with AI") and voice_text:
                response = requests.post(
                    f"{API_URL}/voice/extract",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    json={"transcript": voice_text}
                )
                if response.status_code == 200:
                    tasks = response.json()["tasks"]
                    st.success(f"✅ Extracted {len(tasks)} tasks!")
                    for t in tasks:
                        st.write(f"• {t['description']} [{t['category']}] {t['urgency']}")
    
    # Regular task entry
    st.subheader("📝 What are you planning today?")
    
    with st.form("morning_form"):
        tasks_text = st.text_area(
            "Enter one task per line",
            placeholder="Finish quarterly report\nCall mom\nGo to gym\nStudy Python",
            height=150
        )
        
        submitted = st.form_submit_button("💾 Save Plan", use_container_width=True)
        
        if submitted and tasks_text:
            tasks = [t.strip() for t in tasks_text.split("\n") if t.strip()]
            
            response = requests.post(
                f"{API_URL}/checkin/morning",
                headers={
                    "Authorization": f"Bearer {st.session_state.token}",
                    "Content-Type": "application/json"
                },
                json={"tasks": tasks}
            )
            
            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ Saved {data['tasks_saved']} tasks!")
                
                # Show classification results
                st.subheader("📊 Task Classification")
                for task in data.get("tasks", []):
                    color = "🔴" if task.get("urgency") == "high" else "🟡" if task.get("urgency") == "medium" else "🟢"
                    st.write(f"{color} {task['description']} → {task.get('category', 'work')} ({task.get('urgency', 'medium')})")
                
                st.info(f"🔥 Streak: {data['streak']} days!")
                st.rerun()
            else:
                st.error("Failed to save tasks")

# ==================== EVENING CHECK-IN ====================

def evening_checkin():
    st.header("🌇 Evening Check-in")
    st.markdown("---")
    
    # Get today's tasks
    response = requests.get(
        f"{API_URL}/tasks/today",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if response.status_code != 200:
        st.error("Failed to load tasks")
        return
    
    tasks = response.json().get("tasks", [])
    
    if not tasks:
        st.info("No tasks for today. Complete your morning check-in first!")
        return
    
    # Show incomplete tasks
    incomplete_tasks = [t for t in tasks if not t.get("completed")]
    
    if not incomplete_tasks:
        st.success("🎉 All tasks completed! Great job!")
    else:
        st.subheader(f"📋 {len(incomplete_tasks)} tasks remaining")
        
        with st.form("evening_form"):
            completed_ids = []
            
            for task in incomplete_tasks:
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    checked = st.checkbox(
                        "Complete",
                        key=f"task_{task['id']}",
                        label_visibility="collapsed"
                    )
                with col2:
                    urgency_emoji = "🔴" if task.get("priority") == "high" else "🟡" if task.get("priority") == "medium" else "🟢"
                    st.write(f"{urgency_emoji} {task['description']}")
                with col3:
                    st.caption(f"📂 {task.get('category', 'work')}")
                
                if checked:
                    completed_ids.append(task['id'])
            
            notes = st.text_area(
                "Any notes?",
                placeholder="Had to pivot to urgent client request...",
                height=100
            )
            
            submitted = st.form_submit_button("✅ Complete Evening Check-in", use_container_width=True)
            
            if submitted:
                if not completed_ids:
                    st.warning("Please select at least one task to complete")
                else:
                    response = requests.post(
                        f"{API_URL}/checkin/evening",
                        headers={
                            "Authorization": f"Bearer {st.session_state.token}",
                            "Content-Type": "application/json"
                        },
                        params={"notes": notes},
                        json=completed_ids
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Completed {data['completed']} tasks!")
                        
                        # Run EOD
                        eod_response = requests.post(
                            f"{API_URL}/eod/run",
                            headers={"Authorization": f"Bearer {st.session_state.token}"}
                        )
                        
                        if eod_response.status_code == 200:
                            data = eod_response.json()
                            st.subheader("📄 EOD Summary")
                            st.write(data.get("summary", "No summary generated"))
                            
                            st.subheader("📅 Tomorrow's Plan")
                            st.write(data.get("tomorrow_plan", "No plan generated"))
                            
                            if data.get("overdue"):
                                st.warning(f"⚠️ {len(data['overdue'])} overdue tasks detected!")
                        else:
                            st.error("Failed to generate EOD summary")
                        
                        st.rerun()
                    else:
                        st.error(f"Failed to save evening check-in: {response.status_code}")

# ==================== TASKS VIEW ====================

def show_tasks():
    st.header("📋 My Tasks")
    st.markdown("---")
    
    response = requests.get(
        f"{API_URL}/tasks/today",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if response.status_code != 200:
        st.error("Failed to load tasks")
        return
    
    tasks = response.json().get("tasks", [])
    
    if not tasks:
        st.info("No tasks found. Start with a morning check-in!")
        return
    
    # Filter options
    filter_by = st.selectbox("Filter by", ["All", "Work", "Personal", "Health", "Learning"])
    
    filtered_tasks = tasks
    if filter_by != "All":
        filtered_tasks = [t for t in tasks if t.get("category", "").lower() == filter_by.lower()]
    
    # Group by urgency
    st.subheader("📊 Task Board")
    
    urgency_order = {"high": 0, "medium": 1, "low": 2}
    sorted_tasks = sorted(filtered_tasks, key=lambda t: urgency_order.get(t.get("priority", "medium"), 1))
    
    for task in sorted_tasks:
        col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
        
        with col1:
            if task.get("completed"):
                st.write("✅")
            else:
                st.write("⬜")
        
        with col2:
            urgency_emoji = "🔴" if task.get("priority") == "high" else "🟡" if task.get("priority") == "medium" else "🟢"
            st.write(f"{urgency_emoji} {task['description']}")
        
        with col3:
            st.caption(f"📂 {task.get('category', 'work')}")
        
        with col4:
            if task.get("completed"):
                st.caption("✅ Done")
            else:
                st.caption("⏳ Pending")

# ==================== FOCUS TIMER ====================

def show_focus_timer():
    st.header("⏱️ Focus Timer")
    st.markdown("---")
    
    # Get today's tasks
    response = requests.get(
        f"{API_URL}/tasks/today",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if response.status_code != 200:
        st.error("Failed to load tasks")
        return
    
    tasks = response.json().get("tasks", [])
    incomplete = [t for t in tasks if not t.get("completed")]
    
    # Show focus session if active
    if st.session_state.focus_session:
        st.subheader("🎯 Current Focus Session")
        st.info(f"📌 Task: **{st.session_state.focus_session.get('task', 'Unknown')}**")
        st.info(f"⏱️ Duration: **{st.session_state.focus_session.get('duration', 25)} minutes**")
        st.warning("⏳ Timer is running! Focus on your task.")
        
        # ✅ End Session button - NOW BELOW the info
        if st.button("⏹️ End Session", use_container_width=True):
            session_id = st.session_state.focus_session.get("session_id")
            response = requests.post(
                f"{API_URL}/focus/end/{session_id}",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            if response.status_code == 200:
                data = response.json()
                st.success(data["message"])
                st.balloons()
                st.session_state.focus_session = None
                st.rerun()
            else:
                st.error("Failed to end session")
        
        st.markdown("---")
    
    # Show task selection (only if no active session)
    else:
        if incomplete:
            task_options = {f"{t['description']}": t['id'] for t in incomplete}
            selected = st.selectbox("🎯 Select task to focus on:", list(task_options.keys()))
            task_id = task_options[selected]
            
            duration = st.slider("⏱️ Focus duration (minutes):", 5, 60, 25)
            
            if st.button("▶️ Start Focus Session", use_container_width=True):
                response = requests.post(
                    f"{API_URL}/focus/start/{task_id}",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    params={"duration": duration}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success(data["message"])
                    st.session_state.focus_session = data
                    st.rerun()
                else:
                    st.error("Failed to start focus session")
        else:
            st.info("No incomplete tasks. Complete your morning check-in first!")
    
    st.markdown("---")
    
    # Show focus stats
    st.subheader("📊 Your Focus Stats")
    stats = requests.get(
        f"{API_URL}/focus/stats",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if stats.status_code == 200:
        data = stats.json()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Today's Focus", f"{data['today_minutes']} min")
        with col2:
            st.metric("This Week", f"{data['week_minutes']} min")
        with col3:
            st.metric("Best Task", data.get('best_task', 'None')[:15] if data.get('best_task') else 'None')
# ==================== HABITS ====================

def show_habits():
    st.header("🔥 Habit Tracker")
    st.markdown("---")
    
    # Create new habit
    with st.expander("➕ Create New Habit"):
        with st.form("habit_form"):
            habit_name = st.text_input("Habit name:", placeholder="Gym, Reading, Meditation...")
            frequency = st.selectbox("Frequency:", ["daily", "weekly"])
            
            if st.form_submit_button("Create Habit"):
                response = requests.post(
                    f"{API_URL}/habits/create",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    params={"name": habit_name, "frequency": frequency}
                )
                if response.status_code == 200:
                    st.success(response.json()["message"])
                    st.rerun()
                else:
                    st.error("Failed to create habit")
    
    # List habits
    response = requests.get(
        f"{API_URL}/habits/list",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if response.status_code == 200:
        habits = response.json().get("habits", [])
        
        if not habits:
            st.info("No habits yet. Create your first habit above!")
            return
        
        for habit in habits:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{habit['name']}**")
            with col2:
                st.write(f"🔥 {habit['current_streak']} days")
            with col3:
                if st.button("✅ Check-in", key=f"habit_{habit['id']}"):
                    response = requests.post(
                        f"{API_URL}/habits/check/{habit['id']}",
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.success(data["message"])
                        st.rerun()
                    else:
                        st.error("Failed to check in")

# ==================== INSIGHTS ====================

def show_insights():
    st.header("📊 AI-Powered Insights")
    st.markdown("---")
    
    if st.button("🔄 Generate Weekly Insights", use_container_width=True):
        with st.spinner("Generating insights..."):
            response = requests.get(
                f"{API_URL}/insights/weekly",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tasks Completed", data["stats"]["tasks_completed"])
                with col2:
                    st.metric("Focus Minutes", data["stats"]["total_focus_minutes"])
                with col3:
                    st.metric("Active Habits", data["stats"]["active_habits"])
                
                st.subheader("📝 Weekly Summary")
                st.info(data["summary"])
                
                st.subheader("📅 Tomorrow's Recommendation")
                st.success(data["recommendation"])
            else:
                st.error("Failed to generate insights")

# ==================== PROFILE ====================

def show_profile():
    st.header("📊 Profile")
    st.markdown("---")
    
    # Streak info
    show_streak_badge()
    
    st.markdown("---")
    
    # Features status
    st.subheader("🚀 Features")
    
    features = {
        "Morning Check-in": "✅",
        "Evening Check-in": "✅",
        "Task Classification": "✅",
        "EOD Summary": "✅",
        "Focus Timer": "✅ NEW!",
        "Habit Tracker": "✅ NEW!",
        "AI Insights": "✅ NEW!",
        "Voice Input": "✅ (Beta)",
        "Streak Tracking": "✅"
    }
    
    for feature, status in features.items():
        st.write(f"{status} {feature}")
    
    st.markdown("---")
    
    # Stats placeholder
    st.subheader("📈 Your Stats")
    st.info("Keep using the app daily to build streaks and track progress!")

# ==================== RUN APP ====================

if __name__ == "__main__":
    main()
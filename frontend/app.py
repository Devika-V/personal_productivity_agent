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
API_URL = "http://localhost:8000"

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "tasks" not in st.session_state:
    st.session_state.tasks = []

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
                st.session_state.user_id = 1  # For demo - you'd decode JWT
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
        ["🌅 Morning Check-in", "🌇 Evening Check-in", "📋 My Tasks", "📅 This Week", "📊 Profile"]
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
    elif view == "📅 This Week":
        show_week()
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
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Save Plan", use_container_width=True)
        with col2:
            # Calendar import button
            if st.form_submit_button("📅 Import Calendar", use_container_width=True):
                response = requests.post(
                    f"{API_URL}/calendar/import",
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if response.status_code == 200:
                    st.success(response.json()["message"])
                else:
                    st.error("Failed to import calendar")
        
        if submitted and tasks_text:
            tasks = [t.strip() for t in tasks_text.split("\n") if t.strip()]
            
            response = requests.post(
                f"{API_URL}/checkin/morning",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
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
        return
    
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
                # =============================================
                # 🔍 DEBUG CODE STARTS HERE
                # =============================================
                st.write("🔍 Debug - Task IDs:", completed_ids)
                st.write("🔍 Debug - Notes:", notes)
                # =============================================
                
                response = requests.post(
                    f"{API_URL}/checkin/evening",
                    headers={
                        "Authorization": f"Bearer {st.session_state.token}",
                        "Content-Type": "application/json"
                    },
                    params={"notes": notes},
                    json=completed_ids
                )
                
                # =============================================
                # 🔍 DEBUG CODE CONTINUES
                # =============================================
                st.write("🔍 Debug - Status Code:", response.status_code)
                st.write("🔍 Debug - Response Text:", response.text)
                # =============================================
                
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

# ==================== THIS WEEK VIEW ====================

def show_week():
    st.header("📅 This Week")
    st.markdown("---")
    
    # Get last 7 days
    today = datetime.now()
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%A, %B %d")
        
        with st.expander(f"📆 {date_str}"):
            # Get tasks for this date
            st.write("Loading tasks for this day...")
            st.caption("(This feature would show tasks and summaries for each day)")
            
            # In a full implementation, you'd query tasks by date
            # For now, show a placeholder
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tasks Planned", "0")
            with col2:
                st.metric("Completed", "0")
            with col3:
                st.metric("Pending", "0")

# ==================== PROFILE VIEW ====================

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
        "Voice Input": "✅ (Beta)",
        "Calendar Import": "✅",
        "Streak Tracking": "✅",
        "Weekly Review": "✅ (Sundays)"
    }
    
    for feature, status in features.items():
        st.write(f"{status} {feature}")
    
    st.markdown("---")
    
    # Stats placeholder
    st.subheader("📈 Your Stats")
    st.info("More detailed statistics coming soon!")

# ==================== RUN APP ====================

if __name__ == "__main__":
    main()
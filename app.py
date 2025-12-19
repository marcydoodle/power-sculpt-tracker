import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Page Config MUST be the very first Streamlit command
st.set_page_config(page_title="Power-Sculpt Pro", page_icon="🍑")

# 2. Database Connection with Error Handling
def init_db():
    try:
        conn = sqlite3.connect('power_sculpt_v2.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (date TEXT, exercise TEXT, weight REAL, reps INT, rpe REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS silhouette 
                     (date TEXT, waist REAL, hips REAL, thigh REAL, body_weight REAL)''')
        conn.commit()
        return conn
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None

conn = init_db()

# 3. Simple Visual Header to confirm app is live
st.title("🏋️ Power-Sculpt Pro")
if conn:
    st.success("✅ System Online & Database Connected")
else:
    st.warning("⚠️ System Offline: Check Logs")

# 4. Navigation
menu = st.sidebar.radio("Go To", ["Today's Lift", "Silhouette Tracker", "Analytics"])

# 5. Routine Dictionary
day_name = datetime.now().strftime("%A")
routines = {
    "Monday": ["Back Squat", "Barbell Hip Thrust", "Barbell RDL", "Ab Wheel"],
    "Tuesday": ["Bench Press", "Walking Lunge", "Dumbbell Row", "Machine Hip Abduction"],
    "Wednesday": ["Deadlift", "Barbell Hip Thrust", "Rear Lunge", "Ab Wheel"],
    "Thursday": ["Weighted Rear Lunge", "Machine Hip Abduction", "Ab Wheel"],
    "Friday": ["Dumbbell Overhead Press", "Walking Lunge", "Ab Wheel"],
    "Saturday": ["Barbell Hip Thrust", "Deficit Rear Lunge", "Machine Hip Abduction"],
    "Sunday": ["Rest Day"]
}

# 6. Logging Logic
if menu == "Today's Lift":
    st.subheader(f"Schedule: {day_name}")
    moves = routines.get(day_name, ["Rest Day"])
    ex = st.selectbox("Select Movement", moves)
    
    with st.form("log_set", clear_on_submit=True):
        w = st.number_input("Weight (lbs)", value=100.0, step=2.5)
        r = st.number_input("Reps", value=8, step=1)
        rpe = st.slider("RPE", 1.0, 10.0, 7.5, 0.5)
        
        if st.form_submit_button("Record Set"):
            c = conn.cursor()
            c.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                      (datetime.now().strftime("%Y-%m-%d"), ex, w, r, rpe))
            conn.commit()
            st.toast(f"Logged {ex}!")

elif menu == "Silhouette Tracker":
    st.subheader("Body Progress")
    with st.form("sil_form"):
        waist = st.number_input("Waist (in)", step=0.1)
        hips = st.number_input("Hips (in)", step=0.1)
        if st.form_submit_button("Save"):
            c = conn.cursor()
            c.execute("INSERT INTO silhouette VALUES (?,?,?,?,0)", 
                      (datetime.now().strftime("%Y-%m-%d"), waist, hips))
            conn.commit()
            st.success("Saved!")

elif menu == "Analytics":
    st.subheader("History")
    history = pd.read_sql("SELECT * FROM logs ORDER BY date DESC LIMIT 10", conn)
    if not history.empty:
        st.dataframe(history)
    else:
        st.info("No logs yet. Start training!")
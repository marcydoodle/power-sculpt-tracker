import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. PAGE CONFIG
st.set_page_config(page_title="Power-Sculpt Pro", page_icon="🍑")

# 2. DATABASE WITH THREAD SAFETY
def init_db():
    conn = sqlite3.connect('power_sculpt_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (date TEXT, exercise TEXT, weight REAL, reps INT, rpe REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS silhouette 
                 (date TEXT, waist REAL, hips REAL, thigh REAL, body_weight REAL)''')
    conn.commit()
    return conn

conn = init_db()

# 3. THE PROGRESSION BRAIN
def get_target(exercise):
    # This looks at your LAST logged set for this specific movement
    query = f"SELECT weight, rpe FROM logs WHERE exercise='{exercise}' ORDER BY date DESC LIMIT 1"
    last_log = pd.read_sql(query, conn)
    
    # Starting Weights for Phase 1 (Week 1)
    defaults = {
        'Back Squat': 160.0, 'Barbell Hip Thrust': 200.0, 
        'Bench Press': 115.0, 'Deadlift': 210.0, 'Barbell RDL': 135.0
    }
    
    if last_log.empty:
        return defaults.get(exercise, 45.0) # Default to 45 if not in list
    
    last_w = last_log.iloc[0]['weight']
    last_rpe = last_log.iloc[0]['rpe']
    
    # Automated Progression Logic
    if last_rpe <= 7.0:
        return last_w + 5.0    # Felt light? Add 5lbs
    elif last_rpe <= 9.0:
        return last_w + 2.5    # Perfect? Add 2.5lbs
    else:
        return last_w          # Grinding? Master this weight first

# 4. NAVIGATION & SIDEBAR
st.sidebar.title("Power-Sculpt Pro")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Silhouette Tracker", "Analytics"])

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

# 5. PAGE: TODAY'S LIFT
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    
    # 1. Define the substitutions dictionary
    subs = {
        "Back Squat": ["Back Squat", "Hack Squat", "Leg Press", "Hack Squat"],
        "Barbell Hip Thrust": ["Barbell Hip Thrust", "DB Hip Thrust", "Glute Bridge"],
        "Deadlift": ["Deadlift", "Sumo Deadlift", "Trap Bar Deadlift", "DB RDL"],
        "Bench Press": ["Bench Press", "DB Chest Press", "Incline DB Press"],
        "Walking Lunge": ["Walking Lunge", "Split Squat", "Step Ups"],
        "Barbell RDL": ["Barbell RDL", "DB RDL", "Cable Pull-through"]
    }

    moves = routines.get(day_name, ["Rest Day"])
    
    if "Rest Day" in moves:
        st.write("Recovery day! Focus on steps and hydration.")
    else:
        # 2. Select the scheduled movement
        scheduled_move = st.selectbox("Scheduled Movement", moves)
        
        # 3. Check if we need to swap
        if scheduled_move in subs:
            ex = st.selectbox("Exercise (Select variant if swapping):", subs[scheduled_move])
        else:
            ex = scheduled_move # For accessories without subs like Ab Wheel
            
        target_w = get_target(ex)
        st.metric(label=f"Target for {ex}", value=f"{target_w} lbs")
        
        with st.form("log_set", clear_on_submit=True):
            col1, col2 = st.columns(2)
            w_input = col1.number_input("Weight (lbs)", value=float(target_w), step=2.5)
            r_input = col2.number_input("Reps", value=8, step=1)
            rpe_input = st.select_slider("RPE", options=[5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10])
            
            if st.form_submit_button("Record Set"):
                c = conn.cursor()
                c.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                          (datetime.now().strftime("%Y-%m-%d"), ex, w_input, r_input, rpe_input))
                conn.commit()
                st.success(f"Logged {ex} at {w_input}lbs!")
# 6. PAGE: SILHOUETTE
elif menu == "Silhouette Tracker":
    st.title("⏳ Silhouette Tracker")
    with st.form("sil_form"):
        waist = st.number_input("Waist (inches)", step=0.1)
        hips = st.number_input("Hips (inches)", step=0.1)
        if st.form_submit_button("Log Measurements"):
            c = conn.cursor()
            c.execute("INSERT INTO silhouette VALUES (?,?,?,?,0)", 
                      (datetime.now().strftime("%Y-%m-%d"), waist, hips, 0))
            conn.commit()
            st.success("Measurements saved.")

# 7. PAGE: ANALYTICS
elif menu == "Analytics":
    st.title("📊 Progress Data")   
    df_logs = pd.read_sql("SELECT * FROM logs", conn)
    if not df_logs.empty:
        # Strength Chart
        df_logs['e1rm'] = df_logs['weight'] * (1 + df_logs['reps'] / 30.0)
        st.subheader("Strength Trend (e1RM)")
        st.line_chart(df_logs, x='date', y='e1rm', color='exercise')
        
        # Backup Button
        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Backup (CSV)", data=csv, file_name='my_training_data.csv')

        # Undo Button
        if st.button("🗑️ Delete Last Log Entry"):
            c = conn.cursor()
            c.execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)")
            conn.commit()
            st.warning("Last entry deleted. Refresh the page to update charts.")
    
    # Strength Chart
    df_logs = pd.read_sql("SELECT * FROM logs", conn)
    if not df_logs.empty:
        # Calculate e1RM for the chart
        df_logs['e1rm'] = df_logs['weight'] * (1 + df_logs['reps'] / 30.0)
        st.subheader("Strength Trend (e1RM)")
        st.line_chart(df_logs, x='date', y='e1rm', color='exercise')
        
        st.subheader("Recent History")
        st.dataframe(df_logs.tail(10))



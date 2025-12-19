import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Power-Sculpt Pro", page_icon="🍑", layout="centered")

# --- 2. DATABASE CONFIG ---
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

# --- 3. PROGRESSION ENGINE ---
def get_target(exercise):
    query = f"SELECT weight, rpe FROM logs WHERE exercise='{exercise}' ORDER BY date DESC LIMIT 1"
    last_log = pd.read_sql(query, conn)
    
    defaults = {
        'Back Squat': 160.0, 'Barbell Hip Thrust': 200.0, 
        'Bench Press': 115.0, 'Deadlift': 210.0, 'Barbell RDL': 135.0
    }
    
    if last_log.empty:
        return defaults.get(exercise, 45.0)
    
    last_w, last_rpe = last_log.iloc[0]['weight'], last_log.iloc[0]['rpe']
    
    if last_rpe <= 7.0: return last_w + 5.0
    elif last_rpe <= 9.0: return last_w + 2.5
    else: return last_w

# --- 4. DATA & ROUTINES ---
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

subs = {
    "Back Squat": ["Back Squat", "Goblet Squat", "Hack Squat"],
    "Barbell Hip Thrust": ["Barbell Hip Thrust", "DB Hip Thrust", "Glute Bridge"],
    "Deadlift": ["Deadlift", "Sumo Deadlift", "Trap Bar Deadlift", "DB RDL"],
    "Bench Press": ["Bench Press", "DB Chest Press", "Incline DB Press"],
    "Walking Lunge": ["Walking Lunge", "Split Squat", "Step Ups"],
    "Barbell RDL": ["Barbell RDL", "DB RDL", "Cable Pull-through"]
}

# --- 5. NAVIGATION ---
st.sidebar.title("Power-Sculpt v2")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Silhouette Tracker", "Analytics"])

# --- 6. PAGE: TODAY'S LIFT ---
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    
    moves = routines.get(day_name, ["Rest Day"])
    display_moves = moves + ["+ Add Extra Exercise"]
    scheduled_move = st.selectbox("Select Movement", display_moves)
    
    # Custom vs Swap Logic
    if scheduled_move == "+ Add Extra Exercise":
        ex = st.text_input("Exercise Name:")
    elif scheduled_move in subs:
        ex = st.selectbox("Exercise Variant:", subs[scheduled_move])
    else:
        ex = scheduled_move

    if ex and scheduled_move != "Rest Day":
        target_w = get_target(ex)
        st.metric(label=f"Target Weight", value=f"{target_w} lbs")
        
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
                st.toast(f"Logged {ex}!")

    # --- LIVE SESSION SUMMARY ---
    st.markdown("---")
    st.subheader("📝 Session Summary")
    today_str = datetime.now().strftime("%Y-%m-%d")
    summary_df = pd.read_sql(f"SELECT exercise, weight, reps, rpe FROM logs WHERE date='{today_str}'", conn)
    
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True)
        # Calculate total volume for motivation
        total_vol = (summary_df['weight'] * summary_df['reps']).sum()
        st.caption(f"Total Work Volume Today: {total_vol:,.0f} lbs")
    else:
        st.info("No sets logged yet for today.")

# --- 7. PAGE: SILHOUETTE ---
elif menu == "Silhouette Tracker":
    st.title("⏳ Silhouette Metrics")
    with st.form("sil_form"):
        waist = st.number_input("Waist (inches)", step=0.1)
        hips = st.number_input("Hips (inches)", step=0.1)
        if st.form_submit_button("Save Measurements"):
            c = conn.cursor()
            c.execute("INSERT INTO silhouette VALUES (?,?,?,?,0)", (datetime.now().strftime("%Y-%m-%d"), waist, hips, 0))
            conn.commit()
            st.success("Saved!")

# --- 8. PAGE: ANALYTICS ---
elif menu == "Analytics":
    st.title("📊 Progress Insights")
    df_logs = pd.read_sql("SELECT * FROM logs", conn)
    if not df_logs.empty:
        df_logs['e1rm'] = df_logs['weight'] * (1 + df_logs['reps'] / 30.0)
        st.subheader("Strength Trend (e1RM)")
        st.line_chart(df_logs, x='date', y='e1rm', color='exercise')
        
        st.subheader("History & Backup")
        st.dataframe(df_logs)
        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV Backup", data=csv, file_name='training_data.csv')
        
        if st.button("🗑️ Delete Last Entry"):
            conn.cursor().execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)")
            conn.commit()
            st.rerun()

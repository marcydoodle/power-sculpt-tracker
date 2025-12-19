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

# --- 4. NAVIGATION ---
st.sidebar.title("Power-Sculpt v2")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Program Roadmap", "Silhouette Tracker", "Analytics"])

# ... (keep your routines and subs dictionaries as they are) ...
# --- NEW PAGE: PROGRAM ROADMAP ---
if menu == "Program Roadmap":
    st.title("🗓️ 16-Week Program Roadmap")
    
    # 1. Phase Logic
    start_date = datetime(2025, 12, 19)
    days_in = (datetime.now() - start_date).days
    week_num = max(1, (days_in // 7) + 1)
    
    # Determine Rep Ranges based on Phase
    if week_num <= 4:
        phase_goal = "Phase 1: Hypertrophy & Form"
        rep_range = "3 Sets x 10-12 Reps"
    elif week_num <= 12:
        phase_goal = "Phase 2: Strength Construction"
        rep_range = "3 Sets x 6-8 Reps"
    else:
        phase_goal = "Phase 3: Peaking & Power"
        rep_range = "4 Sets x 3-5 Reps"

    st.subheader(f"📅 {phase_goal} (Week {week_num}/16)")
    st.progress(min(week_num / 16, 1.0))
    
    # 2. Get All-Time Maxes for PR Stars
    pr_query = "SELECT exercise, MAX(weight) as max_w FROM logs GROUP BY exercise"
    df_prs = pd.read_sql(pr_query, conn)
    pr_dict = dict(zip(df_prs['exercise'], df_prs['max_w']))

    # 3. Display Weekly Split with Sets/Reps
    st.write(f"Standard Volume for this phase: **{rep_range}**")
    
    col1, col2 = st.columns(2)
    days = list(routines.keys())
    
    for i, day in enumerate(days):
        with col1 if i % 2 == 0 else col2:
            is_today = (day == day_name)
            with st.expander(f"**{day}**", expanded=is_today):
                moves = routines[day]
                if "Rest Day" in moves:
                    st.write("🧘 *Active Recovery*")
                else:
                    for m in moves:
                        current_weight = get_target(m)
                        all_time_max = pr_dict.get(m, 0)
                        
                        # Icon logic: PR Star or Standard Bullet
                        icon = "🔥" if (all_time_max > 0 and current_weight >= all_time_max) else "🔹"
                        
                        st.write(f"{icon} **{m}**")
                        st.caption(f"Target: {current_weight} lbs | {rep_range}")
                        
    st.markdown("---")
    st.info("💡 Note: For 'Ab Wheel' and bodyweight moves, focus on maximum controlled reps.")
# --- (The rest of your Today's Lift, Silhouette, and Analytics logic) ---
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

    # --- LIVE SESSION SUMMARY & SET TRACKING ---
    st.markdown("---")
    today_str = datetime.now().strftime("%Y-%m-%d")
    # This pulls only the sets you've done TODAY for the selected exercise
    session_data = pd.read_sql(f"SELECT weight, reps, rpe FROM logs WHERE date='{today_str}' AND exercise='{ex}'", conn)
    
    if not session_data.empty:
        set_count = len(session_data)
        st.subheader(f"✅ {ex} Progress: {set_count} Sets Done")
        
        # Displaying sets in a clean, numbered table
        session_data.index = [f"Set {i+1}" for i in range(len(session_data))]
        st.table(session_data) 
        
        # Volume calculation for that specific exercise
        ex_vol = (session_data['weight'] * session_data['reps']).sum()
        st.caption(f"Current {ex} Volume: {ex_vol:,.0f} lbs")
    else:
        st.info(f"Ready for Set 1 of {ex}?")

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





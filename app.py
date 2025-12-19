
import streamlit as st
import pandas as pd
from datetime import datetime

# HYBRID CONNECTION LOGIC
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    mode = "cloud"
except Exception:
    import sqlite3
    conn = sqlite3.connect('power_sculpt_v2.db', check_same_thread=False)
    mode = "local"
    st.sidebar.warning("⚠️ Running in Local Mode (GSheets disconnected)")

# Now your app won't crash!
st.title("Power-Sculpt Tracker")
st.caption(f"Storage Mode: {mode}")
# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Power-Sculpt Pro", page_icon="🍑")

import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --- DATABASE CONFIG (Google Sheets Version) ---
# Ensure you have set up the "Connections" in Streamlit Cloud Dashboard!
conn = st.connection("gsheets", type=GSheetsConnection)

def get_all_data():
    return conn.read(worksheet="logs", ttl="0")

def save_log(new_row):
    # Fetch existing data
    existing_data = conn.read(worksheet="logs", ttl="0")
    # Add new row
    updated_df = pd.concat([existing_data, pd.DataFrame([new_row])], ignore_index=True)
    # Write back to Google Sheets
    conn.update(worksheet="logs", data=updated_df)
# --- 3. PROGRESSION & PHASE LOGIC ---
def get_phase_info():
    start_date = datetime(2025, 12, 19)
    days_in = (datetime.now() - start_date).days
    week_num = max(1, (days_in // 7) + 1)
    
    if week_num <= 4:
        return week_num, "Phase 1: Hypertrophy", "3 Sets x 10-12 Reps"
    elif week_num <= 12:
        return week_num, "Phase 2: Strength", "3 Sets x 6-8 Reps"
    else:
        return week_num, "Phase 3: Peaking", "4 Sets x 3-5 Reps"

def get_target(exercise):
    query = f"SELECT weight, rpe FROM logs WHERE exercise='{exercise}' ORDER BY date DESC LIMIT 1"
    last_log = pd.read_sql(query, conn)
    defaults = {'Back Squat': 160.0, 'Barbell Hip Thrust': 200.0, 'Bench Press': 115.0, 'Deadlift': 210.0, 'Barbell RDL': 135.0}
    if last_log.empty: return defaults.get(exercise, 45.0)
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
    "Back Squat": ["Back Squat", "Goblet Squat", "Leg Press"],
    "Barbell Hip Thrust": ["Barbell Hip Thrust", "DB Hip Thrust", "Glute Bridge"],
    "Deadlift": ["Deadlift", "Sumo Deadlift", "Trap Bar Deadlift"],
    "Bench Press": ["Bench Press", "DB Chest Press"],
    "Walking Lunge": ["Walking Lunge", "Split Squat", "Step Ups"]
}

# --- 5. NAVIGATION ---
st.sidebar.title("Power-Sculpt v2")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Program Roadmap", "Silhouette Tracker", "Analytics"])
week_num, phase_name, rep_goal = get_phase_info()

# --- 6. PAGE: TODAY'S LIFT ---
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    st.subheader(f"{phase_name} | Goal: {rep_goal}")
    
    moves = routines.get(day_name, ["Rest Day"])
    display_moves = moves + ["+ Add Extra Exercise"]
    scheduled_move = st.selectbox("Select Movement", display_moves)
    
    if scheduled_move == "+ Add Extra Exercise":
        ex = st.text_input("Exercise Name:")
    elif scheduled_move in subs:
        ex = st.selectbox("Exercise Variant:", subs[scheduled_move])
    else:
        ex = scheduled_move

    if ex and scheduled_move != "Rest Day":
        target_w = get_target(ex)
        
        # Displaying Goals clearly
        col_a, col_b = st.columns(2)
        col_a.metric("Target Weight", f"{target_w} lbs")
        col_b.metric("Rep Goal", rep_goal.split('x')[1].strip())
        
        with st.form("log_set", clear_on_submit=True):
            c1, c2 = st.columns(2)
            w_input = c1.number_input("Weight (lbs)", value=float(target_w), step=2.5)
            r_input = c2.number_input("Reps", value=10, step=1)
            rpe_input = st.select_slider("RPE", options=[5, 6, 7, 7.5, 8, 8.5, 9, 9.5, 10])
            if st.form_submit_button("Record Set"):
                conn.cursor().execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                                      (datetime.now().strftime("%Y-%m-%d"), ex, w_input, r_input, rpe_input))
                conn.commit()
                st.toast(f"Logged {ex}!")

    # Live Summary
    st.markdown("---")
    today_str = datetime.now().strftime("%Y-%m-%d")
    summary_df = pd.read_sql(f"SELECT exercise, weight, reps, rpe FROM logs WHERE date='{today_str}'", conn)
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True)

# --- 7. PAGE: PROGRAM ROADMAP ---
elif menu == "Program Roadmap":
    st.title("🗓️ 16-Week Roadmap")
    st.markdown(f"### **Week {week_num} of 16**")
    st.progress(week_num / 16)
    st.info(f"**Current Target:** {rep_goal}")

    days = list(routines.keys())
    for i, day in enumerate(days):
        is_today = (day == day_name)
        with st.expander(f"**{day}**", expanded=is_today):
            day_moves = routines[day]
            if "Rest Day" in day_moves:
                st.write("🧘 Active Recovery")
            else:
                for m in day_moves:
                    # Boldly showing the Sets/Reps next to the name
                    st.write(f"🔹 **{m}** — *{rep_goal}*")

# --- 8. ANALYTICS & SILHOUETTE (Keeping same logic) ---
elif menu == "Silhouette Tracker":
    st.title("⏳ Metrics")
    with st.form("sil_form"):
        waist = st.number_input("Waist (in)", step=0.1)
        hips = st.number_input("Hips (in)", step=0.1)
        if st.form_submit_button("Save"):
            conn.cursor().execute("INSERT INTO silhouette VALUES (?,?,?,?,0)", (datetime.now().strftime("%Y-%m-%d"), waist, hips, 0))
            conn.commit()

elif menu == "Analytics":
    st.title("📊 Progress")
    df_logs = pd.read_sql("SELECT * FROM logs", conn)
    if not df_logs.empty:
        st.line_chart(df_logs, x='date', y='weight', color='exercise')
        if st.button("Delete Last Entry"):
            conn.cursor().execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)")
            conn.commit()
            st.rerun()




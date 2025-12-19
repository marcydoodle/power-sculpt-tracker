import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Power-Sculpt Pro", page_icon="🍑", layout="centered")

# --- 2. DATABASE & CONNECTION SAFETY ---
db_mode = "Initializing..."
try:
    from streamlit_gsheets import GSheetsConnection
    if "connections" in st.secrets:
        conn = st.connection("gsheets", type=GSheetsConnection)
        db_mode = "Cloud (Google Sheets)"
    else:
        local_conn = sqlite3.connect('workout_storage.db', check_same_thread=False)
        db_mode = "Local (No Secrets)"
except Exception:
    local_conn = sqlite3.connect('workout_storage.db', check_same_thread=False)
    db_mode = "Local (Fallback Mode)"

if "Local" in db_mode:
    local_conn.execute('CREATE TABLE IF NOT EXISTS logs (date TEXT, exercise TEXT, weight REAL, reps INT, rpe REAL)')

# --- 3. PROGRAM LOGIC (16-WEEK PERIODIZATION) ---
start_date = datetime(2025, 12, 19) 
days_in = (datetime.now() - start_date).days
week_num = max(1, (days_in // 7) + 1)

# Logic for dynamic Phase, Sets, and Reps
if week_num <= 4:
    phase_name, set_goal, rep_range = "Phase 1: Hypertrophy", 3, "10-12 Reps"
elif week_num <= 12:
    phase_name, set_goal, rep_range = "Phase 2: Strength", 3, "6-8 Reps"
else:
    phase_name, set_goal, rep_range = "Phase 3: Peaking", 4, "3-5 Reps"

# --- 4. ROUTINES ---
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

def get_target_weight(ex):
    defaults = {'Back Squat': 160.0, 'Barbell Hip Thrust': 200.0, 'Bench Press': 115.0, 'Deadlift': 210.0}
    try:
        df = conn.read(worksheet="logs", ttl=0) if "Cloud" in db_mode else pd.read_sql("SELECT * FROM logs", local_conn)
        last_log = df[df['exercise'] == ex].tail(1)
        if last_log.empty: return defaults.get(ex, 45.0)
        weight, rpe = float(last_log.iloc[0]['weight']), float(last_log.iloc[0]['rpe'])
        return weight + 5.0 if rpe <= 7.0 else weight + 2.5 if rpe <= 9.0 else weight
    except: return defaults.get(ex, 45.0)

# --- 5. SIDEBAR ---
st.sidebar.title("🍑 Power-Sculpt")
st.sidebar.metric("Week", f"{week_num}/16")
st.sidebar.caption(f"Storage: {db_mode}")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Roadmap", "Analytics"])

# --- 6. PAGE: TODAY'S LIFT ---
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    
    # Restored Phase and Goal display
    st.info(f"**Current Goal:** {phase_name}  \n**Volume:** {set_goal} Sets x {rep_range}")
    
    # SUBSTITUTION LOGIC
    use_sub = st.toggle("🔄 Substitute / Add New Exercise")
    
    if use_sub:
        selected_move = st.text_input("Type Exercise Name", placeholder="e.g. Leg Press")
    else:
        todays_moves = routines.get(day_name, ["Rest Day"])
        selected_move = st.selectbox("Select Planned Exercise", todays_moves)

    if selected_move and selected_move != "Rest Day":
        target_w = get_target_weight(selected_move)
        
        # Display the targets clearly before the form
        c_t1, c_t2 = st.columns(2)
        c_t1.metric("Target Weight", f"{target_w} lbs")
        c_t2.metric("Target Reps", rep_range)

        with st.form("log_set", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            w_in = c1.number_input("Weight (Lbs)", value=float(target_w), step=2.5)
            r_in = c2.number_input("Reps Performed", value=10, step=1)
            rpe_in = c3.select_slider("RPE (Intensity)", options=[6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10], value=8.0)
            
            if st.form_submit_button("Record Set"):
                date_str = datetime.now().strftime("%Y-%m-%d")
                if "Cloud" in db_mode:
                    existing = conn.read(worksheet="logs", ttl=0)
                    new_row = pd.DataFrame([[date_str, selected_move, w_in, r_in, rpe_in]], columns=['date','exercise','weight','reps','rpe'])
                    conn.update(worksheet="logs", data=pd.concat([existing, new_row], ignore_index=True))
                else:
                    local_conn.execute("INSERT INTO logs VALUES (?,?,?,?,?)", (date_str, selected_move, w_in, r_in, rpe_in))
                    local_conn.commit()
                st.success(f"Set Recorded: {selected_move} at {w_in} lbs")
                st.balloons()
    elif selected_move == "Rest Day":
        st.write("🧘 **Rest Day.** Focus on recovery!")

# --- 7. PAGE: ROADMAP ---
elif menu == "Roadmap":
    st.title("🗓️ 16-Week Periodization")
    st.write(f"You are in **{phase_name}**. Focus on: *{rep_range}*")
    for day, moves in routines.items():
        with st.expander(f"**{day}**", expanded=(day == day_name)):
            for m in moves:
                st.write(f"🔹 **{m}**")

# --- 8. PAGE: ANALYTICS ---
elif menu == "Analytics":
    st.title("📊 Training History")
    df = conn.read(worksheet="logs", ttl=0) if "Cloud" in db_mode else pd.read_sql("SELECT * FROM logs", local_conn)
    if not df.empty:
        st.line_chart(df, x='date', y='weight', color='exercise')
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        if st.button("🗑️ Delete Last Entry"):
            if "Cloud" in db_mode: conn.update(worksheet="logs", data=df.iloc[:-1])
            else: local_conn.execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)"); local_conn.commit()
            st.rerun()
        st.download_button("📥 Export CSV", df.to_csv(index=False), "workout_backup.csv")
    else: st.info("No data yet. Crush it on Monday!")

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Power-Sculpt Pro", page_icon="🍑", layout="centered")

# --- 2. DATABASE & CONNECTION SAFETY ---
db_mode = "Local (Server)"
try:
    from streamlit_gsheets import GSheetsConnection
    if "connections" in st.secrets:
        conn = st.connection("gsheets", type=GSheetsConnection)
        db_mode = "Cloud (Google Sheets)"
    else:
        # Fallback to SQLite
        local_conn = sqlite3.connect('workout_storage.db', check_same_thread=False)
        db_mode = "Local (No Secrets)"
except Exception:
    local_conn = sqlite3.connect('workout_storage.db', check_same_thread=False)
    db_mode = "Local (Fallback Mode)"

# Initialize Local Table if needed
if "Local" in db_mode:
    local_conn.execute('CREATE TABLE IF NOT EXISTS logs (date TEXT, exercise TEXT, weight REAL, reps INT, rpe REAL)')

# --- 3. PROGRAM LOGIC (16-WEEK PERIODIZATION) ---
start_date = datetime(2025, 12, 19)
days_in = (datetime.now() - start_date).days
week_num = max(1, (days_in // 7) + 1)

if week_num <= 4:
    phase_name, rep_goal = "Phase 1: Hypertrophy", "3 Sets x 10-12 Reps"
elif week_num <= 12:
    phase_name, rep_goal = "Phase 2: Strength", "3 Sets x 6-8 Reps"
else:
    phase_name, rep_goal = "Phase 3: Peaking", "4 Sets x 3-5 Reps"

# --- 4. ROUTINES & TARGETS ---
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
    # Default starting weights
    defaults = {'Back Squat': 160.0, 'Barbell Hip Thrust': 200.0, 'Bench Press': 115.0, 'Deadlift': 210.0}
    try:
        if "Cloud" in db_mode:
            df = conn.read(worksheet="logs", ttl=0)
        else:
            df = pd.read_sql("SELECT * FROM logs", local_conn)
        
        last_log = df[df['exercise'] == ex].tail(1)
        if last_log.empty: return defaults.get(ex, 45.0)
        
        weight = float(last_log.iloc[0]['weight'])
        rpe = float(last_log.iloc[0]['rpe'])
        # Progression Logic
        if rpe <= 7.0: return weight + 5.0
        elif rpe <= 9.0: return weight + 2.5
        return weight
    except:
        return defaults.get(ex, 45.0)

# --- 5. SIDEBAR ---
st.sidebar.title("🍑 Power-Sculpt")
st.sidebar.metric("Week", f"{week_num}/16")
st.sidebar.caption(f"Status: {db_mode}")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Program Roadmap", "Analytics"])

# --- 6. PAGE: TODAY'S LIFT ---
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    st.info(f"**{phase_name}** | Goal: **{rep_goal}**")
    
    moves = routines.get(day_name, ["Rest Day"])
    if "Rest Day" in moves:
        st.write("🧘 **It's a Rest Day!** Focus on mobility and recovery.")
    else:
        selected_move = st.selectbox("Select Exercise", moves)
        target_w = get_target_weight(selected_move)
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Target Weight", f"{target_w} lbs")
        col_m2.metric("Target Reps", rep_goal.split('x')[1].strip())

        with st.form("log_set", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            w_in = c1.number_input("Weight", value=float(target_w), step=2.5)
            r_in = c2.number_input("Reps", value=10, step=1)
            rpe_in = c3.select_slider("RPE", options=[6, 7, 7.5, 8, 8.5, 9, 9.5, 10], value=8.0)
            
            if st.form_submit_button("Record Set"):
                date_str = datetime.now().strftime("%Y-%m-%d")
                if "Cloud" in db_mode:
                    existing = conn.read(worksheet="logs", ttl=0)
                    new_row = pd.DataFrame([[date_str, selected_move, w_in, r_in, rpe_in]], columns=['date','exercise','weight','reps','rpe'])
                    updated = pd.concat([existing, new_row], ignore_index=True)
                    conn.update(worksheet="logs", data=updated)
                else:
                    local_conn.execute("INSERT INTO logs VALUES (?,?,?,?,?)", (date_str, selected_move, w_in, r_in, rpe_in))
                    local_conn.commit()
                st.success(f"Successfully Logged {selected_move}!")
                st.balloons()

# --- 7. PAGE: PROGRAM ROADMAP ---
elif menu == "Program Roadmap":
    st.title("🗓️ Weekly Plan")
    st.write(f"Targets for **{phase_name}**")
    
    # Get PRs for the Star Logic
    try:
        if "Cloud" in db_mode:
            all_data = conn.read(worksheet="logs", ttl=0)
        else:
            all_data = pd.read_sql("SELECT * FROM logs", local_conn)
        pr_dict = all_data.groupby('exercise')['weight'].max().to_dict()
    except:
        pr_dict = {}

    for day, moves in routines.items():
        is_today = (day == day_name)
        with st.expander(f"**{day}**", expanded=is_today):
            if "Rest Day" in moves:
                st.write("🧘 Active Recovery")
            else:
                for m in moves:
                    target = get_target_weight(m)
                    all_time_max = pr_dict.get(m, 0)
                    icon = "🔥" if (all_time_max > 0 and target >= all_time_max) else "🔹"
                    st.write(f"{icon} **{m}**: {target} lbs — *{rep_goal}*")

# --- 8. PAGE: ANALYTICS ---
# --- UPDATE IN ANALYTICS PAGE ---
elif menu == "Analytics":
    st.title("📊 Progress Tracker")
    
    # 1. Load the Data
    if "Cloud" in db_mode:
        df = conn.read(worksheet="logs", ttl=0)
    else:
        df = pd.read_sql("SELECT * FROM logs", local_conn)

    if not df.empty:
        st.line_chart(df, x='date', y='weight', color='exercise')
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        
        # 2. DELETE BUTTON SECTION
        st.markdown("---")
        if st.button("🗑️ Delete Last Entry"):
            if "Cloud" in db_mode:
                # Remove the last row and update Sheets
                updated_df = df.iloc[:-1]
                conn.update(worksheet="logs", data=updated_df)
            else:
                # SQL command to delete the most recent row
                local_conn.execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)")
                local_conn.commit()
            
            st.warning("Last entry deleted.")
            st.rerun() # Refresh page to show data is gone

        st.download_button("📥 Download CSV Backup", df.to_csv(index=False), "workout_backup.csv")
    else:
        st.info("No data recorded yet.")

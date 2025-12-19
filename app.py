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

# Initialize Local Table if needed
if "Local" in db_mode:
    local_conn.execute('CREATE TABLE IF NOT EXISTS logs (date TEXT, exercise TEXT, weight REAL, reps INT, rpe REAL)')

# --- 3. PROGRAM LOGIC (16-WEEK PERIODIZATION) ---
# Start date set to Monday, Dec 22, 2025 (or today for testing)
start_date = datetime(2025, 12, 19) 
days_in = (datetime.now() - start_date).days
week_num = max(1, (days_in // 7) + 1)

if week_num <= 4:
    phase_name, rep_goal = "Phase 1: Hypertrophy", "3 Sets x 10-12 Reps"
elif week_num <= 12:
    phase_name, rep_goal = "Phase 2: Strength", "3 Sets x 6-8 Reps"
else:
    phase_name, rep_goal = "Phase 3: Peaking", "4 Sets x 3-5 Reps"

# --- 4. FULL ROUTINES ---
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
        if rpe <= 7.0: return weight + 5.0
        elif rpe <= 9.0: return weight + 2.5
        return weight
    except:
        return defaults.get(ex, 45.0)

# --- 5. SIDEBAR ---
st.sidebar.title("🍑 Power-Sculpt")
st.sidebar.metric("Program Week", f"{week_num}/16")
st.sidebar.caption(f"Storage: {db_mode}")
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Roadmap", "Analytics"])

# --- 6. PAGE: TODAY'S LIFT ---
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    st.info(f"**{phase_name}** | Target: **{rep_goal}**")
    
    todays_moves = routines.get(day_name, ["Rest Day"])
    if "Rest Day" in todays_moves:
        st.write("🧘 **Rest Day.** Focus on mobility and protein intake!")
    else:
        selected_move = st.selectbox("Select Exercise", todays_moves)
        target_w = get_target_weight(selected_move)
        
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("Target Weight", f"{target_w} lbs")
        c_m2.metric("Target Reps", rep_goal.split('x')[1].strip())

        with st.form("log_set", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            w_in = c1.number_input("Lbs", value=float(target_w), step=2.5)
            r_in = c2.number_input("Reps", value=10, step=1)
            rpe_in = c3.select_slider("RPE", options=[6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10], value=8.0)
            
            if st.form_submit_button("Record Set"):
                date_str = datetime.now().strftime("%Y-%m-%d")
                if "Cloud" in db_mode:
                    existing = conn.read(worksheet="logs", ttl=0)
                    new_row = pd.DataFrame([[date_str, selected_move, w_in, r_in, rpe_in]], columns=['date','exercise','weight','reps','rpe'])
                    conn.update(worksheet="logs", data=pd.concat([existing, new_row], ignore_index=True))
                else:
                    local_conn.execute("INSERT INTO logs VALUES (?,?,?,?,?)", (date_str, selected_move, w_in, r_in, rpe_in))
                    local_conn.commit()
                st.success(f"Logged {selected_move} at {w_in} lbs!")
                st.balloons()

# --- 7. PAGE: ROADMAP ---
elif menu == "Roadmap":
    st.title("🗓️ 16-Week Journey")
    try:
        df = conn.read(worksheet="logs", ttl=0) if "Cloud" in db_mode else pd.read_sql("SELECT * FROM logs", local_conn)
        pr_dict = df.groupby('exercise')['weight'].max().to_dict()
    except: pr_dict = {}

    for day, moves in routines.items():
        with st.expander(f"**{day}**", expanded=(day == day_name)):
            if "Rest Day" in moves: st.write("🧘 Recovery")
            else:
                for m in moves:
                    target = get_target_weight(m)
                    star = "🔥" if (pr_dict.get(m, 0) > 0 and target >= pr_dict.get(m,0)) else "🔹"
                    st.write(f"{star} **{m}**: {target} lbs")

# --- 8. PAGE: ANALYTICS ---
elif menu == "Analytics":
    st.title("📊 Progress & History")
    try:
        df = conn.read(worksheet="logs", ttl=0) if "Cloud" in db_mode else pd.read_sql("SELECT * FROM logs", local_conn)
        if not df.empty:
            st.line_chart(df, x='date', y='weight', color='exercise')
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
            
            st.divider()
            if st.button("🗑️ Delete Last Entry"):
                if "Cloud" in db_mode:
                    conn.update(worksheet="logs", data=df.iloc[:-1])
                else:
                    local_conn.execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)")
                    local_conn.commit()
                st.warning("Entry Deleted.")
                st.rerun()
                
            st.download_button("📥 Download Backup (CSV)", df.to_csv(index=False), "power_sculpt_backup.csv")
        else: st.info("No data yet.")
    except Exception as e: st.error(f"Error: {e}")

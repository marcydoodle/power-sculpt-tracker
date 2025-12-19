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
    local_conn.execute('CREATE TABLE IF NOT EXISTS silhouette (date TEXT, waist REAL, hips REAL, body_weight REAL)')

# --- 3. PROGRAM LOGIC ---
start_date = datetime(2025, 12, 19) 
days_in = (datetime.now() - start_date).days
week_num = max(1, (days_in // 7) + 1)

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
menu = st.sidebar.radio("Navigation", ["Today's Lift", "Silhouette Tracker", "Roadmap", "Analytics"])

# --- 6. PAGE: TODAY'S LIFT ---
if menu == "Today's Lift":
    st.title(f"🏋️ {day_name} Session")
    st.info(f"**{phase_name}** | {set_goal} Sets x {rep_range}")
    
    use_sub = st.toggle("🔄 Substitute / Add New Exercise")
    if use_sub:
        selected_move = st.text_input("Type Exercise Name", placeholder="e.g. Leg Press")
    else:
        todays_moves = routines.get(day_name, ["Rest Day"])
        selected_move = st.selectbox("Select Planned Exercise", todays_moves)

    if selected_move and selected_move != "Rest Day":
        target_w = get_target_weight(selected_move)
        st.metric("Target", f"{target_w} lbs @ {rep_range}")

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
                st.success(f"Logged {selected_move}!")

# --- 7. NEW PAGE: SILHOUETTE TRACKER ---
elif menu == "Silhouette Tracker":
    st.title("📏 Silhouette Tracking")
    st.write("Track your measurements to see your body composition change.")
    
    with st.form("silhouette_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        wst = c1.number_input("Waist (in)", value=28.0, step=0.1)
        hp = c2.number_input("Hips (in)", value=38.0, step=0.1)
        bw = c3.number_input("Body Weight (lbs)", value=140.0, step=0.1)
        
        if st.form_submit_button("Save Measurements"):
            date_str = datetime.now().strftime("%Y-%m-%d")
            if "Cloud" in db_mode:
                existing = conn.read(worksheet="silhouette", ttl=0)
                new_row = pd.DataFrame([[date_str, wst, hp, bw]], columns=['date','waist','hips','body_weight'])
                conn.update(worksheet="silhouette", data=pd.concat([existing, new_row], ignore_index=True))
            else:
                local_conn.execute("INSERT INTO silhouette VALUES (?,?,?,?)", (date_str, wst, hp, bw))
                local_conn.commit()
            st.success("Measurements saved!")

    st.subheader("Progress History")
    df_s = conn.read(worksheet="silhouette", ttl=0) if "Cloud" in db_mode else pd.read_sql("SELECT * FROM silhouette", local_conn)
    if not df_s.empty:
        st.line_chart(df_s.set_index('date')[['waist', 'hips', 'body_weight']])
        st.dataframe(df_s.sort_index(ascending=False))

# --- 8. PAGE: ROADMAP ---
elif menu == "Roadmap":
    st.title("🗓️ 16-Week Journey")
    for day, moves in routines.items():
        with st.expander(f"**{day}**", expanded=(day == day_name)):
            for m in moves: st.write(f"🔹 **{m}**")

# --- 9. PAGE: ANALYTICS ---
elif menu == "Analytics":
    st.title("📊 Training History")
    df = conn.read(worksheet="logs", ttl=0) if "Cloud" in db_mode else pd.read_sql("SELECT * FROM logs", local_conn)
    if not df.empty:
        st.line_chart(df, x='date', y='weight', color='exercise')
        st.dataframe(df.sort_index(ascending=False))
        if st.button("🗑️ Delete Last Entry"):
            if "Cloud" in db_mode: conn.update(worksheet="logs", data=df.iloc[:-1])
            else: local_conn.execute("DELETE FROM logs WHERE rowid = (SELECT MAX(rowid) FROM logs)"); local_conn.commit()
            st.rerun()

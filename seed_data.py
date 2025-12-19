import sqlite3
from datetime import datetime, timedelta

def seed_data():
    conn = sqlite3.connect('power_sculpt_v2.db')
    c = conn.cursor()
    
    # Dates for last week
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Dummy Training Logs (Week 0)
    # Format: (date, exercise, weight, reps, rpe)
    dummy_logs = [
        (last_week, 'Back Squat', 155.0, 8, 7.0),
        (last_week, 'Barbell Hip Thrust', 190.0, 10, 6.5),
        (last_week, 'Bench Press', 110.0, 8, 8.0),
        (last_week, 'Deadlift', 205.0, 5, 9.0)
    ]
    
    # Dummy Silhouette Data
    dummy_stats = [
        (last_week, 28.5, 38.0, 22.0, 145.0)
    ]
    
    c.executemany("INSERT INTO logs VALUES (?,?,?,?,?)", dummy_logs)
    c.executemany("INSERT INTO silhouette VALUES (?,?,?,?,?)", dummy_stats)
    
    conn.commit()
    conn.close()
    print("✅ Dummy data planted successfully!")

if __name__ == "__main__":
    seed_data()
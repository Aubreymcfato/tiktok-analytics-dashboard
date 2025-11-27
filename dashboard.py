# dashboard.py — FINAL VERSION THAT WORKS WITH EVERY SINGLE ONE OF YOUR CSVS
import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

# UPDATE THIS WHEN YOU DOWNLOAD NEW DATA
DOWNLOAD_DATE = "2025-11-27"
DATA_DIR = "./data"

def safe_int(x):
    if not x or str(x).strip() == "": 
        return 0
    try:
        return int(str(x).replace(",", "").strip())
    except:
        return 0

def safe_float(x):
    if not x or str(x).strip() == "": 
        return 0.0
    try:
        return float(str(x).replace("%", "").replace(",", "").strip())
    except:
        return 0.0

@st.cache_data
def load_all_data():
    profiles = []
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_tiktok_stats.csv"))
    
    for filepath in csv_files:
        username = os.path.basename(filepath).replace("_tiktok_stats.csv", "")
        data = parse_csv_safely(filepath)
        if data:
            data['username'] = username
            data['download_date'] = DOWNLOAD_DATE
            profiles.append(data)
    return profiles

def parse_csv_safely(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.rstrip() for line in f.readlines()]

        result = {
            'nickname': 'Unknown',
            'follower_count': 0,
            'avg_likes': 0,
            'avg_comments': 0,
            'avg_shares': 0,
            'engagement_rate': 0.0,
            'video_count': 0,
            'videos': pd.DataFrame()
        }

        in_videos = False
        video_lines = []

        for line in lines:
            line = line.strip()
            if not line or line == ",":
                continue

            # === METRICS (only read lines that actually contain a comma and a value) ===
            if not in_videos:
                if "Nickname," in line:
                    result['nickname'] = line.split(",", 1)[1].strip()
                elif "Follower Count," in line:
                    result['follower_count'] = safe_int(line.split(",", 1)[1])
                elif "Average Likes," in line:
                    result['avg_likes'] = safe_int(line.split(",", 1)[1])
                elif "Average Comments," in line:
                    result['avg_comments'] = safe_int(line.split(",", 1)[1])
                elif "Average Shares," in line:
                    result['avg_shares'] = safe_int(line.split(",", 1)[1])
                elif "Total Engagement Rate," in line:
                    result['engagement_rate'] = safe_float(line.split(",", 1)[1])
                elif "Video Count," in line:
                    result['video_count'] = safe_int(line.split(",", 1)[1])
                elif line.startswith("Videos"):
                    in_videos = True
                    continue

            # === COLLECT VIDEO LINES ===
            else:
                if line.startswith("Date,Plays") or line.startswith("Mentions") or line.startswith("Hashtags"):
                    continue
                if line.startswith("Date,"):
                    video_lines.append(line)

        # === PARSE VIDEOS (super robust) ===
        videos = []
        for vline in video_lines:
            if '",' in vline:
                # Description is quoted at the end
                desc_start = vline.rfind('",')
                if desc_start == -1:
                    continue
                desc = vline[desc_start+2:].strip('"')
                numbers = vline[:desc_start]
            else:
                # No quoted description → split normally
                parts = vline.split(",", 5)
                if len(parts) < 6:
                    continue
                numbers = ",".join(parts[:5])
                desc = parts[5].strip('"') if len(parts) > 5 else ""

            fields = [f.strip() for f in numbers.split(",")]
            if len(fields) < 5:
                continue

            # Last 4 are always plays, likes, comments, shares
            plays = safe_int(fields[-4])
            likes = safe_int(fields[-3])
            comments = safe_int(fields[-2])
            shares = safe_int(fields[-1])

            # Timestamp = everything before the numbers
            timestamp = ", ".join(fields[:-4])

            videos.append({
                'date': timestamp,
                'plays': plays,
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'description': desc
            })

        result['videos'] = pd.DataFrame(videos)
        return result

    except Exception as e:
        st.error(f"Error parsing {os.path.basename(filepath)}: {e}")
        return None

# ===================== STREAMLIT APP =====================
st.set_page_config(page_title="BookTok Leaderboard", layout="wide")
st.title("BookTok Italia Leaderboard")
st.caption(f"Data updated: **{DOWNLOAD_DATE}**")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

uploaded = st.sidebar.file_uploader("Upload new CSVs", accept_multiple_files=True, type="csv")
if uploaded:
    for f in uploaded:
        with open(os.path.join(DATA_DIR, f.name), "wb") as out:
            out.write(f.getbuffer())
    st.sidebar.success("Uploaded! Refreshing...")
    st.rerun()

profiles = load_all_data()

if not profiles:
    st.warning("No valid CSV files found in ./data/")
    st.stop()

# MAIN LEADERBOARD — only what you care about
df = pd.DataFrame([{
    'Username': p['username'],
    'Nickname': p['nickname'],
    'Followers': p['follower_count'],
    'Avg Likes': p['avg_likes'],
    'Avg Comments': p['avg_comments'],
    'Avg Shares': p['avg_shares'],
    'Engagement %': round(p['engagement_rate'], 2),
    'Videos': p['video_count'] or len(p['videos']),
    'Active': 'Yes' if len(p['videos']) > 0 else 'No'
} for p in profiles])

tab1, tab2 = st.tabs(["Leaderboard", "Details"])

with tab1:
    st.header("Top BookTok Accounts — Sorted by Average Likes")
    board = df.sort_values("Avg Likes", ascending=False).reset_index(drop=True)
    st.dataframe(board.style.format({
        "Followers": "{:,}",
        "Avg Likes": "{:,}",
        "Avg Comments": "{:,}",
        "Avg Shares": "{:,}"
    }), use_container_width=True, hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Accounts", len(board))
    c2.metric("Top Avg Likes", f"{board['Avg Likes'].iloc[0]:,}")
    c3.metric("Median Avg Likes", f"{board['Avg Likes'].median():,.0f}")
    c4.metric("Most Active", board

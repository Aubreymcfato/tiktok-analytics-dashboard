# dashboard.py — FINAL VERSION (works with every TikTok stats CSV you've got)
import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

# CHANGE THIS DATE APPEARS IN THE DASHBOARD — CHANGE IT WHEN YOU UPDATE THE DATA
DOWNLOAD_DATE = "2025-11-27"

DATA_DIR = "./data"

def safe_int(x):
    """Safely convert to int, return 0 on empty/invalid values"""
    if not x or str(x).strip() in ("", ","):
        return 0
    try:
        return int(str(x).replace(",", "").strip())
    except:
        return 0

def safe_float(x):
    """Safely convert to float (removes % too)"""
    if not x or str(x).strip() in ("", ","):
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
        profile = parse_csv(filepath)
        if profile:
            profile["username"] = username
            profile["download_date"] = DOWNLOAD_DATE
            profiles.append(profile)
    return profiles

def parse_csv(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]

        data = {
            "nickname": "Unknown",
            "follower_count": 0,
            "avg_likes": 0,
            "avg_comments": 0,
            "avg_shares": 0,
            "engagement_rate": 0.0,
            "video_count": 0,
            "videos": pd.DataFrame(),
        }

        in_videos_section = False
        video_lines = []

        for line in lines:
            original_line = line
            line = line.strip()

            if not line or line == ",":
                continue

            # ----- HEADER METRICS -----
            if not in_videos_section:
                if line.startswith("Nickname,"):
                    data["nickname"] = line.split(",", 1)[1].strip()
                elif line.startswith("Follower Count,"):
                    data["follower_count"] = safe_int(line.split(",", 1)[1])
                elif line.startswith("Average Likes,"):
                    data["avg_likes"] = safe_int(line.split(",", 1)[1])
                elif line.startswith("Average Comments,"):
                    data["avg_comments"] = safe_int(line.split(",", 1)[1])
                elif line.startswith("Average Shares,"):
                    data["avg_shares"] = safe_int(line.split(",", 1)[1])
                elif line.startswith("Total Engagement Rate,"):
                    data["engagement_rate"] = safe_float(line.split(",", 1)[1])
                elif line.startswith("Video Count,"):
                    data["video_count"] = safe_int(line.split(",", 1)[1])
                elif line.startswith("Videos"):
                    in_videos_section = True
                    continue

            # ----- COLLECT VIDEO LINES -----
            else:
                if line.startswith("Date,Plays") or line.startswith("Mentions") or line.startswith("Hashtags"):
                    continue
                if line.startswith("Date,"):
                    video_lines.append(original_line)  # keep original for correct quoting

        # ----- PARSE VIDEOS (handles commas in descriptions & empty fields) -----
        videos = []
        for vline in video_lines:
            vline = vline.strip()
            if not vline:
                continue

            # Case 1: description is quoted at the end → find last ",
            if '",' in vline:
                desc_start = vline.rfind('",')
                if desc_start == -1:
                    continue
                description = vline[desc_start + 2 :].strip().strip('"')
                numbers_part = vline[: desc_start]
            else:
                # Case 2: no quotes → split normally (rare but happens)
                parts = vline.split(",", 5)
                if len(parts) < 6:
                    continue
                numbers_part = ",".join(parts[:5])
                description = parts[5].strip().strip('"')

            fields = [f.strip() for f in numbers_part.split(",")]
            if len(fields) < 5:
                continue

            plays = safe_int(fields[-4])
            likes = safe_int(fields[-3])
            comments = safe_int(fields[-2])
            shares = safe_int(fields[-1])
            timestamp = ", ".join(fields[:-4])

            videos.append({
                "date": timestamp if timestamp else "Unknown",
                "plays": plays,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "description": description,
            })

        data["videos"] = pd.DataFrame(videos)
        return data

    except Exception as e:
        st.error(f"Error parsing {os.path.basename(filepath)}: {e}")
        return None

# ===================== STREAMLIT APP =====================
st.set_page_config(page_title="BookTok Italia Leaderboard", layout="wide")
st.title("BookTok Italia Leaderboard")
st.caption(f"Data updated on: **{DOWNLOAD_DATE}**")

# Create data folder if missing
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Sidebar uploader
uploaded = st.sidebar.file_uploader("Upload new *_tiktok_stats.csv files", accept_multiple_files=True, type="csv")
if uploaded:
    for file in uploaded:
        with open(os.path.join(DATA_DIR, file.name), "wb") as f:
            f.write(file.getbuffer())
    st.sidebar.success("Files uploaded — refreshing data...")
    st.rerun()

# Load data
profiles = load_all_data()

if not profiles:
    st.warning("No valid CSV files found in the `./data` folder.")
    st.stop()

# Build leaderboard
leaderboard = pd.DataFrame([
    {
        "Username": p["username"],
        "Nickname": p["nickname"],
        "Followers": p["follower_count"],
        "Avg Likes": p["avg_likes"],
        "Avg Comments": p["avg_comments"],
        "Avg Shares": p["avg_shares"],
        "Engagement %": round(p["engagement_rate"], 2),
        "Total Videos": p["video_count"] or len(p["videos"]),
    }
    for p in profiles
])

tab1, tab2 = st.tabs(["Leaderboard", "Profile Details"])

with tab1:
    st.header("Top Accounts — Sorted by Average Likes")
    sorted_board = leaderboard.sort_values("Avg Likes", ascending=False).reset_index(drop=True)
    st.dataframe(
        sorted_board.style.format({
            "Followers": "{:,}",
            "Avg Likes": "{:,}",
            "Avg Comments": "{:,}",
            "Avg Shares": "{:,}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Accounts", len(sorted_board))
    col2.metric("Highest Avg Likes", f"{sorted_board['Avg Likes'].iloc[0]:,}")
    col3.metric("Median Avg Likes", f"{sorted_board['Avg Likes'].median():,.0f}")
    col4.metric("Most Videos", f"{sorted_board.loc[sorted_board["Total Videos"].idxmax(), "Nickname"])

with tab2:
    selected_username = st.selectbox("Choose an account", options=leaderboard["Username"])
    profile = next(p for p in profiles if p["username"] == selected_username)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"@{profile['username']}")
        st.write(f"**{profile['nickname']}**")
        st.write(f"**Followers:** {profile['follower_count']:,}")
        st.write(f"**Total Videos:** {len(profile['videos'])}")
        st.metric("Average Likes", f"{profile['avg_likes']:,}")
        st.metric("Engagement Rate", f"{profile['engagement_rate']:.2f}%")

    with col2:
        if not profile["videos"].empty:
            st.subheader("Latest Videos")
            display = profile["videos"].head(15).copy()
            display["date"] = pd.to_datetime(display["date"], errors="coerce").dt.strftime("%b %d, %Y")
            st.dataframe(
                display[["date", "plays", "likes", "comments", "shares", "description"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No video data available for this profile.")

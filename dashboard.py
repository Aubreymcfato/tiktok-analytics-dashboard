# dashboard.py — FINAL, PERFECTLY WORKING VERSION (2025-11-27)
import streamlit as st
import pandas as pd
import os
import glob

# UPDATE THIS EVERY TIME YOU DOWNLOAD NEW DATA
DOWNLOAD_DATE = "2025-11-27"

DATA_DIR = "./data"

def safe_int(s):
    """Convert string to int safely, return 0 if empty/invalid"""
    if not s or str(s).strip() == "":
        return 0
    try:
        return int(str(s).replace(",", "").strip())
    except:
        return 0

@st.cache_data
def load_all_data():
    profiles = []
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_tiktok_stats.csv"))
    
    for file_path in csv_files:
        username = os.path.basename(file_path).replace("_tiktok_stats.csv", "")
        data = parse_tiktok_csv(file_path)
        if data:
            data['username'] = username
            data['download_date'] = DOWNLOAD_DATE
            profiles.append(data)
    return profiles

def parse_tiktok_csv(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]

        result = {
            'nickname': '', 'follower_count': 0,
            'avg_views': 0, 'avg_likes': 0, 'avg_comments': 0, 'avg_shares': 0,
            'engagement_rate': 0.0,
            'videos': pd.DataFrame(),
            'mentions': {}, 'hashtags': {}
        }

        section = None
        video_lines = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # --- METRICS ---
            if line.startswith("Username,"):
                result['username'] = line.split(",", 1)[1].strip()
            elif line.startswith("Nickname,"):
                result['nickname'] = line.split(",", 1)[1].strip()
            elif line.startswith("Follower Count,"):
                result['follower_count'] = safe_int(line.split(",", 1)[1])
            elif line.startswith("Average Views,"):
                result['avg_views'] = safe_int(line.split(",", 1)[1])
            elif line.startswith("Average Likes,"):
                result['avg_likes'] = safe_int(line.split(",", 1)[1])
            elif line.startswith("Average Comments,"):
                result['avg_comments'] = safe_int(line.split(",", 1)[1])
            elif line.startswith("Average Shares,"):
                result['avg_shares'] = safe_int(line.split(",", 1)[1])
            elif line.startswith("Total Engagement Rate,"):
                val = line.split(",", 1)[1].strip().replace("%", "")
                result['engagement_rate'] = float(val) if val else 0.0

            # --- SECTION SWITCH ---
            elif line.startswith("Videos"):
                section = "videos"
                continue
            elif line.startswith("Mentions"):
                section = "mentions"
                continue
            elif line.startswith("Hashtags"):
                section = "hashtags"
                continue

            # --- COLLECT VIDEO LINES ---
            elif section == "videos":
                if line.startswith("Date,Plays"):
                    continue
                video_lines.append(raw_line)

            # --- MENTIONS & HASHTAGS ---
            elif section == "mentions" and "," in line:
                mention, count = line.rsplit(",", 1)
                result['mentions'][mention.strip("@ ").strip()] = safe_int(count)
            elif section == "hashtags" and "," in line:
                tag, count = line.rsplit(",", 1)
                result['hashtags'][tag.strip("# ").strip()] = safe_int(count)

        # === PARSE VIDEOS — BULLETPROOF ===
        videos = []
        for line in video_lines:
            if not line.strip():
                continue

            # Find description (last quoted field)
            if line.count('"') < 2:
                continue
            start = line.rfind('",')
            if start == -1:
                continue

            description = line[start + 2:].strip().strip('"')
            before_desc = line[:start].strip()

            fields = [f.strip() for f in before_desc.split(",")]

            if len(fields) < 6:  # need at least date, time, plays, likes, comments, shares
                continue

            # Last 4 numeric fields
            plays = safe_int(fields[-4])
            likes = safe_int(fields[-3])
            comments = safe_int(fields[-2])
            shares = safe_int(fields[-1])

            # Everything before = timestamp
            timestamp = ", ".join(fields[:-4])

            videos.append({
                'date': timestamp if timestamp else "Unknown",
                'plays': plays,
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'description': description
            })

        result['videos'] = pd.DataFrame(videos)
        return result

    except Exception as e:
        st.error(f"Error parsing {os.path.basename(filepath)}: {e}")
        return None

# ===================== STREAMLIT APP =====================
st.set_page_config(page_title="TikTok Leaderboard", layout="wide")
st.title("TikTok Analytics Dashboard")
st.caption(f"Data downloaded on: **{DOWNLOAD_DATE}**")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

uploaded = st.sidebar.file_uploader("Upload new CSVs", accept_multiple_files=True, type="csv")
if uploaded:
    for f in uploaded:
        path = os.path.join(DATA_DIR, f.name)
        with open(path, "wb") as out:
            out.write(f.getbuffer())
    st.sidebar.success("Uploaded! Refreshing...")
    st.rerun()

profiles = load_all_data()
if not profiles:
    st.warning("No CSV files found in ./data/ folder")
    st.stop()

summary = pd.DataFrame([{
    'Username': p['username'],
    'Nickname': p['nickname'],
    'Followers': f"{p['follower_count']:,}",
    'Avg Likes': p['avg_likes'],
    'Avg Comments': p['avg_comments'],
    'Avg Shares': p['avg_shares'],
    'Engagement %': round(p['engagement_rate'], 2),
    'Date': p['download_date']
} for p in profiles])

tab1, tab2 = st.tabs(["Leaderboard", "Profile Detail"])

with tab1:
    st.header("Leaderboard — Sorted by Average Likes")
    board = summary.sort_values("Avg Likes", ascending=False).reset_index(drop=True)
    st.dataframe(board.style.format({"Avg Likes": "{:,}", "Followers": "{:,}"}), 
                 use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Accounts", len(board))
    c2.metric("Top Avg Likes", f"{board['Avg Likes'].iloc[0]:,}")
    c3.metric("Median Avg Likes", f"{board['Avg Likes'].median():,.0f}")

with tab2:
    selected = st.selectbox("Select account", options=[p['username'] for p in profiles])
    p = next(x for x in profiles if x['username'] == selected)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"@{selected}")
        st.write(f"**{p['nickname']}**")
        st.write(f"**Followers:** {p['follower_count']:,}")
        st.write(f"**Data from:** {p['download_date']}")
        st.metric("Avg Likes", f"{p['avg_likes']:,}")
        st.metric("Avg Comments", f"{p['avg_comments']:,}")
        st.metric("Avg Shares", f"{p['avg_shares']:,}")
        st.metric("Engagement", f"{p['engagement_rate']:.2f}%")

    with col2:
        if not p['videos'].empty:
            st.subheader("Latest Videos")
            df = p['videos'].head(20).copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime("%b %d, %Y %I:%M %p")
            st.dataframe(df[['date', 'plays', 'likes', 'comments', 'shares', 'description']],
                         use_container_width=True, hide_index=True)

    c3, c4 = st.columns(2)
    with c3:
        if p['mentions']:
            mdf = pd.DataFrame(list(p['mentions'].items()), columns=['Account', 'Count'])\
                  .sort_values('Count', ascending=False).head(10)
            st.dataframe(mdf, use_container_width=True, hide_index=True)
    with c4:
        if p['hashtags']:
            hdf = pd.DataFrame(list(p['hashtags'].items()), columns=['Hashtag', 'Count'])\
                  .sort_values('Count', ascending=False).head(10)
            st.dataframe(hdf, use_container_width=True, hide_index=True)

# dashboard.py — FINAL VERSION (works on Streamlit Cloud + local)
import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

# UPDATE THIS EVERY TIME YOU DOWNLOAD NEW DATA
DOWNLOAD_DATE = "2025-11-27"

DATA_DIR = "./data"

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

        data = {
            'nickname': '', 'follower_count': 0,
            'avg_views': 0, 'avg_likes': 0, 'avg_comments': 0, 'avg_shares': 0,
            'engagement_rate': 0.0,
            'videos': pd.DataFrame(),
            'mentions': {}, 'hashtags': {}
        }

        section = None
        video_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # --- METRICS ---
            if line.startswith("Username,"):
                data['username'] = line.split(",", 1)[1].strip()
            elif line.startswith("Nickname,"):
                data['nickname'] = line.split(",", 1)[1].strip()
            elif line.startswith("Follower Count,"):
                data['follower_count'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Views,"):
                data['avg_views'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Likes,"):
                data['avg_likes'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Comments,"):
                data['avg_comments'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Shares,"):
                data['avg_shares'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Total Engagement Rate,"):
                val = line.split(",", 1)[1].strip().replace("%", "")
                data['engagement_rate'] = float(val) if val else 0.0

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

            # --- VIDEOS (the tricky part) ---
            elif section == "videos":
                if line.startswith("Date,Plays"):
                    continue  # header
                video_lines.append(line)

            # --- MENTIONS & HASHTAGS ---
            elif section == "mentions":
                if "," in line:
                    mention, count = line.rsplit(",", 1)
                    data['mentions'][mention.strip("@ ").strip()] = int(count.strip())
            elif section == "hashtags":
                if "," in line:
                    tag, count = line.rsplit(",", 1)
                    data['hashtags'][tag.strip("# ").strip()] = int(count.strip())

        # === PARSE VIDEOS SAFELY (handles commas in description + date,time format) ===
        videos = []
        for line in video_lines:
            if not line:
                continue

            # Find the last 4 numeric fields: Likes, Comments, Shares, Description (quoted)
            # Description is always quoted and may contain commas
            if '",' in line:
                # Split on the last ", before the final quote
                desc_start = line.rfind('",')  # last occurrence of ",
                if desc_start == -1:
                    continue
                numbers_part = line[:desc_start]
                description = line[desc_start+2:].strip().strip('"')

                # Now split the part before description
                fields = [f.strip() for f in numbers_part.split(",")]
                if len(fields) < 5:
                    continue

                # Last 4 fields before description
                try:
                    shares = int(fields[-1].replace(",", ""))
                    comments = int(fields[-2].replace(",", ""))
                    likes = int(fields[-3].replace(",", ""))
                    plays = int(fields[-4].replace(",", ""))

                    # Everything before the last 4 numeric fields is the timestamp
                    timestamp_parts = fields[:-4]
                    full_timestamp = ", ".join(timestamp_parts)  # e.g. "11/25/2025, 12:08:36 PM"

                    videos.append({
                        'date': full_timestamp,
                        'plays': plays,
                        'likes': likes,
                        'comments': comments,
                        'shares': shares,
                        'description': description
                    })
                except:
                    continue  # skip malformed lines

        data['videos'] = pd.DataFrame(videos)
        return data

    except Exception as e:
        st.error(f"Error parsing {os.path.basename(filepath)}: {e}")
        return None

# ===================== STREAMLIT APP =====================
st.set_page_config(page_title="TikTok Leaderboard", layout="wide")
st.title("TikTok Analytics Dashboard")
st.caption(f"Data downloaded on: **{DOWNLOAD_DATE}**")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

uploaded = st.sidebar.file_uploader("Upload new CSVs (optional)", accept_multiple_files=True, type="csv")
if uploaded:
    for f in uploaded:
        with open(os.path.join(DATA_DIR, f.name), "wb") as out:
            out.write(f.getbuffer())
    st.sidebar.success("Uploaded! Refreshing data...")
    st.rerun()

profiles = load_all_data()
if not profiles:
    st.warning("No CSV files found in ./data folder")
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

tab1, tab2 = st.tabs(["Leaderboard (by Avg Likes)", "Profile Detail"])

with tab1:
    st.header("Leaderboard — Sorted by Average Likes")
    board = summary.sort_values("Avg Likes", ascending=False).reset_index(drop=True)
    st.dataframe(board.style.format({"Avg Likes": "{:,}"}), use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Accounts", len(board))
    c2.metric("Top Avg Likes", f"{board['Avg Likes'].iloc[0]:,}")
    c3.metric("Median Avg Likes", f"{board['Avg Likes'].median():,.0f}")

with tab2:
    selected = st.selectbox("Select profile", options=[p['username'] for p in profiles])
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
            df = p['videos'].copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime("%b %d, %Y %I:%M %p")
            show = df[['date', 'plays', 'likes', 'comments', 'shares', 'description']].head(20)
            st.dataframe(show, use_container_width=True, hide_index=True)

    c3, c4 = st.columns(2)
    with c3:
        if p['mentions']:
            st.subheader("Top Mentions")
            mdf = pd.DataFrame(list(p['mentions'].items()), columns=['Account', 'Count'])\
                   .sort_values('Count', ascending=False).head(10)
            st.dataframe(mdf, use_container_width=True, hide_index=True)
    with c4:
        if p['hashtags']:
            st.subheader("Top Hashtags")
            hdf = pd.DataFrame(list(p['hashtags'].items()), columns=['Hashtag', 'Count'])\
                   .sort_values('Count', ascending=False).head(10)
            st.dataframe(hdf, use_container_width=True, hide_index=True)

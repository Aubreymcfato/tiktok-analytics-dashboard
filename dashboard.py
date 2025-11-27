import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

# CHANGE THIS DATE EVERY TIME YOU DOWNLOAD NEW DATA
DOWNLOAD_DATE = "2025-11-27"   # ← UPDATE THIS!

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

def parse_tiktok_csv(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        metrics = {}
        videos = []
        mentions = {}
        hashtags = {}
        current_section = None

        for line in lines:
            # Skip empty lines
            if not line or line == ',':
                continue

            # === HEADER METRICS ===
            if line.startswith("Username,"):
                metrics['username'] = line.split(",", 1)[1].strip()
            elif line.startswith("Nickname,"):
                metrics['nickname'] = line.split(",", 1)[1].strip()
            elif line.startswith("Follower Count,"):
                metrics['follower_count'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Views,"):
                metrics['avg_views'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Likes,"):
                metrics['avg_likes'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Comments,"):
                metrics['avg_comments'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif line.startswith("Average Shares,"):
                metrics['avg_shares'] = int(line.split(",", 1)[1].replace(",", "").strip())
            elif "Engagement Rate" in line:
                metrics['engagement_rate'] = float(line.split(",", 1)[1].strip().replace("%", ""))

            # === SECTION SWITCHES ===
            elif line.startswith("Videos"):
                current_section = "videos"
                continue
            elif line.startswith("Mentions"):
                current_section = "mentions"
                continue
            elif line.startswith("Hashtags"):
                current_section = "hashtags"
                continue

            # === VIDEOS SECTION (FIXED!) ===
            elif current_section == "videos":
                if line.startswith("Date,Plays"):  # header
                    continue
                # Split only once from the right to preserve commas in description
                parts = line.rsplit(",", 4)  # last 4 fields: Likes, Comments, Shares, Description
                if len(parts) >= 5:
                    rest = parts[0]
                    likes = int(parts[1].strip().replace(",", ""))
                    comments = int(parts[2].strip().replace(",", ""))
                    shares = int(parts[3].strip().replace(",", ""))
                    description = parts[4].strip().strip('"')

                    # Extract plays from the remaining part
                    plays_part = rest.rsplit(",", 1)[0] if "," in rest.rsplit(",", 1)[0] else rest
                    plays_str = plays_part.split(",")[-1].strip().replace(",", "")
                    try:
                        plays = int(plays_str)
                    except:
                        plays = 0

                    videos.append({
                        'date': rest.split(",", 1)[0] if "," in rest else rest,
                        'plays': plays,
                        'likes': likes,
                        'comments': comments,
                        'shares': shares,
                        'description': description
                    })

            # === MENTIONS ===
            elif current_section == "mentions" and "," in line:
                mention, count = line.rsplit(",", 1)
                mentions[mention.strip("@").strip()] = int(count.strip())

            # === HASHTAGS ===
            elif current_section == "hashtags" and "," in line:
                hashtag, count = line.rsplit(",", 1)
                hashtags[hashtag.strip("#").strip()] = int(count.strip())

        return {
            'nickname': metrics.get('nickname', 'Unknown'),
            'follower_count': metrics.get('follower_count', 0),
            'avg_views': metrics.get('avg_views', 0),
            'avg_likes': metrics.get('avg_likes', 0),
            'avg_comments': metrics.get('avg_comments', 0),
            'avg_shares': metrics.get('avg_shares', 0),
            'engagement_rate': metrics.get('engagement_rate', 0),
            'videos': pd.DataFrame(videos),
            'mentions': mentions,
            'hashtags': hashtags
        }
    except Exception as e:
        st.error(f"Error parsing {os.path.basename(file_path)}: {e}")
        return None

# ====================== STREAMLIT APP ======================
st.set_page_config(page_title="TikTok Leaderboard", layout="wide")
st.title("TikTok Analytics Dashboard")
st.caption(f"Data downloaded on: **{DOWNLOAD_DATE}**")

# Auto-create data folder if missing
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Sidebar upload (great for testing on Streamlit Cloud)
uploaded = st.sidebar.file_uploader("Upload new CSVs (optional)", accept_multiple_files=True, type="csv")
if uploaded:
    for file in uploaded:
        with open(os.path.join(DATA_DIR, file.name), "wb") as f:
            f.write(file.getbuffer())
    st.sidebar.success("Files uploaded! Refreshing...")

# Load data
profiles = load_all_data()

if not profiles:
    st.warning("No data found. Put your `*_tiktok_stats.csv` files in the `data/` folder.")
    st.stop()

# Summary table
summary_df = pd.DataFrame([{
    'Username': p['username'],
    'Nickname': p['nickname'],
    'Followers': f"{p['follower_count']:,}",
    'Avg Likes': p['avg_likes'],
    'Avg Comments': p['avg_comments'],
    'Avg Shares': p['avg_shares'],
    'Engagement %': round(p['engagement_rate'], 2),
    'Download Date': p['download_date']
} for p in profiles])

# Tabs
tab1, tab2 = st.tabs(["Leaderboard (by Avg Likes)", "Profile Explorer"])

with tab1:
    st.header("Leaderboard – Sorted by Average Likes")
    leaderboard = summary_df.sort_values("Avg Likes", ascending=False).reset_index(drop=True)
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Accounts", len(leaderboard))
    with col2:
        st.metric("Top Avg Likes", leaderboard["Avg Likes"].iloc[0])
    with col3:
        st.metric("Median Avg Likes", int(leaderboard["Avg Likes"].median()))

with tab2:
    st.header("Explore Individual Profile")
    selected = st.selectbox("Choose account:", options=[p['username'] for p in profiles])
    profile = next(p for p in profiles if p['username'] == selected)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"@{selected}")
        st.write(f"**Name:** {profile['nickname']}")
        st.write(f"**Followers:** {profile['follower_count']:,}")
        st.write(f"**Data from:** {profile['download_date']}")

        st.metric("Average Likes", profile['avg_likes'])
        st.metric("Average Comments", profile['avg_comments'])
        st.metric("Average Shares", profile['avg_shares'])
        st.metric("Engagement Rate", f"{profile['engagement_rate']:.2f}%")

    with col2:
        if not profile['videos'].empty:
            st.subheader("Latest Videos")
            display_videos = profile['videos'].copy()
            display_videos['date'] = pd.to_datetime(display_videos['date'], errors='coerce').dt.strftime("%b %d")
            st.dataframe(display_videos[['date', 'plays', 'likes', 'comments', 'shares', 'description']].head(15),
                         use_container_width=True, hide_index=True)

    col3, col4 = st.columns(2)
    with col3:
        if profile['mentions']:
            st.subheader("Top Mentions")
            mentions_df = pd.DataFrame(list(profile['mentions'].items()), columns=['Account', 'Mentions'])\
                          .sort_values('Mentions', ascending=False).head(10)
            st.dataframe(mentions_df, use_container_width=True, hide_index=True)

    with col4:
        if profile['hashtags']:
            st.subheader("Top Hashtags")
            hashtags_df = pd.DataFrame(list(profile['hashtags'].items()), columns=['Hashtag', 'Count'])\
                          .sort_values('Count', ascending=False).head(10)
            st.dataframe(hashtags_df, use_container_width=True, hide_index=True)

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import glob
import io  # For handling uploaded files in cloud

# Hardcoded download date (change this as needed for each run)
DOWNLOAD_DATE = "2025-11-14"

# Directory containing the CSV files (assumes files named like {username}_tiktok_stats.csv)
DATA_DIR = "./data"  # Adjust if your CSVs are elsewhere

@st.cache_data
def load_all_data():
    """
    Loads and parses all CSV files in DATA_DIR, extracting key metrics.
    Returns a list of dicts with profile data.
    """
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
    """
    Parses a single TikTok stats CSV file.
    Extracts key metrics like Average Likes, Comments, etc.
    Returns a dict with the data or None if parsing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        metrics = {}
        current_section = None
        videos = []
        mentions = {}
        hashtags = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Username,"):
                metrics['username'] = line.split(",", 1)[1].strip()
            elif line.startswith("Nickname,"):
                metrics['nickname'] = line.split(",", 1)[1].strip()
            elif line.startswith("Follower Count,"):
                metrics['follower_count'] = int(line.split(",", 1)[1].strip())
            elif line.startswith("Average Views,"):
                metrics['avg_views'] = int(line.split(",", 1)[1].strip())
            elif line.startswith("Average Likes,"):
                metrics['avg_likes'] = int(line.split(",", 1)[1].strip())
            elif line.startswith("Average Comments,"):
                metrics['avg_comments'] = int(line.split(",", 1)[1].strip())
            elif line.startswith("Average Shares,"):
                metrics['avg_shares'] = int(line.split(",", 1)[1].strip())
            elif line.startswith("Total Engagement Rate,"):
                metrics['engagement_rate'] = float(line.split(",", 1)[1].strip().replace("%", ""))
            elif line.startswith("Likes Rate,"):
                metrics['likes_rate'] = float(line.split(",", 1)[1].strip().replace("%", ""))
            elif line.startswith("Comments Rate,"):
                metrics['comments_rate'] = float(line.split(",", 1)[1].strip().replace("%", ""))
            elif line.startswith("Shares Rate,"):
                metrics['shares_rate'] = float(line.split(",", 1)[1].strip().replace("%", ""))
            elif line.startswith("Videos"):
                current_section = "videos"
            elif current_section == "videos" and line.startswith("Date,"):
                # Skip header
                continue
            elif current_section == "videos":
                parts = line.split(",", 5)  # Date,Plays,Likes,Comments,Shares,Description
                if len(parts) >= 5:
                    date_str = parts[0].strip()
                    plays = int(parts[1].strip())
                    likes = int(parts[2].strip())
                    comments = int(parts[3].strip())
                    shares = int(parts[4].strip())
                    desc = parts[5].strip().strip('"') if len(parts) > 5 else ""
                    videos.append({
                        'date': date_str,
                        'plays': plays,
                        'likes': likes,
                        'comments': comments,
                        'shares': shares,
                        'description': desc
                    })
            elif line.startswith("Mentions"):
                current_section = "mentions"
            elif current_section == "mentions":
                if "," in line:
                    mention, count_str = line.split(",", 1)
                    mentions[mention.strip("@")] = int(count_str.strip())
            elif line.startswith("Hashtags"):
                current_section = "hashtags"
            elif current_section == "hashtags":
                if "," in line:
                    hashtag, count_str = line.split(",", 1)
                    hashtags[hashtag.strip("#")] = int(count_str.strip())
        
        # Store sections
        data = {
            'nickname': metrics.get('nickname', ''),
            'follower_count': metrics.get('follower_count', 0),
            'avg_views': metrics.get('avg_views', 0),
            'avg_likes': metrics.get('avg_likes', 0),
            'avg_comments': metrics.get('avg_comments', 0),
            'avg_shares': metrics.get('avg_shares', 0),
            'engagement_rate': metrics.get('engagement_rate', 0),
            'likes_rate': metrics.get('likes_rate', 0),
            'comments_rate': metrics.get('comments_rate', 0),
            'shares_rate': metrics.get('shares_rate', 0),
            'videos': pd.DataFrame(videos),
            'mentions': mentions,
            'hashtags': hashtags
        }
        return data
    except Exception as e:
        st.error(f"Error parsing {file_path}: {e}")
        return None

# Streamlit App
st.set_page_config(page_title="TikTok Analytics Dashboard", layout="wide")
st.title("TikTok Analytics Dashboard")
st.caption(f"Data downloaded on: {DOWNLOAD_DATE}")

# Option for cloud: Upload CSVs if data dir is empty
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

uploaded_files = st.sidebar.file_uploader("Upload CSV files (optional, for testing)", accept_multiple_files=True, type='csv')
if uploaded_files:
    for uploaded_file in uploaded_files:
        # Save uploaded file to data dir
        with open(os.path.join(DATA_DIR, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"Uploaded {uploaded_file.name}")

# Load data
profiles = load_all_data()

if not profiles:
    st.warning("No CSV files found in the data directory. Please add your *_tiktok_stats.csv files there or upload via sidebar.")
    st.stop()

# Create summary DataFrame for leaderboard (focus on key interactions)
summary_df = pd.DataFrame([
    {
        'Username': p['username'],
        'Nickname': p['nickname'],
        'Followers': p['follower_count'],
        'Avg Likes': p['avg_likes'],
        'Avg Comments': p['avg_comments'],
        'Avg Shares': p['avg_shares'],
        'Engagement Rate (%)': round(p['engagement_rate'], 2),
        'Likes Rate (%)': round(p['likes_rate'], 2),
        'Comments Rate (%)': round(p['comments_rate'], 2),
        'Shares Rate (%)': round(p['shares_rate'], 2),
        'Download Date': p['download_date']
    }
    for p in profiles
])

# Tabs
tab1, tab2 = st.tabs(["Leaderboard (by Avg Likes)", "Profile Details"])

with tab1:
    st.header("Leaderboard: Sorted by Average Likes")
    # Sort by Avg Likes descending
    leaderboard_df = summary_df.sort_values('Avg Likes', ascending=False).reset_index(drop=True)
    st.dataframe(leaderboard_df, use_container_width=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Profiles", len(leaderboard_df))
    with col2:
        st.metric("Top Avg Likes", leaderboard_df['Avg Likes'].max())
    with col3:
        st.metric("Avg Avg Likes", round(leaderboard_df['Avg Likes'].mean(), 1))
    with col4:
        st.metric("Total Followers", leaderboard_df['Followers'].sum())

with tab2:
    st.header("Individual Profile Details")
    selected_username = st.selectbox("Select Profile:", options=[p['username'] for p in profiles])
    
    if selected_username:
        profile = next(p for p in profiles if p['username'] == selected_username)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"@{selected_username}")
            st.write(f"**Nickname:** {profile['nickname']}")
            st.write(f"**Followers:** {profile['follower_count']:,}")
            st.write(f"**Download Date:** {profile['download_date']}")
        
        with col2:
            st.metric("Avg Likes", profile['avg_likes'])
            st.metric("Avg Comments", profile['avg_comments'])
            st.metric("Avg Shares", profile['avg_shares'])
            st.metric("Engagement Rate", f"{profile['engagement_rate']:.2f}%")
        
        # Videos
        if not profile['videos'].empty:
            st.subheader("Recent Videos")
            st.dataframe(profile['videos'][['date', 'plays', 'likes', 'comments', 'shares', 'description']].head(10), use_container_width=True)
        
        # Top Mentions and Hashtags
        st.subheader("Top Mentions")
        if profile['mentions']:
            mentions_df = pd.DataFrame(list(profile['mentions'].items()), columns=['Mention', 'Count']).sort_values('Count', ascending=False).head(10)
            st.dataframe(mentions_df, use_container_width=True)
        
        st.subheader("Top Hashtags")
        if profile['hashtags']:
            hashtags_df = pd.DataFrame(list(profile['hashtags'].items()), columns=['Hashtag', 'Count']).sort_values('Count', ascending=False).head(10)
            st.dataframe(hashtags_df, use_container_width=True)

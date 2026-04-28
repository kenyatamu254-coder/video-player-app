import os
import subprocess
import time
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
TOKEN = '8738639794:AAHhkDQMRQQ9yCpnx1IiG5RKCwu7PwC7qYc' 
CHANNEL_ID = -1003921891307 
GITHUB_REPO_PATH = r'C:\Users\director\Documents\video-player-app' 
MINI_APP_URL = 'https://kenyatamu254-coder.github.io/video-player-app/'
BOT_USERNAME = "Kenya_Tamu_Bot"  # Your bot username added here

bot = Bot(token=TOKEN)

def get_duration(file_path):
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

async def process_video(video_path):
    # Generate a unique ID for this video batch
    video_id = f"vid{int(time.time())}"
    segments_dir = os.path.join(GITHUB_REPO_PATH, "segments")
    
    if not os.path.exists(segments_dir):
        os.makedirs(segments_dir)

    print(f"🚀 Processing: {video_path}")

    # Split into 30s segments
    subprocess.call([
        'ffmpeg', '-i', video_path, 
        '-f', 'segment', '-segment_time', '30', 
        '-g', '30', '-c', 'copy', 
        os.path.join(segments_dir, f"{video_id}_part_%03d.mp4")
    ])

    # Get the list of segments we just created
    parts = sorted([f for f in os.listdir(segments_dir) if f.startswith(video_id)])
    
    # Push to GitHub
    print("☁️ Syncing with GitHub...")
    os.chdir(GITHUB_REPO_PATH)
    try:
        print("🔄 Pulling latest changes from GitHub...")
        subprocess.run(['git', 'pull', 'origin', 'main'], check=False)
        
        print("📤 Uploading new segments...")
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f'Segments for {video_id}'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
    except Exception as e:
        print(f"❌ Git Upload Failed: {e}")
        return

    # Send to Telegram Channel
    print("📤 Posting to Telegram...")
    for i, part_file in enumerate(parts):
        # Extract part number
        raw_part_num = part_file.split('_part_')[-1].replace('.mp4', '')
        part_num_clean = str(int(raw_part_num))
        
        # --- FIX: DIRECT MINI APP DEEP LINK ---
        # This format is allowed in channels and opens the Mini App panel
        deep_link = f"https://t.me/{BOT_USERNAME}/app?startapp=vid_{video_id}_part_{part_num_clean}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🎬 Watch Inside Bot", 
                    url=deep_link  # Use URL instead of WebAppInfo for Channel compatibility
                )
            ]]
        )
        
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"📺 **Part {i+1}**\n\nTap below to watch inside the bot! ⚡️",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            print(f"✅ Posted Part {i+1}/{len(parts)}")
            
            # --- ANTI-FLOOD DELAY ---
            await asyncio.sleep(2.5) 
            
        except Exception as e:
            print(f"⚠️ Error sending part {i+1}: {e}")
            if "RetryAfter" in str(e):
                print("⏳ Flood limit hit. Sleeping for 30s...")
                await asyncio.sleep(30)
    
    await bot.session.close()
    print(f"✅ All tasks complete! Users can now watch on @{BOT_USERNAME}")

if __name__ == "__main__":
    file_to_split = "my_video.mp4" 
    target_path = os.path.join(GITHUB_REPO_PATH, file_to_split)
    
    if os.path.exists(target_path):
        asyncio.run(process_video(target_path))
    else:
        print(f"❌ Error: Could not find '{file_to_split}' in {GITHUB_REPO_PATH}")
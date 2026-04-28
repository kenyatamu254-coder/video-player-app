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
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f'Segments for {video_id}'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
    except Exception as e:
        print(f"❌ Git Upload Failed: {e}")
        return

    # Send to Telegram Channel
    print("📤 Posting to Telegram...")
    for i, part_file in enumerate(parts):
        # Extract part number (e.g., 000, 001) - keeping it raw for the URL
        # Our HTML padStart fix handles the rest
        raw_part_num = part_file.split('_part_')[-1].replace('.mp4', '')
        
        # We convert to int and back to string to remove leading zeros for the URL 
        # (e.g., 001 becomes 1), which is cleaner for the URL parameters
        part_num_clean = str(int(raw_part_num))
        
        link = f"{MINI_APP_URL}?vid={video_id}&part={part_num_clean}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🔓 Watch Now", url=link)
            ]]
        )
        
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"🎬 **Part {i+1}**\n\nTap below to watch this segment! ⚡️",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            print(f"✅ Posted Part {i+1}/{len(parts)}")
            
            # --- ANTI-FLOOD DELAY ---
            # Telegram allows ~20 messages per minute in channels. 
            # 2-3 seconds is the "sweet spot" for safety.
            await asyncio.sleep(2.5) 
            
        except Exception as e:
            print(f"⚠️ Error sending part {i+1}: {e}")
            # If we hit a serious flood error, wait longer
            if "RetryAfter" in str(e):
                await asyncio.sleep(30)
    
    await bot.session.close()
    print("✅ All tasks complete! Check your Telegram channel.")

if __name__ == "__main__":
    file_to_split = "my_video.mp4" 
    target_path = os.path.join(GITHUB_REPO_PATH, file_to_split)
    
    if os.path.exists(target_path):
        asyncio.run(process_video(target_path))
    else:
        print(f"❌ Error: Could not find '{file_to_split}' in {GITHUB_REPO_PATH}")
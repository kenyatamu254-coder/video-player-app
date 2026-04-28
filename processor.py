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
        part_num = part_file.split('_part_')[-1].replace('.mp4', '')
        link = f"{MINI_APP_URL}?vid={video_id}&part={part_num}"
        
        # Standard URL button - very reliable for Channels
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🔓 Watch Now", url=link)
            ]]
        )
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🎬 **Part {i+1}**\n\nTap below to watch this segment! ⚡️",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await bot.session.close()
    print("✅ Done! Check your Telegram channel.")

if __name__ == "__main__":
    file_to_split = "my_video.mp4" 
    target_path = os.path.join(GITHUB_REPO_PATH, file_to_split)
    
    if os.path.exists(target_path):
        asyncio.run(process_video(target_path))
    else:
        print(f"❌ Error: Could not find '{file_to_split}'")
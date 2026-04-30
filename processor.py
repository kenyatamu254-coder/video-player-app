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
BOT_USERNAME = "Kenya_Tamu_Bot" 

bot = Bot(token=TOKEN)

async def process_video(video_path):
    # FORCE LOWERCASE for the ID to prevent GitHub 404 Case-Sensitivity errors
    video_id = f"vid{int(time.time())}".lower()
    segments_dir = os.path.join(GITHUB_REPO_PATH, "segments")
    
    if not os.path.exists(segments_dir):
        os.makedirs(segments_dir)

    print(f"🚀 Processing: {video_path}")

    # Split into 30s segments with 3-digit padding (001, 002...)
    # This matches the HTML's padStart(3, '0')
    output_pattern = os.path.join(segments_dir, f"{video_id}_part_%03d.mp4")
    
    subprocess.call([
        'ffmpeg', '-i', video_path, 
        '-f', 'segment', '-segment_time', '30', 
        '-g', '30', '-c:v', 'libx264', '-crf', '23', '-c:a', 'aac', # Re-encoding slightly for better web compatibility
        output_pattern
    ])

    # Get the list of segments we just created
    parts = sorted([f for f in os.listdir(segments_dir) if f.startswith(video_id)])
    
    if not parts:
        print("❌ Error: No segments were created. Check ffmpeg.")
        return

    # Push to GitHub
    print("☁️ Syncing with GitHub...")
    os.chdir(GITHUB_REPO_PATH)
    try:
        subprocess.run(['git', 'pull', 'origin', 'main'], check=False)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f'Segments for {video_id}'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("✅ GitHub Sync Complete!")
    except Exception as e:
        print(f"❌ Git Upload Failed: {e}")
        return

    # Post to Telegram Channel
    print("📤 Posting to Telegram...")
    for i, part_file in enumerate(parts):
        # Extract the clean part number for the deep link
        # Example: vid123_part_001.mp4 -> 1
        raw_part_num = part_file.split('_part_')[-1].replace('.mp4', '')
        part_num_clean = str(int(raw_part_num))
        
        # Deep link format: startapp=vid_vid12345_part_1
        deep_link = f"https://t.me/{BOT_USERNAME}/app?startapp=vid_{video_id}_part_{part_num_clean}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🎬 Watch Inside Bot", url=deep_link)
            ]]
        )
        
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"📺 **Part {i+1}**\n⚡️ Optimized for Mobile",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            print(f"✅ Posted Part {i+1}/{len(parts)}")
            await asyncio.sleep(2.5) 
            
        except Exception as e:
            print(f"⚠️ Error sending part {i+1}: {e}")

    await bot.session.close()
    print(f"🏁 Finished! Users can now watch on @{BOT_USERNAME}")

if __name__ == "__main__":
    file_to_split = "my_video.mp4" 
    target_path = os.path.join(GITHUB_REPO_PATH, file_to_split)
    
    if os.path.exists(target_path):
        asyncio.run(process_video(target_path))
    else:
        print(f"❌ Error: {file_to_split} not found in {GITHUB_REPO_PATH}")
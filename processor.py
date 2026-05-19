import os
import subprocess
import time
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()  # This loads the variables from your .env file

# Pull the token from your hidden file instead of hardcoding it
TOKEN = os.getenv('BOT_TOKEN') 
CHANNEL_ID = -1003921891307 
GITHUB_REPO_PATH = r'C:\Users\director\Documents\video-player-app' 
BOT_USERNAME = "Kenya_Tamu_Bot" 

# Safety check: make sure the token actually loaded
if not TOKEN:
    print("❌ Error: Could not find BOT_TOKEN in .env file!")
    exit()

bot = Bot(token=TOKEN)

async def process_video(video_path):
    # FORCE LOWERCASE for the ID to prevent GitHub 404 Case-Sensitivity errors
    video_id = f"vid{int(time.time())}".lower()
    segments_dir = os.path.join(GITHUB_REPO_PATH, "segments")
    
    if not os.path.exists(segments_dir):
        os.makedirs(segments_dir)

    print(f"🚀 Processing: {video_path}")

    # Split into 30s segments with 3-digit padding (001, 002...)
    output_pattern = os.path.join(segments_dir, f"{video_id}_part_%03d.mp4")

    # --- THE FIXED & OPTIMIZED FFMPEG COMMAND ---
    ffmpeg_command = [
        'ffmpeg', 
        '-y',                            # Overwrite existing files
        '-i', video_path, 
        '-f', 'segment', 
        '-segment_time', '30', 
        '-g', '60',                      # Keyframe every 2 seconds (assuming 30fps)
        '-sc_threshold', '0',            # Force exact cuts at 30 seconds
        '-c:v', 'libx264', 
        '-pix_fmt', 'yuv420p',           # Maximum compatibility for mobile
        '-crf', '28',                    # Balanced quality/file size for mobile data
        '-c:a', 'aac', 
        '-b:a', '128k', 
        '-ac', '2',                      # Ensure stereo audio
        '-movflags', '+faststart+frag_keyframe+empty_moov+default_base_moof', 
        output_pattern
    ]

    try:
        print("🎬 Running optimized video splitting...")
        # FIXED: Added capture_output and text to prevent terminal deadlocks on large files
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        print("✅ Video segments created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed with error code: {e.returncode}")
        print(f"Error details: {e.stderr}")
        return

    # Get the list of segments we just created
    parts = sorted([f for f in os.listdir(segments_dir) if f.startswith(video_id) and f.endswith('.mp4')])
    
    if not parts:
        print("❌ Error: No segments were created. Check ffmpeg.")
        return

    # --- NEW: GENERATE UNIQUE PRO-QUALITY THUMBNAILS FOR EVERY PART ---
    print("📸 Generating high-quality unique thumbnails for each part...")
    part_thumbnails = {} # Dictionary to keep track of which thumbnail goes to which part
    
    for part_file in parts:
        part_path = os.path.join(segments_dir, part_file)
        thumb_name = part_file.replace('.mp4', '_thumb.jpg')
        thumb_path = os.path.join(segments_dir, thumb_name)
        
        # Grab frame at the 2-second mark of each segment with highest JPEG quality (-q:v 1)
        thumb_command = [
            'ffmpeg', 
            '-y', 
            '-ss', '00:00:02',  
            '-i', part_path, 
            '-vframes', '1',    
            '-q:v', '1',        # 1 is the highest possible quality setting for JPEGs
            thumb_path
        ]
        
        try:
            subprocess.run(thumb_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            part_thumbnails[part_file] = thumb_path
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to generate thumbnail for {part_file}.")
            part_thumbnails[part_file] = None

    print("✅ All unique thumbnails created!")

    # Push to GitHub
    print("☁️ Syncing with GitHub...")
    os.chdir(GITHUB_REPO_PATH)
    try:
        subprocess.run(['git', 'pull', 'origin', 'main'], check=False)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f'Segments and unique thumbs for {video_id}'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("✅ GitHub Sync Complete!")
    except Exception as e:
        print(f"❌ Git Upload Failed: {e}")
        return

    # Post to Telegram Channel
    print("📤 Posting to Telegram...")
    for i, part_file in enumerate(parts):
        # Extract the clean part number for the deep link
        raw_part_num = part_file.split('_part_')[-1].replace('.mp4', '')
        part_num_clean = str(int(raw_part_num))
        
        # Using /play to match your Telegram Direct Link settings
        deep_link = f"https://t.me/{BOT_USERNAME}/play?startapp=vid_{video_id}_part_{part_num_clean}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🎬 Watch Inside Bot", url=deep_link)
            ]]
        )
        
        try:
            # Get the specific thumbnail for this specific part
            current_thumb_path = part_thumbnails.get(part_file)
            
            # Check if thumbnail exists, send photo if yes, message if no
            if current_thumb_path and os.path.exists(current_thumb_path):
                photo = FSInputFile(current_thumb_path)
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photo,
                    caption=f"📺 **Part {i+1}**\n⚡️ Optimized for Mobile",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=f"📺 **Part {i+1}**\n⚡️ Optimized for Mobile",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
            print(f"✅ Posted Part {i+1}/{len(parts)} with unique thumbnail")
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
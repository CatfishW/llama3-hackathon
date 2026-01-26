import re
import os
import hashlib
import soundfile as sf

MAIN_PY = "/data/Yanlai/llama3-hackathon/llama3/Hackathon/prompt-portal/AgentSkillsAnimationExplain/main_2.py"
AUDIO_DIR = "/data/Yanlai/llama3-hackathon/llama3/Hackathon/prompt-portal/AgentSkillsAnimationExplain/audio"

def get_audio_duration(file_path):
    try:
        data, samplerate = sf.read(file_path)
        return len(data) / samplerate
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def main():
    if not os.path.exists(MAIN_PY):
        print("main.py not found")
        return

    with open(MAIN_PY, 'r') as f:
        content = f.read()

    # Regex to find play_segment("text", duration, ...)
    # Group 1: full call, Group 2: text, Group 3: duration, Group 4: optional extras
    pattern = r'(play_segment\(\s*\"(.*?)\"\s*,\s*(\d+(\.\d+)?)\s*(,\s*wait=(True|False))?\s*\))'
    
    matches = list(re.finditer(pattern, content, re.DOTALL))
    print(f"Found {len(matches)} play_segment calls.")

    new_content = content
    offset = 0

    for match in matches:
        full_call = match.group(1)
        text = match.group(2).strip()
        current_duration_val = float(match.group(3))
        extras = match.group(5) if match.group(5) else ""
        
        txt_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        audio_path = os.path.join(AUDIO_DIR, f"{txt_hash}.ogg")
        
        if os.path.exists(audio_path):
            actual_duration = get_audio_duration(audio_path)
            if actual_duration:
                # Use 0.4s buffer
                new_duration = round(actual_duration + 0.4, 1)
                
                # Construct new call
                new_call = f'play_segment("{text}", {new_duration}{extras})'
                
                if abs(current_duration_val - new_duration) > 0.05:
                    print(f"Updating: \"{text[:30]}...\" {current_duration_val} -> {new_duration}")
                
                start = match.start() + offset
                end = match.end() + offset
                
                new_content = new_content[:start] + new_call + new_content[end:]
                offset += len(new_call) - len(full_call)
            else:
                print(f"Could not get duration for {audio_path}")
        else:
            print(f"Audio file not found for hash {txt_hash} (Text: {text[:30]}...)")

    with open(MAIN_PY, 'w') as f:
        f.write(new_content)
    print("Optimization complete.")

if __name__ == "__main__":
    main()

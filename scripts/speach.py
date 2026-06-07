import threading
import sounddevice as sd
import numpy as np
from scripts import temporary
import re

# ===============================================================================
#     Simple-PDF-Player: TTS Engine
# ===============================================================================

pipeline = None

def get_pipeline():
    """Lazy-loads the Kokoro TTS pipeline so it doesn't slow down app startup."""
    global pipeline
    if pipeline is None:
        from kokoro import KPipeline
        # Explicit repo_id suppresses the warning and points to the cached files
        print("[*] Initializing Kokoro TTS Pipeline...")
        pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
        print("[*] Kokoro TTS Pipeline ready.")
    return pipeline

def split_into_chunks(text, max_chars=500):
    """Splits text into smaller chunks at sentence endings for smoother TTS playback."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks if chunks else [text]

def speak_text(text_chunk):
    """Synthesizes and plays text chunk. Blocks until playback is done."""
    try:
        pipe = get_pipeline()
        voice = temporary.app_state["voice"]
        speed = temporary.app_state["speed"]
        
        audio_chunks = []
        for graphemes, phonemes, audio in pipe(text_chunk, voice=voice, speed=speed):
            if temporary.app_state["stop_flag"]:
                return 0
            if audio is not None:
                audio_chunks.append(audio)
        
        if not audio_chunks:
            return len(text_chunk)
            
        import torch
        if isinstance(audio_chunks[0], torch.Tensor):
            audio_data = torch.cat(audio_chunks).cpu().numpy()
        elif isinstance(audio_chunks[0], np.ndarray):
            audio_data = np.concatenate(audio_chunks)
        else:
            audio_data = np.array(audio_chunks)
            
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        if temporary.app_state["stop_flag"]:
            return 0

        sd.play(audio_data, samplerate=24000)
        
        while sd.get_stream() is not None and sd.get_stream().active:
            if temporary.app_state["stop_flag"]:
                sd.stop()
                return 0
            sd.sleep(100)
            
        return len(text_chunk)
        
    except Exception as e:
        print(f"TTS Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

def start_playback():
    if not temporary.app_state["doc"]:
        return
        
    temporary.app_state["stop_flag"] = False
    temporary.app_state["is_playing"] = True
    temporary.app_state["is_paused"] = False
    
    def worker():
        while not temporary.app_state["stop_flag"]:
            page_idx = temporary.app_state["current_page"]
            if page_idx >= len(temporary.app_state["text_data"]):
                temporary.app_state["is_playing"] = False
                break
            
            page_data = temporary.app_state["text_data"][page_idx]
            remaining_text = page_data["text"][temporary.app_state["current_char_index"]:]
            
            if not remaining_text.strip():
                temporary.app_state["current_page"] += 1
                temporary.app_state["current_char_index"] = 0
                continue
            
            chunks = split_into_chunks(remaining_text)
            
            for chunk in chunks:
                if temporary.app_state["stop_flag"]:
                    break
                
                chars_spoken = speak_text(chunk)
                temporary.app_state["current_char_index"] += chars_spoken
                
            if temporary.app_state["current_char_index"] >= len(page_data["text"]):
                temporary.app_state["current_page"] += 1
                temporary.app_state["current_char_index"] = 0
                
    temporary.app_state["tts_thread"] = threading.Thread(target=worker, daemon=True)
    temporary.app_state["tts_thread"].start()

def pause_playback():
    """Pauses playback, holding the current position so it can be resumed."""
    temporary.app_state["stop_flag"] = True
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = True
    sd.stop()

def stop_playback():
    """Stops playback entirely and clears the paused state."""
    temporary.app_state["stop_flag"] = True
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = False
    sd.stop()
# ===============================================================================
#     Simple-PDF-Player: Temporary Globals
# ===============================================================================

app_state = {
    "pdf_path": None,
    "doc": None,
    "text_data": [],      # List of dicts: {"text": str, "chars": int, "words": int, "paragraphs": int, "is_chapter": bool}
    "current_page": 0,
    "current_char_index": 0,
    "is_playing": False,
    "is_paused": False,   # True when paused mid-playback (position is held, audio is stopped)
    "tts_thread": None,
    "stop_flag": False,
    "voice": "af_heart",
    "speed": 1.0,
    "totals": {"chars": 0, "words": 0, "paragraphs": 0, "pages": 0},
    
    # UI Window Dimensions (Adjust these to change the default player size)
    "window_width": 650,
    "window_height": 350
}
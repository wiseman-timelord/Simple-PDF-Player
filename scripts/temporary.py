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
    "_producer_thread": None,
    "stop_flag": False,
    "voice": "af_heart",
    "speed": 1.0,
    "totals": {"chars": 0, "words": 0, "paragraphs": 0, "pages": 0},
    
    # UI Window Dimensions
    "window_width": 740,
    "window_height": 350,

    # Playlist support
    "playlist": [],           # list of absolute PDF file paths
    "playlist_index": -1,     # currently selected / playing index in playlist (-1 = none)
    "playback_generation": 0, # incremented on every stop/load to invalidate stale TTS threads

    # Playlist window state (saved in program.json)
    "playlist_open": False,
    "playlist_width": 740,
    "playlist_height": 400,

    # TTS model lifecycle
    "models_loaded": False,   # True once Kokoro pipeline has been successfully created
    "models_loading": False,  # True while models are being loaded or unloaded
}

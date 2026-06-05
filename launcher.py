import sys
import os

# ===============================================================================
#     Simple-PDF-Player: Launcher
# ===============================================================================

# FIX for pythonw.exe: If running in silent mode (pythonw), sys.stdout and 
# sys.stderr are None. Attempting to print() will crash the app silently.
# This redirects any stray print statements to the void.
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

from nicegui import ui, app
from scripts import displays
from scripts import utility
from scripts import temporary

def main():
    # Load configuration (Loads window size from last session)
    utility.load_persistent()
    
    # Register shutdown sequence to run when the window closes
    @app.on_shutdown
    def handle_shutdown():
        try:
            # Attempt to capture the current window size before shutting down
            if hasattr(app.native, 'window') and app.native.window:
                temporary.app_state["window_width"] = app.native.window.width
                temporary.app_state["window_height"] = app.native.window.height
        except Exception:
            pass # Fallback to the loaded defaults if window object is already destroyed
        
        utility.shutdown()
    
    # Configure native window properties from temporary.py globals
    app.native.window_args['width'] = temporary.app_state.get("window_width", 650)
    app.native.window_args['height'] = temporary.app_state.get("window_height", 300)
    app.native.window_args['resizable'] = True  
    
    # Build the NiceGUI Interface
    displays.build_ui()
    
    # Run NiceGUI natively
    ui.run(title='Simple-PDF-Player', native=True, favicon='📄', dark=True)

# Note: NiceGUI requires "__mp_main__" when running in native mode 
if __name__ in {"__main__", "__mp_main__"}:
    main()
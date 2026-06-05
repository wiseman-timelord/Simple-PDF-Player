from nicegui import ui
from scripts import temporary
from scripts import speach
from scripts import utility

# ===============================================================================
#     Simple-PDF-Player: User Interface
# ===============================================================================

progress_label = None
play_button = None

def update_progress():
    if progress_label:
        progress_label.text = utility.get_progress()
        
    # Update play/pause icon dynamically
    if play_button:
        play_button.props(f'icon={"stop" if temporary.app_state["is_playing"] else "play_arrow"}')

def build_ui():
    global progress_label, play_button
    
    # Inject custom CSS to remove default body margins and prevent scrollbars
    ui.add_head_html('''<style>
        body { margin: 0; padding: 0; overflow: hidden; }
    </style>''')

    # Main Container - Centers contents vertically and horizontally.
    with ui.card().classes('w-full h-screen q-pa-md bg-grey-10 text-white column items-center justify-center no-shadow').style('border-radius: 0; box-sizing: border-box;'):
        
        # Titlebar
        ui.label('Simple-PDF-Player').classes('text-h5 text-weight-bold')

        # Progress Display
        progress_label = ui.label('C0/W0/p0/P0 / C0/W0/p0/P0').classes(
            'text-subtitle1 text-center q-mt-md q-pa-sm bg-grey-9 rounded'
        )

        # Controls
        with ui.row().classes('q-mt-md q-gutter-sm'):
            ui.button('⏮', on_click=skip_start).props('flat rounded size=lg color=white').tooltip('Skip Start')
            ui.button('⏹', on_click=stop).props('flat rounded size=lg color=white').tooltip('Stop')
            
            play_button = ui.button(on_click=play_resume).props('flat rounded size=lg color=white icon=play_arrow').tooltip('Play/Resume')
            
            ui.button('📖', on_click=skip_chapter).props('flat rounded size=lg color=white').tooltip('Next Chapter')
            ui.button('📄', on_click=skip_page).props('flat rounded size=lg color=white').tooltip('Next Page')
            ui.button(icon='folder_open', on_click=open_file).props('flat rounded size=lg color=white').tooltip('Open File')
            ui.button(icon='settings', on_click=open_config).props('flat rounded size=lg color=white').tooltip('Settings')

    # UI Updater Timer (runs every 500ms to refresh progress string)
    ui.timer(0.5, update_progress)

def skip_start():
    speach.stop_playback()
    temporary.app_state["current_page"] = 0
    temporary.app_state["current_char_index"] = 0
    update_progress()

def stop():
    speach.stop_playback()

def play_resume():
    if not temporary.app_state["is_playing"]:
        speach.start_playback()

def skip_page():
    was_playing = temporary.app_state["is_playing"]
    speach.stop_playback()
    if temporary.app_state["current_page"] < len(temporary.app_state["text_data"]) - 1:
        temporary.app_state["current_page"] += 1
    temporary.app_state["current_char_index"] = 0
    if was_playing:
        speach.start_playback()

def skip_chapter():
    was_playing = temporary.app_state["is_playing"]
    speach.stop_playback()
    
    current = temporary.app_state["current_page"]
    for i in range(current + 1, len(temporary.app_state["text_data"])):
        if temporary.app_state["text_data"][i]["is_chapter"]:
            temporary.app_state["current_page"] = i
            temporary.app_state["current_char_index"] = 0
            break
    else:
        # If no next chapter, go to end
        temporary.app_state["current_page"] = len(temporary.app_state["text_data"]) - 1
        temporary.app_state["current_char_index"] = 0
        
    if was_playing:
        speach.start_playback()

async def open_file():
    from nicegui import run
    # Explicitly import filedialog from tkinter to avoid AttributeError
    def get_filepath():
        from tkinter import filedialog
        return filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        
    result = await run.io_bound(get_filepath)
    if result:
        utility.load_pdf(result)
        utility.save_persistent()
        update_progress()

def open_config():
    # Constrain dialog width so it fits the settings tightly
    with ui.dialog().props('persistent').style('width: 320px') as dialog, \
         ui.card().classes('bg-grey-10 text-white q-pa-md').style('border-radius: 10px; width: 100%'):
        
        ui.label("Configuration").classes('text-h6 text-center w-full')
        
        # Use no-wrap to keep label and dropdown on the same line
        with ui.row().classes('w-full items-center q-mt-md no-wrap'):
            ui.label("Voice:").classes('text-weight-bold').style('min-width: 50px')
            voice_options = ['af_heart', 'af_bella', 'af_nicole', 'am_adam', 'am_michael']
            # Dropdown fills remaining space
            voice_select = ui.select(voice_options, value=temporary.app_state["voice"]).classes('w-full bg-grey-9')
            
        with ui.row().classes('w-full items-center q-mt-sm no-wrap'):
            ui.label("Speed:").classes('text-weight-bold').style('min-width: 50px')
            speed_options = ['0.5x', '0.75x', '1.0x', '1.25x', '1.5x', '2.0x']
            speed_select = ui.select(speed_options, value=f'{temporary.app_state["speed"]}x').classes('w-full bg-grey-9')
        
        with ui.row().classes('w-full justify-end q-mt-md'):
            ui.button('Cancel', on_click=dialog.close).props('flat color=white')
            ui.button('Save', on_click=lambda: save_config(voice_select.value, speed_select.value, dialog)).props('color=primary')
        
        dialog.open()

def save_config(voice, speed_str, dialog):
    temporary.app_state["voice"] = voice
    temporary.app_state["speed"] = float(speed_str.replace('x', ''))
    utility.save_persistent()
    dialog.close()
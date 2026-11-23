from nicegui import ui
from scripts import temporary
from scripts import speach
from scripts import utility
import os

# ===============================================================================
#     Simple-PDF-Player: User Interface
# ===============================================================================

progress_label = None
filename_label = None
play_button = None
playlist_dialog = None
playlist_list_container = None

def _status_callback(msg):
    """Called by speach during model load/unload so the filename label updates."""
    if not filename_label:
        return
    if msg == "loading":
        filename_label.text = "Loading TTS Models..."
    elif msg == "unloading":
        filename_label.text = "Unloading TTS Models..."
    elif msg == "standby":
        filename_label.text = "Standby Mode, Models Unloaded"
    elif msg == "ready":
        # After load we fall back to the normal filename display
        update_filename()
    elif msg == "error":
        filename_label.text = "TTS Model Load Failed"
    # Force UI refresh if possible
    try:
        filename_label.update()
    except Exception:
        pass

def update_filename():
    """Refresh the main status / filename line according to current state."""
    if not filename_label:
        return

    # Highest priority: explicit loading / unloading
    if temporary.app_state.get("models_loading"):
        # _status_callback already set the text; don't overwrite
        return

    # Models not loaded and nothing playing → standby
    if not temporary.app_state.get("models_loaded") and not temporary.app_state.get("is_playing") and not temporary.app_state.get("is_paused"):
        filename_label.text = "Standby Mode, Models Unloaded"
        return

    # Otherwise show the current PDF name (or "No file loaded")
    path = temporary.app_state.get("pdf_path")
    if path:
        name = os.path.splitext(os.path.basename(path))[0]
        truncated = name[:50] + '…' if len(name) > 50 else name
        filename_label.text = truncated
    else:
        filename_label.text = 'No file loaded'

def update_progress():
    if progress_label:
        progress_label.text = utility.get_progress()
        
    # Update play/pause icon dynamically
    if play_button:
        if temporary.app_state["is_playing"]:
            play_button.props('icon=pause color=white')
        elif temporary.app_state["is_paused"]:
            play_button.props('icon=play_arrow color=amber')
        else:
            play_button.props('icon=play_arrow color=white')

    # Keep the status line consistent
    update_filename()

def build_ui():
    global progress_label, filename_label, play_button
    
    ui.add_head_html('''<style>
        body { margin: 0; padding: 0; overflow: hidden; }
        .playlist-item { cursor: pointer; padding: 6px 10px; border-radius: 4px; }
        .playlist-item:hover { background: rgba(255,255,255,0.08); }
        .playlist-item.selected { background: rgba(33,150,243,0.35); }
        .playlist-drop-zone { border: 2px dashed #555; border-radius: 8px; min-height: 80px;
                             display: flex; align-items: center; justify-content: center;
                             color: #888; transition: border-color 0.2s; }
        .playlist-drop-zone.drag-over { border-color: #2196f3; color: #2196f3; }
    </style>''')

    with ui.card().classes('w-full h-screen q-pa-md bg-grey-10 text-white column items-center justify-center no-shadow').style('border-radius: 0; box-sizing: border-box;'):
        
        ui.label('Simple-PDF-Player').classes('text-h5 text-weight-bold')

        filename_label = ui.label('Standby Mode, Models Unloaded').classes(
            'text-subtitle1 text-center text-grey-8'
        )

        progress_label = ui.label('C0/W0/p0/P0 / C0/W0/p0/P0').classes(
            'text-subtitle1 text-center q-mt-md q-pa-sm bg-grey-8 rounded'
        )

        # Controls: Skip Start, Stop, Play, Next Page, Next Chapter, Open, Playlist, Settings
        with ui.row().classes('q-mt-md q-gutter-sm'):
            ui.button('⏮', on_click=skip_start).props('flat rounded size=md color=white').tooltip('Skip Start')
            ui.button('⏹', on_click=stop).props('flat rounded size=md color=white').tooltip('Stop')
            
            play_button = ui.button(on_click=play_pause).props('flat rounded size=md color=white icon=play_arrow').tooltip('Play / Pause')
            
            ui.button('📄', on_click=skip_page).props('flat rounded size=md color=white').tooltip('Next Page')
            ui.button('📖', on_click=skip_chapter).props('flat rounded size=md color=white').tooltip('Next Chapter')
            
            ui.button(icon='folder_open', on_click=open_file).props('flat rounded size=md color=white').tooltip('Open File')
            ui.button(icon='playlist_play', on_click=open_playlist).props('flat rounded size=md color=white').tooltip('Playlist')
            ui.button(icon='settings', on_click=open_config).props('flat rounded size=md color=white').tooltip('Settings')

    ui.timer(0.5, update_progress)

    # Restore playlist window if it was open last session
    if temporary.app_state.get("playlist_open"):
        ui.timer(0.8, open_playlist, once=True)

def skip_start():
    speach.stop_playback()
    temporary.app_state["current_page"] = 0
    temporary.app_state["current_char_index"] = 0
    update_progress()

def stop():
    speach.stop_playback()
    # After an explicit stop we leave models loaded (user may resume or play another).
    # Only unload when a document finishes and the playlist is exhausted.
    update_progress()

def _on_document_finished():
    """
    Called by the TTS consumer when the current PDF has been fully spoken.
    Advances to the next playlist item if any remain; otherwise unloads models.
    """
    pl = temporary.app_state.get("playlist", [])
    idx = temporary.app_state.get("playlist_index", -1)

    next_idx = idx + 1
    if 0 <= next_idx < len(pl):
        # More items remain → keep models loaded and start the next PDF
        next_path = pl[next_idx]
        temporary.app_state["playlist_index"] = next_idx
        utility.load_pdf(next_path)          # this also stops any residual playback
        utility.save_playlist()
        update_filename()
        update_progress()
        # Start next document (models stay loaded)
        speach.start_playback(status_callback=_status_callback,
                              on_document_finished=_on_document_finished)
    else:
        # Playlist exhausted → unload models and go to standby
        speach.unload_models_if_idle(status_callback=_status_callback)
        update_filename()
        update_progress()

def play_pause():
    """Toggles between playing and paused. If stopped, starts from current position."""
    if temporary.app_state["is_playing"]:
        speach.pause_playback()
    else:
        # Will load models if needed, then start
        speach.start_playback(status_callback=_status_callback,
                              on_document_finished=_on_document_finished)
    update_progress()

def skip_page():
    was_playing = temporary.app_state["is_playing"]
    speach.stop_playback()
    if temporary.app_state["current_page"] < len(temporary.app_state["text_data"]) - 1:
        temporary.app_state["current_page"] += 1
    temporary.app_state["current_char_index"] = 0
    if was_playing:
        speach.start_playback(status_callback=_status_callback,
                              on_document_finished=_on_document_finished)

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
        temporary.app_state["current_page"] = len(temporary.app_state["text_data"]) - 1
        temporary.app_state["current_char_index"] = 0
        
    if was_playing:
        speach.start_playback(status_callback=_status_callback,
                              on_document_finished=_on_document_finished)

async def open_file():
    from nicegui import run
    def get_filepath():
        from tkinter import filedialog
        return filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        
    result = await run.io_bound(get_filepath)
    if result:
        utility.load_pdf(result)
        if result not in temporary.app_state["playlist"]:
            temporary.app_state["playlist"].append(result)
            temporary.app_state["playlist_index"] = len(temporary.app_state["playlist"]) - 1
        utility.save_program()
        utility.save_playlist()
        update_filename()
        update_progress()
        refresh_playlist_list()

def open_config():
    with ui.dialog().props('persistent').style('width: 320px') as dialog, \
         ui.card().classes('bg-grey-10 text-white q-pa-md').style('border-radius: 10px; width: 100%'):
        
        ui.label("Configuration").classes('text-h6 text-center w-full')
        
        with ui.row().classes('w-full items-center q-mt-md no-wrap'):
            ui.label("Voice:").classes('text-weight-bold').style('min-width: 50px')
            voice_options = ['af_heart', 'af_bella', 'af_nicole', 'am_adam', 'am_michael']
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
    utility.save_program()
    dialog.close()


# ---------------------------------------------------------------------------
# Playlist window / dialog
# ---------------------------------------------------------------------------

def open_playlist():
    global playlist_dialog, playlist_list_container

    temporary.app_state["playlist_open"] = True
    utility.save_program()

    if playlist_dialog is not None:
        playlist_dialog.open()
        refresh_playlist_list()
        return

    # Use last saved playlist window size (falls back to main window width)
    w = temporary.app_state.get("playlist_width") or temporary.app_state.get("window_width", 740)
    h = temporary.app_state.get("playlist_height") or 400

    with ui.dialog().props('persistent maximized=false') as dialog, \
         ui.card().classes('bg-grey-10 text-white q-pa-none column').style(
             f'width: {w}px; min-height: {h}px; max-height: 90vh; border-radius: 8px; overflow: hidden;'):

        with ui.row().classes('w-full items-center q-px-md q-py-sm bg-grey-9').style('min-height: 40px;'):
            ui.label('Playlist').classes('text-h6 text-weight-bold')
            ui.space()
            def _close_playlist():
                temporary.app_state["playlist_open"] = False
                # Best-effort remember current size (dialog itself is not easily queryable)
                utility.save_program()
                dialog.close()
            ui.button(icon='close', on_click=_close_playlist).props('flat round dense color=white')

        with ui.scroll_area().classes('w-full col').style('flex: 1 1 auto; min-height: 120px;'):
            playlist_list_container = ui.column().classes('w-full q-pa-sm')

        with ui.element('div').classes('playlist-drop-zone q-ma-sm').style('height: 60px;'):
            ui.label('Drag & drop PDF files here  (or use Add)').classes('text-caption')

        with ui.row().classes('w-full items-center q-pa-sm bg-grey-9 q-gutter-sm').style('min-height: 48px;'):
            ui.button('Shuffle', on_click=shuffle_playlist).props('flat color=white')
            ui.button('Remove', on_click=remove_selected).props('flat color=white')
            ui.button('Clear', on_click=clear_playlist).props('flat color=white')
            ui.space()
            ui.button(icon='add', on_click=add_pdfs_to_playlist).props('flat round color=white').tooltip('Add PDF(s)')
            ui.button('Close', on_click=_close_playlist).props('flat color=white')

        playlist_dialog = dialog
        dialog.open()
        refresh_playlist_list()


def refresh_playlist_list():
    if playlist_list_container is None:
        return

    playlist_list_container.clear()
    playlist = temporary.app_state.get("playlist", [])
    current_idx = temporary.app_state.get("playlist_index", -1)

    with playlist_list_container:
        if not playlist:
            ui.label('Playlist is empty').classes('text-grey-6 q-pa-md text-center w-full')
            return

        for i, path in enumerate(playlist):
            name = os.path.basename(path)
            is_current = (i == current_idx)
            classes = 'playlist-item w-full'
            if is_current:
                classes += ' selected'

            def make_handlers(index=i, p=path):
                def on_click():
                    temporary.app_state["playlist_index"] = index
                    refresh_playlist_list()
                def on_dblclick():
                    temporary.app_state["playlist_index"] = index
                    utility.load_pdf(p)
                    utility.save_playlist()
                    update_filename()
                    update_progress()
                    refresh_playlist_list()
                    # Start playback (will load models if needed)
                    speach.start_playback(status_callback=_status_callback,
                                          on_document_finished=_on_document_finished)
                return on_click, on_dblclick

            click, dblclick = make_handlers()
            row = ui.row().classes(classes).style('cursor: pointer;')
            with row:
                indicator = '▶ ' if is_current else '   '
                ui.label(f'{indicator}{name}').classes('text-body2')
            row.on('click', click)
            row.on('dblclick', dblclick)

            try:
                playlist_list_container.make_sortable(
                    on_end=lambda e: _on_playlist_reorder(e)
                )
            except Exception:
                pass


def _on_playlist_reorder(e):
    try:
        old = e.args.get('oldIndex') if hasattr(e, 'args') else getattr(e, 'old_index', None)
        new = e.args.get('newIndex') if hasattr(e, 'args') else getattr(e, 'new_index', None)
        if old is None or new is None:
            return
        pl = temporary.app_state["playlist"]
        if 0 <= old < len(pl) and 0 <= new < len(pl):
            item = pl.pop(old)
            pl.insert(new, item)
            cur = temporary.app_state.get("playlist_index", -1)
            if cur == old:
                temporary.app_state["playlist_index"] = new
            elif old < cur <= new:
                temporary.app_state["playlist_index"] = cur - 1
            elif new <= cur < old:
                temporary.app_state["playlist_index"] = cur + 1
            utility.save_playlist()
            refresh_playlist_list()
    except Exception as ex:
        print(f"Reorder error: {ex}")


async def add_pdfs_to_playlist():
    from nicegui import run
    def get_filepaths():
        from tkinter import filedialog
        return filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
    results = await run.io_bound(get_filepaths)
    if results:
        added = 0
        for p in results:
            if p and p.lower().endswith('.pdf') and p not in temporary.app_state["playlist"]:
                temporary.app_state["playlist"].append(p)
                added += 1
        if added:
            utility.save_playlist()
            refresh_playlist_list()
            ui.notify(f'Added {added} PDF(s) to playlist')


def shuffle_playlist():
    import random
    pl = temporary.app_state["playlist"]
    if len(pl) < 2:
        return
    current_path = None
    idx = temporary.app_state.get("playlist_index", -1)
    if 0 <= idx < len(pl):
        current_path = pl[idx]
    random.shuffle(pl)
    if current_path:
        try:
            temporary.app_state["playlist_index"] = pl.index(current_path)
        except ValueError:
            temporary.app_state["playlist_index"] = -1
    utility.save_playlist()
    refresh_playlist_list()
    ui.notify('Playlist shuffled')


def remove_selected():
    idx = temporary.app_state.get("playlist_index", -1)
    pl = temporary.app_state["playlist"]
    if 0 <= idx < len(pl):
        removed = pl.pop(idx)
        if temporary.app_state["playlist_index"] >= len(pl):
            temporary.app_state["playlist_index"] = len(pl) - 1
        utility.save_playlist()
        refresh_playlist_list()
        ui.notify(f'Removed: {os.path.basename(removed)}')
    else:
        ui.notify('No item selected')


def clear_playlist():
    temporary.app_state["playlist"] = []
    temporary.app_state["playlist_index"] = -1
    utility.save_playlist()
    refresh_playlist_list()
    ui.notify('Playlist cleared')

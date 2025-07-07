# --- Standard Library Imports ---
import os
import sys
import re
import json
import threading
from datetime import datetime

# --- Third-Party Imports ---
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp


# --- Windows dark/light mode detection ---
def is_windows_dark_mode():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False

# --- Color palettes ---
LIGHT_COLORS = {
    "bg": "#fdfdfd",
    "fg": "#222",
    "entry_bg": "#e0e0e0",
    "entry_fg": "#222",
    "label_fg": "#222",
    "section_bg": "#f5f5f5",
    "section_border": "#e0e0e0",
    "button_bg": "#4CAF50",
    "button_fg": "white",
    "button_active": "#45a049",
    "progress_bg": "#4CAF50",
    "progress_trough": "#d0d0d0",
    "disabled_fg": "#888888",
    "highlight": "#4CAF50",
    "status_success": "#43a047",
    "status_error": "#e53935",
    "status_info": "#1976d2",
    "status_warn": "#ffa000"
}
DARK_COLORS = {
    "bg": "#23272e",
    "fg": "#f5f5f5",
    "entry_bg": "#2c313a",
    "entry_fg": "#f5f5f5",
    "label_fg": "#f5f5f5",
    "section_bg": "#23272e",
    "section_border": "#333842",
    "button_bg": "#388e3c",
    "button_fg": "#f5f5f5",
    "button_active": "#43a047",
    "progress_bg": "#43a047",
    "progress_trough": "#333842",
    "disabled_fg": "#888888",
    "highlight": "#43a047",
    "status_success": "#43a047",
    "status_error": "#e53935",
    "status_info": "#90caf9",
    "status_warn": "#ffa000"
}

USE_DARK = is_windows_dark_mode()
COLORS = DARK_COLORS if USE_DARK else LIGHT_COLORS



# --- Resource extraction for ffmpeg.exe (for onefile PyInstaller) ---
import tempfile
import shutil

def extract_ffmpeg():
    """Extract ffmpeg.exe from bundled data to a temp directory and return its path."""
    if hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        src = os.path.join(sys._MEIPASS, 'ffmpeg', 'bin', 'ffmpeg.exe')
        temp_dir = os.path.join(tempfile.gettempdir(), 'yt_ffmpeg_bin')
        os.makedirs(temp_dir, exist_ok=True)
        dst = os.path.join(temp_dir, 'ffmpeg.exe')
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
        return dst
    else:
        # Running from source
        return os.path.abspath(os.path.join('ffmpeg', 'bin', 'ffmpeg.exe'))

def resource_path(relative_path):
    """Get path to resource, works for dev and PyInstaller"""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)


# Set up the main window
root = tk.Tk()
root.title("YouTube Video Downloader")
root.geometry("550x400")
root.resizable(False, False)
root.configure(bg=COLORS["bg"])

# Style configuration
style = ttk.Style()
style.theme_use('clam')
style.configure("TCombobox",
                fieldbackground=COLORS["entry_bg"],
                background=COLORS["bg"],
                font=("Segoe UI", 11),
                foreground=COLORS["fg"])
style.configure("TProgressbar",
                thickness=10,
                troughcolor=COLORS["progress_trough"],
                background=COLORS["progress_bg"],
                bordercolor=COLORS["progress_trough"])
# --- Pill-shaped button style (ttk limitation: corners may not be truly rounded on Windows) ---
# This style increases padding and removes border for a modern look, but true pill/rounded corners require a custom widget or third-party library.
style.configure("Pill.TButton",
    font=("Segoe UI", 10),
    background=COLORS["button_bg"],
    foreground=COLORS["button_fg"],
    padding=(18, 8),  # More horizontal and vertical padding
    borderwidth=0,
    relief="flat"
)
style.map("Pill.TButton",
    background=[("active", COLORS["button_active"]), ("!active", COLORS["button_bg"])],
    foreground=[("disabled", COLORS["disabled_fg"]), ("!disabled", COLORS["button_fg"])])
# Note: True rounded corners are not supported by ttk on Windows. For a more modern look, consider using a custom image or a third-party widget.

# --- Custom style for rounded entry fields ---

class RoundedEntry(tk.Entry):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["section_border"],
            highlightcolor=COLORS["highlight"],
            bg=COLORS["entry_bg"],
            fg=COLORS["entry_fg"]
        )


# Set app icon if available
try:
    if os.path.exists("icon.ico"):
        root.iconbitmap("icon.ico")

except Exception as e:
    print("Icon not set:", e)

# Function to browse folder
def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        download_path.set(folder_selected)

# Download video function
# Add cancel flag as a global variable
download_in_progress = False
cancel_download = False

def cancel_download_task():
    global cancel_download, download_in_progress
    if download_in_progress:
        cancel_download = True
        status_label.config(text="Cancelling download...", fg="orange")
        root.update()
        # Reset progress bar and label immediately
        progress_bar.configure(value=0)
        progress_label.config(text="")
        # Switch button back to Download after cancelling
        set_unified_btn_mode("download")
        unified_btn.config(state="normal")

def download_video():
    # Show "Collecting Information..." label immediately after Download is clicked
    global collecting_label
    collecting_label.config(text="Collecting Information...")
    collecting_label.grid(row=4, column=0, pady=(0, 2), sticky="n")

    # Create a thread for download operation
    download_thread = threading.Thread(target=download_task)
    download_thread.daemon = True
    download_thread.start()


def is_valid_youtube_url(url):
    # More comprehensive URL validation for video platforms
    video_regex = (
        # YouTube formats
        r'^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))'
        r'(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$|'
        # Vimeo formats
        r'^((?:https?:)?\/\/)?((?:www|player)\.)?(vimeo\.com)'
        r'\/(?:channels\/(?:\w+\/)?|groups\/(?:[^\/]*)\/videos\/|video\/|)(\d+)(?:|\/\?)$|'
        # Dailymotion formats
        r'^((?:https?:)?\/\/)?((?:www|touch)\.)?(dailymotion\.com)'
        r'\/(?:video|embed\/video)\/([a-zA-Z0-9]+)(?:_[\w_-]+)?$|'
        # Facebook video formats (classic and new share/v/)
        r'^((?:https?:)?\/\/)?((?:www|web|m)\.)?(facebook\.com)'
        r'\/(?:video\.php\?v=\d+|.*?\/videos\/\d+|share\/v\/[\w-]+\/?){1}$|'
        # Twitter video formats
        r'^((?:https?:)?\/\/)?((?:www|mobile)\.)?(twitter\.com)'
        r'\/.*?\/status\/\d+$|'
        # Instagram video formats
        r'^((?:https?:)?\/\/)?((?:www)\.)?(instagram\.com)'
        r'\/(?:p|reel)\/[\w-]+\/?$|'
        # TikTok video formats
        r'^((?:https?:)?\/\/)?((?:www|vm)\.)?(tiktok\.com)'
        r'\/(?:@[\w\.-]+\/video\/\d+|v\/\w+|embed\/v2\/\w+)$'
    )
    return bool(re.match(video_regex, url))

# Add after imports
import json
from datetime import datetime

# Add after global variables
HISTORY_FILE = "download_history.json"
SETTINGS_FILE = "settings.json"


def show_history():
    history_window = tk.Toplevel(root)
    history_window.title("Download History")
    history_window.geometry("700x400")
    history_window.configure(bg="#fdfdfd")

    # Position the history window to the right of the main window
    root_x, root_y, root_width = root.winfo_x(), root.winfo_y(), root.winfo_width()
    history_window.geometry(f"700x400+{root_x + root_width + 10}+{root_y}")

    main_frame = tk.Frame(history_window, bg="#fdfdfd")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    button_frame = tk.Frame(main_frame, bg="#fdfdfd")
    button_frame.pack(fill=tk.X, pady=(0, 5))

    columns = ('Date', 'Filename', 'Format', 'Quality')
    tree = ttk.Treeview(main_frame, columns=columns, show='headings', selectmode='extended')
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    for col, width in zip(columns, (140, 330, 120, 80)):
        tree.heading(col, text=col)
        tree.column(col, width=width)

    def handle_click(event):
        if not tree.identify_row(event.y):
            for selected_item in tree.selection():
                tree.selection_remove(selected_item)
    tree.bind('<Button-1>', handle_click)

    # Efficient history loading
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                for item in reversed(history):
                    tree.insert('', 'end', values=(
                        item['date'],
                        item.get('title', os.path.basename(item['filename'])),
                        item['format'],
                        item['quality']
                    ))
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load history: {e}")

    def clear_selected():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select items to clear")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to clear selected items?"):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
                selected_dates = {tree.item(item)['values'][0] for item in selected_items}
                new_history = [item for item in history if item['date'] not in selected_dates]
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(new_history, f, indent=2)
                for item in selected_items:
                    tree.delete(item)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {e}")

    def clear_all():
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all history?"):
            try:
                with open(HISTORY_FILE, 'w') as f:
                    json.dump([], f)
                for item in tree.get_children():
                    tree.delete(item)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {e}")

    clear_selected_btn = ttk.Button(button_frame, text="Clear Selected", command=clear_selected, style="Pill.TButton")
    clear_selected_btn.pack(side=tk.LEFT, padx=5)
    clear_all_btn = ttk.Button(button_frame, text="Clear All", command=clear_all, style="Pill.TButton")
    clear_all_btn.pack(side=tk.LEFT, padx=5)

    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Modify the save_to_history function to include title and URL

def save_to_history(url, filename, format_type, quality):
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        else:
            history = []
        title = os.path.basename(filename).replace('%(title)s', '')
        history.append({
            'url': url,
            'filename': filename,
            'title': title,
            'format': format_type,
            'quality': quality,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        # Keep only last 100 entries
        history = history[-100:]
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def download_task():
    global download_in_progress, cancel_download
    global progress_max_percent
    progress_max_percent = 0  # Reset for each download
    cancel_download = False
    download_in_progress = True
    url = url_entry.get().strip()
    if url == "Video URL" or not url:
        messagebox.showwarning("Input Error", "Please enter a Video URL.")
        download_in_progress = False
        return
    if not is_valid_youtube_url(url):
        messagebox.showwarning("Invalid URL", "Please enter a valid Video URL.")
        download_in_progress = False
        return
    folder = download_path.get().strip()
    format_choice = format_var.get()
    quality_choice = quality_var.get()
    custom_name = filename_entry.get().strip()
    is_playlist = playlist_var.get()
    playlist_start = playlist_start_var.get().strip()
    playlist_end = playlist_end_var.get().strip()
    if not folder:
        messagebox.showwarning("Input Error", "Please select a download folder.")
        download_in_progress = False
        return
    # Switch unified button to Cancel after a short delay (e.g., 1.2s)
    root.after(0, lambda: set_unified_btn_mode("cancel", delay=1200))

    # Get the height value from quality choice
    quality_map = {
        "2160p (4K)": 2160,
        "1440p (2K)": 1440,
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
        "360p": 360
    }
    max_height = quality_map.get(quality_choice, 1080)

    # Use the same playlist options for info extraction and download
    info_opts = {}
    if is_playlist:
        if playlist_start.isdigit():
            info_opts['playliststart'] = int(playlist_start)
        if playlist_end.isdigit():
            info_opts['playlistend'] = int(playlist_end)
        info_opts['noplaylist'] = False
    else:
        info_opts['noplaylist'] = True

    # Extract info to get playlist title if needed
    playlist_folder = None
    video_title = None
    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # For playlist, use the playlist title; for single video, use video title
            if is_playlist and 'title' in info:
                video_title = info['title']
                playlist_folder = info['title']
            elif 'title' in info:
                video_title = info['title']
            else:
                video_title = 'Unknown Title'
    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract info: {e}")
        download_in_progress = False
        return

    # If playlist, append playlist folder to download path
    final_folder = folder
    if is_playlist and playlist_folder:
        # Sanitize folder name
        safe_folder = re.sub(r'[\\/:*?"<>|]', '_', playlist_folder)
        final_folder = os.path.join(folder, safe_folder)
        if not os.path.exists(final_folder):
            try:
                os.makedirs(final_folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create playlist folder: {e}")
                download_in_progress = False
                return

    # Handle filename (make truly optional for playlist)
    if is_playlist and url and "playlist?list=" in url:
        if custom_name and custom_name != "Filename is optional":
            output_template = custom_name + '_%(playlist_index)s.%(ext)s'
        else:
            output_template = '%(title)s_%(playlist_index)s.%(ext)s'
    else:
        if custom_name and custom_name != "Filename is optional":
            output_template = custom_name + '.%(ext)s'
        else:
            output_template = '%(title)s.%(ext)s'

    # Handle duplicate files differently for playlist and single videos
    output_template = os.path.join(final_folder, output_template)
    if not is_playlist:
        base, ext = os.path.splitext(output_template)
        # Only add autonumber if file exists
        if os.path.exists(output_template):
            output_template = base + '(1)' + ext


    # Base options
    # Optimize yt-dlp options for faster downloads
    ydl_opts = {
        'outtmpl': output_template,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
        'concurrent_fragment_downloads': 3,  # Download multiple fragments simultaneously
        'buffersize': 1024 * 16,  # Increase buffer size for faster downloads
        'http_chunk_size': 10485760,  # Increase chunk size to 10MB
        'ffmpeg_location': extract_ffmpeg()
    }

    # Add playlist options if enabled
    if is_playlist:
        if playlist_start.isdigit():
            ydl_opts['playliststart'] = int(playlist_start)
        if playlist_end.isdigit():
            ydl_opts['playlistend'] = int(playlist_end)
        ydl_opts['noplaylist'] = False
    else:
        ydl_opts['noplaylist'] = True

    # Add format options
    if format_choice == "MP4 (Video + Audio)":
        ydl_opts.update({
            'format': f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]',
            'merge_output_format': 'mp4'
        })
    elif format_choice == "MP4 (Video Only)":
        ydl_opts.update({
            'format': f'bestvideo[height<={max_height}][ext=mp4]/best[height<={max_height}][ext=mp4]',
            'merge_output_format': 'mp4'
        })
    elif format_choice == "MP4 (Facebook Video)":
        # Only allow for Facebook links
        if 'facebook.com' in url:
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4'
            })
        else:
            messagebox.showwarning("Format Error", "'MP4 (Facebook Video)' is only available for Facebook video links.")
            download_in_progress = False
            return
    else:  # MP3 (Audio Only)
        ydl_opts.update({
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'extractaudio': True,
            'audioformat': 'mp3'
        })


    # Show progress bar and 0% as soon as yt-dlp starts extracting info
    root.after(0, lambda: status_icon_label.config(text="ℹ️", fg=COLORS["status_info"]))
    root.after(0, lambda: status_label.config(text="Preparing download...", fg=COLORS["status_info"]))
    root.after(0, lambda: progress_bar.grid())
    root.after(0, lambda: progress_bar.configure(value=0))
    root.after(0, lambda: progress_label.config(text="0%"))

    # Hide the collecting label as soon as progress bar shows 0%
    def hide_collecting_label():
        global collecting_label
        try:
            collecting_label.config(text="")
            collecting_label.grid_remove()
        except Exception:
            pass

    def maybe_hide_label():
        if progress_label.cget("text") == "0%":
            hide_collecting_label()
        else:
            root.after(100, maybe_hide_label)
    root.after(100, maybe_hide_label)

    # --- Playlist-wide progress calculation ---
    total_playlist_bytes = [0]
    downloaded_playlist_bytes = [0]
    is_playlist_mode = is_playlist

    def playlist_progress_hook(d):
        nonlocal total_playlist_bytes, downloaded_playlist_bytes
        if cancel_download:
            raise Exception("Download cancelled by user")

        # For each video, accumulate total bytes
        if d.get('status') == 'pre_process':
            # Reset per-video bytes
            d['__video_total_bytes'] = 0
            d['__video_downloaded_bytes'] = 0

        if d.get('status') == 'downloading':
            # Estimate total bytes for the playlist
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            # On first chunk, add to total if not already counted
            if not hasattr(d, '__counted'):
                total_playlist_bytes[0] += total
                d['__counted'] = True
            # Update downloaded bytes
            downloaded_playlist_bytes[0] += downloaded - d.get('__video_downloaded_bytes', 0)
            d['__video_downloaded_bytes'] = downloaded

            percent = int((downloaded_playlist_bytes[0] / total_playlist_bytes[0]) * 100) if total_playlist_bytes[0] else 0

            def format_size(bytes):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if bytes < 1024:
                        return f"{bytes:.1f} {unit}"
                    bytes /= 1024
                return f"{bytes:.1f} GB"

            downloaded_str = format_size(downloaded_playlist_bytes[0])
            total_str = format_size(total_playlist_bytes[0])
            speed = d.get('speed', 0)
            speed_str = format_size(speed) + "/s" if speed else "N/A"
            status_text = f"{downloaded_str} of {total_str} ({speed_str})"
            root.after(0, lambda: progress_bar.configure(value=percent))
            root.after(0, lambda: progress_label.config(text=f"{percent}%"))
            root.after(0, lambda: speed_label.config(text=f"Speed: {speed_str}"))
            root.after(0, lambda: status_icon_label.config(text="⬇️", fg=COLORS["status_info"]))
            root.after(0, lambda: status_label.config(text=status_text, fg=COLORS["status_info"]))
        elif d.get('status') == 'finished':
            root.after(0, lambda: progress_bar.configure(value=100))
            root.after(0, lambda: progress_label.config(text="100%"))
            root.after(0, lambda: speed_label.config(text=""))

    # Use playlist-wide progress if playlist, else normal
    if is_playlist_mode:
        ydl_opts['progress_hooks'] = [playlist_progress_hook]
    else:
        ydl_opts['progress_hooks'] = [progress_hook]

    retry_count = 3
    while retry_count > 0:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            break
        except Exception as e:
            print("[yt-dlp ERROR]", e)
            if retry_count > 1 and not cancel_download:
                retry_count -= 1
                root.after(0, lambda: status_icon_label.config(text="!", fg=COLORS["status_warn"]))
                root.after(0, lambda: status_label.config(text=f"Retrying... ({retry_count} attempts left)", fg=COLORS["status_warn"]))
                continue
            raise e

    if not cancel_download:
        save_to_history(url, video_title, format_choice, quality_choice)
        root.after(0, lambda: status_icon_label.config(text="✓", fg=COLORS["status_success"]))
        root.after(0, lambda: status_label.config(text="Download completed!", fg=COLORS["status_success"]))
        def show_success_and_reset():
            messagebox.showinfo("Success", "Download completed successfully.")
            progress_bar.configure(value=0)
            progress_label.config(text="")
            set_unified_btn_mode("download")
            unified_btn.config(state="normal")
        root.after(0, show_success_and_reset)

def progress_hook(d):
    global cancel_download, download_in_progress
    global progress_max_percent
    if cancel_download:
        download_in_progress = False
        raise Exception("Download cancelled by user")


    # Reset progress for each new video in playlist (handle both 'started' and 'pre_process')
    # Also reset on 'downloading' if fragment_index == 0 (yt-dlp sometimes doesn't emit 'started' for every video)
    if (
        d.get('status') in ('started', 'pre_process')
        or (d.get('status') == 'downloading' and d.get('fragment_index', 0) == 0 and d.get('downloaded_bytes', 0) == 0)
    ):
        global progress_max_percent
        progress_max_percent = 0
        root.after(0, lambda: progress_bar.grid())
        root.after(0, lambda: progress_bar.configure(value=0))
        root.after(0, lambda: progress_label.config(text="0%"))

    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', d.get('total_bytes_estimate', 1))
        percent = int(downloaded * 100 / total) if total else 0
        speed = d.get('speed', 0)

        # Only allow progress to move forward (merge audio/video into one bar)
        if percent > progress_max_percent:
            progress_max_percent = percent
        else:
            percent = progress_max_percent

        def format_size(bytes):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024
            return f"{bytes:.1f} GB"

        downloaded_str = format_size(downloaded)
        total_str = format_size(total)
        speed_str = format_size(speed) + "/s" if speed else "N/A"

        status_text = f"{downloaded_str} of {total_str} ({speed_str})"
        root.after(0, lambda: progress_bar.configure(value=percent))
        root.after(0, lambda: progress_label.config(text=f"{percent}%"))
        root.after(0, lambda: speed_label.config(text=f"Speed: {speed_str}"))
        root.after(0, lambda: status_icon_label.config(text="⬇️", fg=COLORS["status_info"]))
        root.after(0, lambda: status_label.config(text=status_text, fg=COLORS["status_info"]))
    elif d['status'] == 'finished':
        root.after(0, lambda: progress_bar.configure(value=100))
        root.after(0, lambda: progress_label.config(text="100%"))


class MyLogger:
    def debug(self, _): pass
    def warning(self, _): pass
    def error(self, msg):
        messagebox.showerror("Error", msg)

# Tkinter Variables
download_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))


# --- Section Headings ---
section_label = tk.Label(root, text="Download Options", font=("Segoe UI", 13, "bold"), bg=COLORS["bg"], fg=COLORS["label_fg"])
section_label.grid(row=0, column=0, sticky="w", padx=20, pady=(10, 0))

fields_frame = tk.Frame(root, bg=COLORS["section_bg"], highlightbackground=COLORS["section_border"], highlightthickness=1)
fields_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
fields_frame.grid_columnconfigure(1, weight=1)
fields_frame.grid_columnconfigure(2, weight=0)

label_width = 18
entry_width = 42



# Row 1 - URL (improved alignment)
url_label = tk.Label(fields_frame, text="YouTube Video URL:", font=("Segoe UI", 11), bg=COLORS["section_bg"], fg=COLORS["label_fg"], width=label_width, anchor="w")
url_label.grid(row=0, column=0, sticky="w", pady=5)
url_entry = RoundedEntry(fields_frame, width=32, font=("Segoe UI", 11))
url_entry.insert(0, "Video URL")
url_entry.config(fg=COLORS["disabled_fg"])
url_entry.grid(row=0, column=1, pady=5, sticky="ew")


# --- URL Entry Placeholder Logic ---
def on_url_click(_):
    if url_entry.get() == "Video URL":
        url_entry.delete(0, tk.END)
        url_entry.config(fg=COLORS["entry_fg"])

def on_url_focusout(_):
    if url_entry.get() == '':
        url_entry.insert(0, "Video URL")
        url_entry.config(fg=COLORS["disabled_fg"])

url_entry.bind('<FocusIn>', on_url_click)
url_entry.bind('<FocusOut>', on_url_focusout)

# Initial state for playlist checkbutton (must be after playlist_check is created)

# Define is_playlist_url and update_playlist_check_and_enable after playlist_check is created

# Row 2 - Folder (improved alignment)
folder_label = tk.Label(fields_frame, text="Download Folder:", font=("Segoe UI", 11), bg=COLORS["section_bg"], fg=COLORS["label_fg"], width=label_width, anchor="w")
folder_label.grid(row=1, column=0, sticky="w", pady=5)
folder_entry = RoundedEntry(fields_frame, textvariable=download_path, width=28, font=("Segoe UI", 11))
folder_entry.grid(row=1, column=1, pady=5, sticky="ew")
ttButton = ttk.Button(fields_frame, text="Browse", command=browse_folder, style="outline.TButton", width=8)
ttButton.grid(row=1, column=2, padx=(4,20), pady=5, sticky="ew")


# Row 3 - Format
format_label = tk.Label(fields_frame, text="Format:", font=("Segoe UI", 11), bg=COLORS["section_bg"], fg=COLORS["label_fg"], width=label_width, anchor="w")
format_label.grid(row=2, column=0, sticky="w", pady=5)
format_var = tk.StringVar(value="MP4 (Video + Audio)")

# --- Modernized Combobox for Format ---

# Set width to 20 to prevent overflow and improve alignment
format_menu = ttk.Combobox(fields_frame, textvariable=format_var,
    values=["MP4 (Video + Audio)", "MP4 (Video Only)", "MP3 (Audio Only)", "MP4 (Facebook Video)"],
    state="readonly", width=20)
format_menu.grid(row=2, column=1, pady=5, padx=(0, 5), sticky="ew")


# Row 4 - Quality
quality_label = tk.Label(fields_frame, text="Quality:", font=("Segoe UI", 11), bg=COLORS["section_bg"], fg=COLORS["label_fg"], width=label_width, anchor="w")
quality_label.grid(row=3, column=0, sticky="w", pady=5)

quality_var = tk.StringVar(value="1080p")

# --- Modernized Combobox for Quality ---

# Set width to 20 to prevent overflow and improve alignment
quality_menu = ttk.Combobox(fields_frame, textvariable=quality_var,
    values=["2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"],
    state="readonly", width=20)
quality_menu.grid(row=3, column=1, pady=5, padx=(0, 5), sticky="ew")

# --- Disable/enable quality dropdown based on format selection ---
def update_quality_state(*_):
    if format_var.get() == "MP3 (Audio Only)":
        quality_menu.config(state="disabled")
    else:
        quality_menu.config(state="readonly")

# Initial state
update_quality_state()
# Trace format_var changes
format_var.trace_add('write', update_quality_state)

# Row 5 - Playlist Options


# Playlist row: align with label and entry columns
playlist_label = tk.Label(fields_frame, text="", bg=COLORS["section_bg"], width=label_width)
playlist_label.grid(row=4, column=0, sticky="w", pady=5)
playlist_frame = tk.Frame(fields_frame, bg=COLORS["section_bg"])
playlist_frame.grid(row=4, column=1, columnspan=2, pady=5, sticky="ew")



playlist_var = tk.BooleanVar(value=False)

style.configure("Tick.TCheckbutton",
    font=("Segoe UI", 11),
    background=COLORS["section_bg"],
    foreground=COLORS["fg"],
    padding=6,
    focuscolor=COLORS["highlight"],
    borderwidth=0
)
style.map("Tick.TCheckbutton",
    background=[("active", COLORS["section_bg"]), ("!active", COLORS["section_bg"])],
    foreground=[("active", COLORS["highlight"]), ("selected", COLORS["highlight"]), ("!selected", COLORS["fg"])]
)
playlist_check = ttk.Checkbutton(
    playlist_frame,
    text="Download Playlist",
    variable=playlist_var,
    style="Tick.TCheckbutton"
)
playlist_check.pack(side=tk.LEFT, padx=(0, 5), pady=2, anchor="w")


# Use a Unicode tick (✓) as the label, and hide the indicator for a modern look
style = ttk.Style()
style.layout('Tick.TCheckbutton', [
    ('Checkbutton.padding', {'children': [
        ('Checkbutton.label', {'side': 'left', 'sticky': ''})
    ]})
])
def update_playlist_check():
    if playlist_var.get():
        playlist_check.config(text='Download Playlist ✓')
    else:
        playlist_check.config(text='Download Playlist')
playlist_var.trace_add('write', lambda *_: update_playlist_check())
update_playlist_check()

playlist_start_var = tk.StringVar()


playlist_start_label = tk.Label(playlist_frame, text="Start:", bg=COLORS["section_bg"], fg=COLORS["label_fg"])
playlist_start_label.pack(side=tk.LEFT, padx=5)
playlist_start_entry = RoundedEntry(playlist_frame, textvariable=playlist_start_var, width=5)
playlist_start_entry.pack(side=tk.LEFT, padx=2)

playlist_end_var = tk.StringVar()
playlist_end_label = tk.Label(playlist_frame, text="End:", bg=COLORS["section_bg"], fg=COLORS["label_fg"])
playlist_end_label.pack(side=tk.LEFT, padx=5)
playlist_end_entry = RoundedEntry(playlist_frame, textvariable=playlist_end_var, width=5)
playlist_end_entry.pack(side=tk.LEFT, padx=2)

# Function to update playlist start/end highlight and state
def update_playlist_fields(*_):
    if playlist_var.get():
        playlist_start_entry.config(state='normal', highlightbackground=COLORS["highlight"], highlightcolor=COLORS["highlight"])
        playlist_end_entry.config(state='normal', highlightbackground=COLORS["highlight"], highlightcolor=COLORS["highlight"])
        playlist_start_label.config(fg=COLORS["highlight"])
        playlist_end_label.config(fg=COLORS["highlight"])
    else:
        playlist_start_entry.config(state='disabled', highlightbackground=COLORS["section_border"], highlightcolor=COLORS["section_border"])
        playlist_end_entry.config(state='disabled', highlightbackground=COLORS["section_border"], highlightcolor=COLORS["section_border"])
        playlist_start_label.config(fg=COLORS["disabled_fg"])
        playlist_end_label.config(fg=COLORS["disabled_fg"])

# Initial state
update_playlist_fields()
# Trace playlist_var changes
playlist_var.trace_add('write', update_playlist_fields)



# Row 6 - Filename (improved alignment)
filename_label = tk.Label(fields_frame, text="Filename:", font=("Segoe UI", 11), bg=COLORS["section_bg"], fg=COLORS["label_fg"], width=label_width, anchor="w")
filename_label.grid(row=5, column=0, sticky="w", pady=5)
filename_entry = RoundedEntry(fields_frame, width=32, font=("Segoe UI", 11))
filename_entry.insert(0, "Filename is optional")
filename_entry.config(fg=COLORS["disabled_fg"])
filename_entry.grid(row=5, column=1, pady=5, sticky="ew")


# --- Filename Entry Placeholder Logic ---
def on_entry_click(_):
    if filename_entry.get() == "Filename is optional":
        filename_entry.delete(0, tk.END)
        filename_entry.config(fg=COLORS["entry_fg"])

def on_focusout(_):
    if filename_entry.get() == '':
        filename_entry.insert(0, "Filename is optional")
        filename_entry.config(fg=COLORS["disabled_fg"])

filename_entry.bind('<FocusIn>', on_entry_click)
filename_entry.bind('<FocusOut>', on_focusout)


# --- Section for actions ---


buttons_frame = tk.Frame(root, bg=COLORS["bg"])
buttons_frame.grid(row=3, column=0, pady=10)



unified_btn_state = {"mode": "download", "delay_active": False}

def unified_btn_action():
    if unified_btn_state["mode"] == "download":
        download_video()
    elif unified_btn_state["mode"] == "cancel":
        cancel_download_task()

def set_unified_btn_mode(mode, delay=0):
    # mode: "download" or "cancel"
    def _set():
        if mode == "download":
            unified_btn.config(text="Download", state="normal")
            unified_btn_state["mode"] = "download"
            unified_btn_state["delay_active"] = False
        elif mode == "cancel":
            unified_btn.config(text="Cancel", state="normal")
            unified_btn_state["mode"] = "cancel"
            unified_btn_state["delay_active"] = False
    if delay > 0:
        unified_btn.config(state="disabled")
        unified_btn_state["delay_active"] = True
        root.after(delay, _set)
    else:
        _set()


# --- Modernized pill-shaped buttons with extra padding ---
unified_btn = ttk.Button(buttons_frame, text="Download", command=unified_btn_action, width=12, style="outline.TButton")
unified_btn.pack(side=tk.LEFT, padx=10, pady=4)

ttHistory = ttk.Button(buttons_frame, text="History", command=show_history, width=12, style="outline.TButton")
ttHistory.pack(side=tk.LEFT, padx=10, pady=4)



# Add event handlers to save settings when changed
def on_setting_changed(*_):
    save_settings()

format_var.trace_add('write', on_setting_changed)
quality_var.trace_add('write', on_setting_changed)
download_path.trace_add('write', on_setting_changed)

# --- Settings persistence ---

def save_settings():
    settings = {
        'download_path': download_path.get(),
        'format': format_var.get(),
        'quality': quality_var.get()
    }
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            download_path.set(settings.get('download_path', os.path.join(os.path.expanduser("~"), "Downloads")))
            format_var.set(settings.get('format', "MP4 (Video + Audio)"))
            quality_var.set(settings.get('quality', "1080p"))
    except Exception as e:
        print(f"Error loading settings: {e}")

# Load settings before mainloop
load_settings()


# --- Tooltips ---
def add_tooltip(widget, text):
    tooltip = tk.Toplevel(widget)
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    tooltip_label = tk.Label(tooltip, text=text, bg=COLORS["section_bg"], fg=COLORS["fg"], font=("Segoe UI", 9), relief="solid", borderwidth=1, padx=4, pady=2)
    tooltip_label.pack()

    def enter(event):
        x = event.x_root + 10
        y = event.y_root + 10
        tooltip.geometry(f"+{x}+{y}")
        tooltip.deiconify()
    def leave(event):
        tooltip.withdraw()
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)

add_tooltip(url_entry, "Paste a YouTube or playlist URL here.")
add_tooltip(folder_entry, "Choose where to save your downloads.")
add_tooltip(format_menu, "Select the output format.")
add_tooltip(quality_menu, "Select the maximum video quality. (Disabled for audio-only downloads)")
add_tooltip(playlist_check, "Enable to download all videos in a playlist.")
add_tooltip(playlist_start_entry, "First video in playlist to download (optional).")
add_tooltip(playlist_end_entry, "Last video in playlist to download (optional).")
add_tooltip(filename_entry, "Custom filename (optional). For playlists, index is appended.")
add_tooltip(unified_btn, "Start downloading the video or playlist. When downloading, becomes Cancel.")
add_tooltip(ttHistory, "View download history.")


# --- Collecting Information Label (placed below buttons) ---
collecting_label = tk.Label(root, text="", font=("Segoe UI", 10, "italic"), fg=COLORS["status_info"], bg=COLORS["bg"])
collecting_label.grid(row=4, column=0, pady=(0, 2), sticky="n")
collecting_label.grid_remove()  # Hide initially

# --- Progress and status ---
progress_frame = tk.Frame(root, bg=COLORS["bg"])
progress_frame.grid(row=5, column=0, pady=5, sticky="ew")
progress_frame.grid_columnconfigure(0, weight=1)


# Progress bar
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=450, mode="determinate")
progress_bar.grid(row=0, column=0, sticky="ew")

# Frame for speed and percent (side by side, below progress bar)
speed_percent_frame = tk.Frame(progress_frame, bg=COLORS["bg"])
speed_percent_frame.grid(row=1, column=0, sticky="ew", pady=(2, 0))
speed_percent_frame.grid_columnconfigure(0, weight=1)
speed_percent_frame.grid_columnconfigure(1, weight=0)

# Speed label (left, expands)
speed_label = tk.Label(speed_percent_frame, text="", font=("Segoe UI", 9), fg=COLORS["fg"], bg=COLORS["bg"])
speed_label.grid(row=0, column=0, sticky="w")
# Percent label (right, bold)
progress_label = tk.Label(speed_percent_frame, text="", font=("Segoe UI", 10, "bold"), fg=COLORS["fg"], bg=COLORS["bg"])
progress_label.grid(row=0, column=1, sticky="e", padx=(8, 0))

# Status label with icon
status_icon_label = tk.Label(root, text="", font=("Segoe UI", 13), bg=COLORS["bg"])
status_icon_label.grid(row=6, column=0, sticky="w", padx=20)
status_label = tk.Label(root, text="", font=("Segoe UI", 10), bg=COLORS["bg"], fg=COLORS["fg"])
status_label.grid(row=7, column=0, sticky="w", padx=50)

# Start the main loop (this should be the last line)
root.mainloop()

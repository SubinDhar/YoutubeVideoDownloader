import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import yt_dlp
import os
import threading
import re  # Add this import for URL validation

# Set up the main window
root = tk.Tk()
root.title("YouTube Video Downloader")
root.geometry("550x400")
root.resizable(False, False)
root.configure(bg="#fdfdfd")

# Style configuration
style = ttk.Style()
style.theme_use('clam')
style.configure("TCombobox",
                fieldbackground="#e0e0e0",
                background="#f0f0f0",
                font=("Arial", 11))
style.configure("TProgressbar",
                thickness=10,
                troughcolor="#d0d0d0",
                background="#4CAF50",
                bordercolor="#d0d0d0")
style.configure("TButton",
                font=("Arial", 10),
                background="#4CAF50",
                foreground="white",
                padding=6)
style.map("TButton",
          background=[("active", "#45a049")])

# Custom style for rounded entry fields
class RoundedEntry(tk.Entry):
    def __init__(self, master=None, **kwargs):
        tk.Entry.__init__(self, master, **kwargs)
        self.configure(
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d0d0d0",
            highlightcolor="#4CAF50"
        )

# Set app icon if available, otherwise set a label with text "i"
try:
    if os.path.exists("icon.ico"):
        root.iconbitmap("icon.ico")
    else:
        label_no_icon = tk.Label(root, text="i", font=("Arial", 20, "bold"), fg="blue", bg="#fdfdfd")
        label_no_icon.place(x=5, y=5)
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

def download_video():
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
        # Facebook video formats
        r'^((?:https?:)?\/\/)?((?:www|web|m)\.)?(facebook\.com)'
        r'\/(?:video\.php\?v=\d+|.*?\/videos\/\d+)$|'
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

def show_history():
    history_window = tk.Toplevel(root)
    history_window.title("Download History")
    history_window.geometry("700x400")
    history_window.configure(bg="#fdfdfd")
    
    # Get the main window's position and dimensions
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    
    # Position the history window to the right of the main window
    history_window.geometry(f"700x400+{root_x + root_width + 10}+{root_y}")
    
    # Create main frame
    main_frame = tk.Frame(history_window, bg="#fdfdfd")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Create button frame
    button_frame = tk.Frame(main_frame, bg="#fdfdfd")
    button_frame.pack(fill=tk.X, pady=(0, 5))
    
    # Create treeview with selectmode='extended' to allow multiple selections
    columns = ('Date', 'Filename', 'Format', 'Quality')
    tree = ttk.Treeview(main_frame, columns=columns, show='headings', selectmode='extended')
    
    # Add scrollbar before loading data
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Set column headings and widths
    tree.heading('Date', text='Date')
    tree.heading('Filename', text='Filename')
    tree.heading('Format', text='Format')
    tree.heading('Quality', text='Quality')
    
    tree.column('Date', width=140)
    tree.column('Filename', width=330)
    tree.column('Format', width=120)
    tree.column('Quality', width=80)
    
    # Add deselection handler
    def handle_click(event):
        if not tree.identify_row(event.y):  # If clicked on empty space
            # Clear selection
            for selected_item in tree.selection():
                tree.selection_remove(selected_item)
    
    # Bind the click handler to the treeview
    tree.bind('<Button-1>', handle_click)
    
    # Load history more efficiently
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                # Insert items in batch instead of one by one
                items_to_insert = [(
                    item['date'],
                    item.get('title', os.path.basename(item['filename'])),
                    item['format'],
                    item['quality']
                ) for item in reversed(history)]
                for values in items_to_insert:
                    tree.insert('', 'end', values=values)
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
                
                # Get the dates of selected items
                selected_dates = [tree.item(item)['values'][0] for item in selected_items]
                
                # Remove selected items from history
                new_history = [item for item in history 
                             if item['date'] not in selected_dates]
                
                # Save updated history
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(new_history, f, indent=2)
                
                # Remove from treeview
                for item in selected_items:
                    tree.delete(item)
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {e}")
    
    def clear_all():
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all history?"):
            try:
                # Clear the file
                with open(HISTORY_FILE, 'w') as f:
                    json.dump([], f)
                
                # Clear the treeview
                for item in tree.get_children():
                    tree.delete(item)
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {e}")
    
    # Add Clear buttons after function definitions
    clear_selected_btn = ttk.Button(button_frame, text="Clear Selected", command=clear_selected)
    clear_selected_btn.pack(side=tk.LEFT, padx=5)
    
    clear_all_btn = ttk.Button(button_frame, text="Clear All", command=clear_all)
    clear_all_btn.pack(side=tk.LEFT, padx=5)
    
    def redownload_item(url):
        # Clear the URL entry and set it properly
        url_entry.delete(0, tk.END)
        url_entry.insert(0, url)
        url_entry.config(fg='black')
        # Close history window
        history_window.destroy()
        # Reset the download state before starting new download
        global download_in_progress, cancel_download
        download_in_progress = False
        cancel_download = False
        # Start the download
        download_video()
    
    def handle_click(event, url):
        # Get the clicked column
        region = tree.identify_region(event.x, event.y)
        column = tree.identify_column(event.x)
        
        # Only trigger download if clicking on the Actions column
        if region == "cell" and column == "#5":  # Actions is the 5th column
            redownload_item(url)
    
    # Load history
    try:
        history = []
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
    
    # Pack the tree and scrollbar
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Modify the save_to_history function to include title and URL
def save_to_history(url, filename, format_type, quality):
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        
        # Extract title from the filename template
        title = os.path.basename(filename)
        if '%(title)s' in title:
            title = title.replace('%(title)s', '')
        
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
    cancel_download = False
    download_in_progress = True
    
    url = url_entry.get().strip()
    if url == "Video URL" or not url:
        messagebox.showwarning("Input Error", "Please enter a YouTube URL.")
        download_in_progress = False
        return
    if not is_valid_youtube_url(url):
        messagebox.showwarning("Invalid URL", "Please enter a valid YouTube URL.")
        download_in_progress = False
        return

    folder = download_path.get().strip()
    format_choice = format_var.get()
    quality_choice = quality_var.get()
    custom_name = filename_entry.get().strip()
    is_playlist = playlist_var.get()
    playlist_start = playlist_start_var.get().strip()
    playlist_end = playlist_end_var.get().strip()

    # Remove redundant URL check
    if not folder:
        messagebox.showwarning("Input Error", "Please select a download folder.")
        download_in_progress = False
        return

    # Enable cancel button and disable download button
    root.after(0, lambda: ttCancel.state(['!disabled']))
    root.after(0, lambda: ttDownload.state(['disabled']))

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

    # Handle filename
    if custom_name and custom_name != "Filename is optional":
        if is_playlist:
            output_template = custom_name + '_%(playlist_index)s.%(ext)s'
        else:
            output_template = custom_name + '.%(ext)s'
    else:
        if is_playlist:
            output_template = '%(title)s_%(playlist_index)s.%(ext)s'
        else:
            output_template = '%(title)s.%(ext)s'

    # Handle duplicate files differently for playlist and single videos
    output_template = os.path.join(folder, output_template)
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
        'http_chunk_size': 10485760  # Increase chunk size to 10MB
    }

    # Add playlist options if enabled
    if is_playlist:
        if playlist_start:
            ydl_opts['playliststart'] = int(playlist_start)
        if playlist_end:
            ydl_opts['playlistend'] = int(playlist_end)
        # For playlists, let yt-dlp handle the numbering naturally
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

    try:
        root.after(0, lambda: status_label.config(text="Downloading...", fg="blue"))
        root.after(0, lambda: progress_bar.configure(value=0))
        root.after(0, lambda: progress_label.config(text="0%"))

        # Get video info first with noplaylist option if playlist is not checked
        info_opts = {'noplaylist': not is_playlist}
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'Unknown Title')

        retry_count = 3
        while retry_count > 0:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                break
            except Exception as e:
                if retry_count > 1 and not cancel_download:
                    retry_count -= 1
                    root.after(0, lambda: status_label.config(text=f"Retrying... ({retry_count} attempts left)", fg="orange"))
                    continue
                raise e

        if not cancel_download:
            save_to_history(url, video_title, format_choice, quality_choice)
            root.after(0, lambda: status_label.config(text="Download completed!", fg="green"))
            root.after(0, lambda: messagebox.showinfo("Success", "Download completed successfully."))
    except Exception as e:
        if str(e) == "Download cancelled by user":
            root.after(0, lambda: status_label.config(text="Download cancelled.", fg="orange"))
        else:
            root.after(0, lambda: status_label.config(text="Download failed.", fg="red"))
            root.after(0, lambda: messagebox.showerror("Error", str(e)))
    finally:
        download_in_progress = False
        cancel_download = False
        root.after(0, lambda: progress_bar.configure(value=0))
        root.after(0, lambda: progress_label.config(text=""))
        root.after(0, lambda: ttCancel.state(['disabled']))
        root.after(0, lambda: ttDownload.state(['!disabled']))

def progress_hook(d):
    global cancel_download, download_in_progress
    if cancel_download:
        download_in_progress = False
        raise Exception("Download cancelled by user")
        
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', d.get('total_bytes_estimate', 1))
        percent = int(downloaded * 100 / total)
        speed = d.get('speed', 0)
        
        # Format size and speed
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
        root.after(0, lambda: status_label.config(text=status_text))
    elif d['status'] == 'finished':
        root.after(0, lambda: progress_bar.configure(value=100))
        root.after(0, lambda: progress_label.config(text="100%"))

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): messagebox.showerror("Error", msg)

# Tkinter Variables
download_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))

# Layout
fields_frame = tk.Frame(root, bg="#fdfdfd")
fields_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
fields_frame.grid_columnconfigure(1, weight=1)
fields_frame.grid_columnconfigure(2, weight=0)

label_width = 18
entry_width = 42

# Row 1 - URL
url_label = tk.Label(fields_frame, text="YouTube Video URL:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
url_label.grid(row=0, column=0, sticky="w", pady=5)
url_entry = RoundedEntry(fields_frame, width=entry_width, font=("Segoe UI", 11), bg="#e0e0e0")
url_entry.insert(0, "Video URL")
url_entry.config(fg='gray')
url_entry.grid(row=0, column=1, columnspan=2, pady=5, sticky="ew")

# Add event handlers for URL placeholder
def on_url_click(event):
    if url_entry.get() == "Video URL":
        url_entry.delete(0, tk.END)
        url_entry.config(fg='black')

def on_url_focusout(event):
    if url_entry.get() == '':
        url_entry.insert(0, "Video URL")
        url_entry.config(fg='gray')

url_entry.bind('<FocusIn>', on_url_click)
url_entry.bind('<FocusOut>', on_url_focusout)

# Row 2 - Folder
folder_label = tk.Label(fields_frame, text="Download Folder:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
folder_label.grid(row=1, column=0, sticky="w", pady=5)
folder_entry = RoundedEntry(fields_frame, textvariable=download_path, width=entry_width - 10, font=("Segoe UI", 11), bg="#e0e0e0")
folder_entry.grid(row=1, column=1, pady=5, sticky="ew")
ttButton = ttk.Button(fields_frame, text="Browse", command=browse_folder)
ttButton.grid(row=1, column=2, padx=5, sticky="ew")

# Row 3 - Format
format_label = tk.Label(fields_frame, text="Format:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
format_label.grid(row=2, column=0, sticky="w", pady=5)
format_var = tk.StringVar(value="MP4 (Video + Audio)")
format_menu = ttk.Combobox(fields_frame, textvariable=format_var, 
                          values=["MP4 (Video + Audio)", "MP4 (Video Only)", "MP3 (Audio Only)"], 
                          state="readonly", width=entry_width)
format_menu.grid(row=2, column=1, columnspan=2, pady=5, sticky="ew")

# Row 4 - Quality
quality_label = tk.Label(fields_frame, text="Quality:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
quality_label.grid(row=3, column=0, sticky="w", pady=5)
quality_var = tk.StringVar(value="1080p")
quality_menu = ttk.Combobox(fields_frame, textvariable=quality_var, 
                           values=["2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"], 
                           state="readonly", width=entry_width)
quality_menu.grid(row=3, column=1, columnspan=2, pady=5, sticky="ew")

# Row 5 - Playlist Options
playlist_frame = tk.Frame(fields_frame, bg="#fdfdfd")
playlist_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky="ew")

playlist_var = tk.BooleanVar(value=False)
playlist_check = ttk.Checkbutton(playlist_frame, text="Download Playlist", variable=playlist_var)
playlist_check.pack(side=tk.LEFT, padx=5)

playlist_start_var = tk.StringVar()
playlist_start_label = tk.Label(playlist_frame, text="Start:", bg="#fdfdfd")
playlist_start_label.pack(side=tk.LEFT, padx=5)
playlist_start_entry = RoundedEntry(playlist_frame, textvariable=playlist_start_var, width=5)
playlist_start_entry.pack(side=tk.LEFT, padx=2)

playlist_end_var = tk.StringVar()
playlist_end_label = tk.Label(playlist_frame, text="End:", bg="#fdfdfd")
playlist_end_label.pack(side=tk.LEFT, padx=5)
playlist_end_entry = RoundedEntry(playlist_frame, textvariable=playlist_end_var, width=5)
playlist_end_entry.pack(side=tk.LEFT, padx=2)

# Row 6 - Filename (moved down one row)
filename_label = tk.Label(fields_frame, text="Filename:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
filename_label.grid(row=5, column=0, sticky="w", pady=5)
filename_entry = RoundedEntry(fields_frame, width=entry_width, font=("Segoe UI", 11), bg="#e0e0e0")
filename_entry.insert(0, "Filename is optional")
filename_entry.config(fg='gray')
filename_entry.grid(row=5, column=1, columnspan=2, pady=5, sticky="ew")

# Add event handlers for placeholder text
def on_entry_click(event):
    if filename_entry.get() == "Filename is optional":
        filename_entry.delete(0, tk.END)
        filename_entry.config(fg='black')

def on_focusout(event):
    if filename_entry.get() == '':
        filename_entry.insert(0, "Filename is optional")
        filename_entry.config(fg='gray')

filename_entry.bind('<FocusIn>', on_entry_click)
filename_entry.bind('<FocusOut>', on_focusout)

# Download and Cancel buttons frame
buttons_frame = tk.Frame(root, bg="#fdfdfd")
buttons_frame.grid(row=1, column=0, pady=10)

ttDownload = ttk.Button(buttons_frame, text="Download", command=download_video)
ttDownload.pack(side=tk.LEFT, padx=5)

ttCancel = ttk.Button(buttons_frame, text="Cancel", command=cancel_download_task, state='disabled')
ttCancel.pack(side=tk.LEFT, padx=5)

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=450, mode="determinate")
progress_bar.grid(row=2, column=0, pady=5)

# Progress label
progress_label = tk.Label(root, text="", font=("Segoe UI", 10), bg="#fdfdfd")
progress_label.grid(row=3, column=0)

# Status label
status_label = tk.Label(root, text="", font=("Segoe UI", 10), bg="#fdfdfd")
status_label.grid(row=4, column=0)

# Add after imports
SETTINGS_FILE = "settings.json"

# Move all settings and history related functions here, before creating the UI
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

# Add History button next to Cancel button
ttHistory = ttk.Button(buttons_frame, text="History", command=show_history)
ttHistory.pack(side=tk.LEFT, padx=5)

# Add event handlers to save settings when changed
def on_setting_changed(*args):
    save_settings()

format_var.trace('w', on_setting_changed)
quality_var.trace('w', on_setting_changed)
download_path.trace('w', on_setting_changed)

# Load settings before mainloop
load_settings()

# Start the main loop (this should be the last line)
root.mainloop()

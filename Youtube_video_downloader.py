import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import yt_dlp
import os

# Set up the main window
root = tk.Tk()
root.title("YouTube Video Downloader")
root.geometry("550x300")
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
def download_video():
    url = url_entry.get().strip()
    folder = download_path.get().strip()
    format_choice = format_var.get()
    custom_name = filename_entry.get().strip()

    if not url:
        messagebox.showwarning("Input Error", "Please enter a YouTube URL.")
        return
    if not folder:
        messagebox.showwarning("Input Error", "Please select a download folder.")
        return

    class MyLogger:
        def debug(self, msg):
            pass

        def warning(self, msg):
            pass

        def error(self, msg):
            messagebox.showerror("Error", msg)

    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', d.get('total_bytes_estimate', 1))
            percent = int(downloaded * 100 / total)
            progress_bar['value'] = percent
            progress_label.config(text=f"{percent}%")
            root.update_idletasks()
        elif d['status'] == 'finished':
            progress_bar['value'] = 100
            progress_label.config(text="100%")
            root.update_idletasks()

    output_template = '%(title)s.%(ext)s'
    if custom_name:
        output_template = custom_name + ".%(ext)s"

    if format_choice == "MP4 (Video + Audio)":
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(folder, output_template),
            'logger': MyLogger(),
            'progress_hooks': [progress_hook]
        }
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(folder, output_template),
            'logger': MyLogger(),
            'progress_hooks': [progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }

    try:
        status_label.config(text="Downloading...", fg="blue")
        progress_bar['value'] = 0
        progress_label.config(text="0%")
        root.update()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        status_label.config(text="Download completed!", fg="green")
        messagebox.showinfo("Success", "Download completed successfully.")
    except Exception as e:
        status_label.config(text="Download failed.", fg="red")
        messagebox.showerror("Error", str(e))

# Tkinter Variables
download_path = tk.StringVar()

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
url_entry = tk.Entry(fields_frame, width=entry_width, font=("Segoe UI", 11), bg="#e0e0e0")
url_entry.grid(row=0, column=1, columnspan=2, pady=5, sticky="ew")

# Row 2 - Folder
folder_label = tk.Label(fields_frame, text="Download Folder:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
folder_label.grid(row=1, column=0, sticky="w", pady=5)
folder_entry = tk.Entry(fields_frame, textvariable=download_path, width=entry_width - 10, font=("Segoe UI", 11), bg="#e0e0e0")
folder_entry.grid(row=1, column=1, pady=5, sticky="ew")
ttButton = ttk.Button(fields_frame, text="Browse", command=browse_folder)
ttButton.grid(row=1, column=2, padx=5, sticky="ew")

# Row 3 - Format
format_label = tk.Label(fields_frame, text="Format:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
format_label.grid(row=2, column=0, sticky="w", pady=5)
format_var = tk.StringVar(value="MP4 (Video + Audio)")
format_menu = ttk.Combobox(fields_frame, textvariable=format_var, values=["MP4 (Video + Audio)", "MP3 (Audio Only)"], state="readonly", width=entry_width)
format_menu.grid(row=2, column=1, columnspan=2, pady=5, sticky="ew")

# Row 4 - Filename
filename_label = tk.Label(fields_frame, text="Filename:", font=("Segoe UI", 11), bg="#fdfdfd", width=label_width, anchor="w")
filename_label.grid(row=3, column=0, sticky="w", pady=5)
filename_entry = tk.Entry(fields_frame, width=entry_width, font=("Segoe UI", 11), bg="#e0e0e0")
filename_entry.grid(row=3, column=1, columnspan=2, pady=5, sticky="ew")

# Download button
ttDownload = ttk.Button(root, text="Download", command=download_video)
ttDownload.grid(row=1, column=0, pady=10)

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=450, mode="determinate")
progress_bar.grid(row=2, column=0, pady=5)

# Progress label
progress_label = tk.Label(root, text="", font=("Segoe UI", 10), bg="#fdfdfd")
progress_label.grid(row=3, column=0)

# Status label
status_label = tk.Label(root, text="", font=("Segoe UI", 10), bg="#fdfdfd")
status_label.grid(row=4, column=0)

root.mainloop()

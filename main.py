#!/usr/bin/env python3
import os
import io
import pickle
import csv
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Thread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Default redirect URI with port
REDIRECT_URI = 'http://localhost:61249/'
# Global variable to store credentials in memory
memory_token = None
# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of supported MIME types
SUPPORTED_MIME_TYPES = [
    'application/pdf',
    'application/vnd.google-apps.document',  # Google Docs
    'application/vnd.google-apps.spreadsheet'  # Google Sheets
]

def authenticate(credentials_path):
    """Authenticate and return the Google Drive service."""
    global memory_token
    creds = None

    if memory_token:
        creds = Credentials.from_authorized_user_info(memory_token, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            flow.redirect_uri = REDIRECT_URI
            creds = flow.run_local_server(port=61249)
        # Save the credentials to memory
        memory_token = creds.to_json()
    return build('drive', 'v3', credentials=creds)

def log_to_console(message, queue):
    queue.put(message)

def update_console(console_text, log_queue):
    while True:
        message = log_queue.get()
        if message == 'QUIT':
            break
        console_text.config(state=tk.NORMAL)
        console_text.insert(tk.END, message + '\n')
        console_text.see(tk.END)
        console_text.config(state=tk.DISABLED)
        log_queue.task_done()

def download_file(service, file_id, file_name, queue):
    """Download a file from Google Drive."""
    log_to_console(f"Starting download of file: {file_name}", queue)
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        log_to_console(f"Downloading {file_name}: {int(status.progress() * 100)}%", queue)
    fh.close()
    # Check if the file is empty
    if os.path.getsize(file_name) == 0:
        log_to_console(f"downloaded empty file: {file_name}", queue)
    log_to_console(f"Finished download of file: {file_name}", queue)

def export_google_docs_file(service, file_id, file_name, export_mime_type, queue):
    """Export a Google Docs Editors file to a specified format."""
    log_to_console(f"Starting export of file: {file_name}", queue)
    request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        log_to_console(f"Downloading {file_name}: {int(status.progress() * 100)}%", queue)
    fh.close()
    # Check if the file is empty
    if os.path.getsize(file_name) == 0:
        log_to_console(f"downloaded empty file: {file_name}", queue)
    log_to_console(f"Finished export of file: {file_name}", queue)

def handle_file(service, file, error_log, download_folder, queue):
    """Handle downloading or exporting a file based on its type."""
    file_id = file['id']
    file_name = file['name']
    mime_type = file.get('mimeType')

    if mime_type not in SUPPORTED_MIME_TYPES:
        return

    try:
        if mime_type == 'application/pdf':
            download_file(service, file_id, os.path.join(download_folder, file_name), queue)
        elif mime_type == 'application/vnd.google-apps.document':
            export_google_docs_file(service, file_id, os.path.join(download_folder, f"{file_name}.pdf"), 'application/pdf', queue)
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            export_google_docs_file(service, file_id, os.path.join(download_folder, f"{file_name}.pdf"), 'application/pdf', queue)
    except Exception as e:
        logger.error(f"Error processing file {file_name} ({file_id}): {e}")
        error_log.append([file_id, file_name, str(e)])
        log_to_console(f"Error processing file {file_name} ({file_id}): {e}", queue)

def get_files_page(service, page_token=None):
    """Retrieve a page of files where the user has at least viewer access."""
    results = service.files().list(
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType)",
        pageToken=page_token
    ).execute()
    return results.get('files', []), results.get('nextPageToken')

def process_files(service, files, error_log, download_folder, queue):
    """Process files using multiple threads."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(handle_file, service, file, error_log, download_folder, queue) for file in files]
        for future in futures:
            future.result()

def start_transfer(credentials_path, download_folder, queue):
    try:
        if not credentials_path:
            raise ValueError("Credentials file not selected.")

        service = authenticate(credentials_path)
        page_token = None
        total_files = 0
        error_log = []

        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        while True:
            files, page_token = get_files_page(service, page_token)
            total_files += len(files)
            process_files(service, files, error_log, download_folder, queue)
            if not page_token:
                break

        messagebox.showinfo("Download Complete", f"Total number of files processed: {total_files}")
        log_to_console(f"Total number of files processed: {total_files}", queue)

        if error_log:
            with open('error_log.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['File ID', 'File Name', 'Error'])
                writer.writerows(error_log)
            messagebox.showinfo("Errors Logged", "Errors logged to error_log.csv")
            log_to_console("Errors logged to error_log.csv", queue)
    except Exception as e:
        messagebox.showerror("Error", str(e))
        log_to_console(f"Error: {str(e)}", queue)

# Create the main window
root = tk.Tk()
root.title("Google Drive File Downloader")
root.geometry("400x400")

# Variables to store GUI elements
download_folder_path = tk.StringVar(root, os.path.expanduser("~"))  # Default to user's home directory
credentials_path = tk.StringVar(root)

# GUI components
def select_credentials_file():
    credentials_path_local = filedialog.askopenfilename(
        title="Select Credentials File",
        filetypes=(("JSON Files", "*.json"), ("All Files", "*.*"))
    )
    start_transfer_button.config(state=tk.NORMAL if credentials_path_local else tk.DISABLED)
    credentials_path.set(credentials_path_local)

def select_download_folder():
    selected_folder = filedialog.askdirectory(title="Select Download Folder")
    download_folder_path.set(selected_folder)

select_credentials_button = tk.Button(root, text="Select Credentials File", command=select_credentials_file)
select_credentials_button.pack(pady=20)

select_folder_button = tk.Button(root, text="Select Download Folder", command=select_download_folder)
select_folder_button.pack(pady=10)

console_text = tk.Text(root, height=10, wrap=tk.WORD, state=tk.DISABLED)
console_text.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

log_queue = Queue()
console_thread = Thread(target=update_console, args=(console_text, log_queue))
console_thread.start()

def start_transfer_action():
    start_transfer_thread = Thread(target=start_transfer, args=(credentials_path.get(), download_folder_path.get(), log_queue))
    start_transfer_thread.start()

def update_gui():
    if log_queue.qsize() > 0:
        message = log_queue.get()
        console_text.config(state=tk.NORMAL)
        console_text.insert(tk.END, message + '\n')
        console_text.see(tk.END)
        console_text.config(state=tk.DISABLED)
        root.after(1500, update_gui)  # Call update_gui again after 100ms

start_transfer_button = tk.Button(root, text="Start Transfer", command=start_transfer_action, state=tk.DISABLED)
start_transfer_button.pack(pady=20)

update_gui()  # Start updating the GUI

# Start the GUI event loop
root.mainloop()

# Signal the console thread to quit
log_queue.put('QUIT')
console_thread.join()
# Google Drive Downloader

This Python script allows you to download files from Google Drive using the Google Drive API. It supports downloading PDF files and exporting Google Docs and Google Sheets files to PDF format.

## Installation

1. Clone this repository to your local machine:

    ```bash
    git clone https://github.com/your-username/GoogleDriveDownloader.git
    cd GoogleDriveDownloader
    ```

2. Install the required dependencies from `requirements.txt`:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Obtain your Google Drive API credentials:
    - Go to the Google Developers Console.
    - Create a new project and enable the Google Drive API.
    - Create OAuth 2.0 credentials (client ID and client secret).
    - Download the credentials JSON file and save it as `credentials.json` in the project directory.

2. Run the script:

    ```bash
    python main.py
    ```

3. The script will prompt you to authorize access to your Google Drive account. Follow the instructions in the terminal.

4. Once authorized, you can select files to download or export. The downloaded files will be saved in the specified download folder.

## Notes

- Make sure you have Python 3.x installed.
- If you encounter any issues, refer to the Google Drive API documentation for troubleshooting.


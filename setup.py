from setuptools import setup

APP = ['main.py']  # Replace with the name of your Python script
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['googleapiclient', 'google', 'google_auth_oauthlib', 'google_auth_httplib2']
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

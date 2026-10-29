# Personal Expense Tracker

A Windows-friendly desktop app for recording and reviewing personal expenses. The current application is a single-file Python and Tkinter program that stores data locally in JSON and uses only the Python standard library.

## Features

- Add, edit, search, filter, and delete expense records
- Validate dates and positive numeric amounts
- View totals, record counts, average spending, and the top category
- Review category breakdown and a six-month trend chart
- Set and remove category spending limits
- Export expenses to CSV
- Load demo records to explore the charts
- Save records locally and show action feedback in the status bar

## Requirements

- Python 3.8 or newer
- Tkinter enabled in the Python installation
- No third-party packages or internet connection required

## Run on Windows

1. Open this folder in File Explorer.
2. Double-click `start_app.bat`.

Alternatively, open PowerShell or Command Prompt in this folder and run:

```powershell
py expense_tracker_app.py
```

To run from Visual Studio Code, open `expense_tracker_app.py` and choose **Run Python File** or press **F5**.

## Data and privacy

The current app creates `expenses.json` beside `expense_tracker_app.py` when it first saves data. Expense records and category budget limits stay on this computer. CSV exports may contain personal financial information; choose a safe location for them. Local data and exports are excluded from this Git repository.

## Project files

- `expense_tracker_app.py` - current Tkinter app using JSON storage
- `start_app.bat` - Windows launcher for the current app
- `expense_tracker_gui.py` and `expense_tracker/` - earlier modular SQLite desktop version
- `expense_tracker.py` - earlier command-line SQLite version
- `README.md` - setup and usage instructions

The SQLite versions are retained for learning and comparison. They are separate from the current JSON-based GUI.

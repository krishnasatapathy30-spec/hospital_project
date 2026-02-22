Hospital Project — Quick run & public URL via ngrok
===============================================

Overview
--------
This is a small Flask app for a hospital demo. The app runs on localhost:5000 by default.

Run locally (Windows, using the included venv)
------------------------------------------------
1. Activate the venv:

```powershell
E:\Hospital_project\venv\Scripts\Activate.ps1
```

2. Install requirements (if needed):

```powershell
pip install -r "main folder/requirements.txt"
```

3. Start the app (from the project root):

```powershell
E:\Hospital_project\venv\Scripts\python.exe "app.py"
```

Quick open helper
-----------------
Run the provided PowerShell helper which activates the venv, opens the app in a new terminal window and launches your browser:

```powershell
.\open_project.ps1
```

Run the smoke tests
-------------------
```powershell
E:\Hospital_project\venv\Scripts\python.exe tests/smoke_tests.py
```

Expose to the internet with ngrok
--------------------------------
The repo includes `start_ngrok.py` which uses `pyngrok`. To start a public tunnel (your running app must be on port 5000):

```powershell
E:\Hospital_project\venv\Scripts\python.exe start_ngrok.py
```

When the tunnel starts, the script prints a public URL such as `https://xxxxxxxx.ngrok.io` — opening that URL in a browser will forward to the running Flask app.

Notes
-----
- Keep the Flask process running while using the public ngrok URL.
- For production use do not run Flask with `debug=True` and set a secure `SECRET_KEY`.

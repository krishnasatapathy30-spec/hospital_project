# Hospital Project — Simple Flask App

This is a small Flask-based hospital patient management app (students-friendly). It includes:

- User authentication (SQLite + hashed passwords)
- Add / Edit / Delete patients (SQLite)
- Static assets in the `static/` folder
- Templates in `templates/` (login, dashboard, edit)

Quick start (Windows / VS Code):

1. Open the workspace folder in VS Code (`main folder`).
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Run the app:

```powershell
cd "main folder"
python app.py
```

5. Open http://127.0.0.1:5000/login in your browser.

Seeded users:

- `admin` / `password`
- `ramesh` / `12345`
- `krishna` / `krishna123`

Notes:

- Use the Flask URL to view templates rendered with Jinja — Live Server won't render Jinja templates.
- To reset the database, delete `hospital.db` and restart the app.

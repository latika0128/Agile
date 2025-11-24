# Frontend demo (Flask)

This is a small Python/Flask demo frontend for the PhonePe-style app. It is intentionally minimal and uses an in-memory store for demonstration.

Run (Windows PowerShell):
```powershell
cd frontend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000/ in your browser.

Environment variables:
- `FRONTEND_SECRET` - Flask `secret_key` for sessions (optional)
- `BACKEND_URL` - If set, frontend can be extended to call a real backend instead of the demo store.

Notes:
- This is a frontend demo only. Do not use the in-memory store for production.
- I can extend this to call your backend API (real UPI/payment flows), add client-side validation, or convert to a React/React-Native frontend.

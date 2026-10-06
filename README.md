# EventHub Full-Stack College Event Management System

This project takes the supplied EventHub frontend and connects it to a real FastAPI + SQLite backend. It includes student authentication, event data, registrations, Razorpay payment order/verification, signed QR passes, camera scanning, attendance, and an admin panel.

## Run on Windows

```powershell
cd EventHub_FullStack
py -m venv .venv
.\.venv\Scripts\Activate.ps1
cd backend
pip install -r requirements.txt
copy .env.example .env
python seed.py
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/

### Demo student
student@eventhub.test / student123

### Admin
admin / admin123

Admin: http://127.0.0.1:8000/admin/login.html
Scanner: http://127.0.0.1:8000/admin/scanner.html
API docs: http://127.0.0.1:8000/docs

## Razorpay
Put Razorpay TEST credentials in `backend/.env`:

```env
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

The backend creates the order and verifies the checkout signature before a paid registration is confirmed and its pass is issued. Keep the secret only on the server. For production, configure a Razorpay webhook and set `RAZORPAY_WEBHOOK_SECRET`; use HTTPS.

For QR testing before event day, `ALLOW_EARLY_SCAN=true` is convenient. Set it to `false` for actual gate-time enforcement.

Do not open HTML files by double-clicking them; FastAPI serves both frontend and API.

# Firebase Push Setup (Android)

Use this to enable closed-app notification bar delivery for student users.

## 1) Create/verify Firebase Android app
- Firebase project -> add Android app package: `com.example.adr_mobile_app`
- Download `google-services.json`
- Put file at:
  - `/Users/anujmishra/Desktop/Adr_app/mobile_app/android/app/google-services.json`

## 2) Create Firebase service account key
- Firebase Console -> Project settings -> Service accounts
- Generate new private key (JSON)
- Store it outside git, for example:
  - `/Users/anujmishra/Desktop/Adr_app/backend/keys/fcm-service-account.json`

## 3) Backend env
Update `/Users/anujmishra/Desktop/Adr_app/backend/.env`:

```env
FCM_PROJECT_ID=your-firebase-project-id
FCM_CREDENTIALS_PATH=/Users/anujmishra/Desktop/Adr_app/backend/keys/fcm-service-account.json
# leave this empty when using FCM_CREDENTIALS_PATH
FCM_CREDENTIALS_JSON=
```

## 4) Verify setup
From backend:

```bash
cd /Users/anujmishra/Desktop/Adr_app/backend
source .venv/bin/activate
python -m app.scripts.verify_push_setup
```

Expected:
- `FCM_PROJECT_ID: OK`
- `FCM_CREDENTIALS_PATH file: OK`
- `google-services.json: OK`
- `push_ready: OK`

## 5) Run stack
Terminal 1 (backend):

```bash
cd /Users/anujmishra/Desktop/Adr_app/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 (celery worker):

```bash
cd /Users/anujmishra/Desktop/Adr_app/backend
source .venv/bin/activate
celery -A app.workers.celery_app:celery_app worker -l info -Q notifications_bulk,integrations,assessments
```

Terminal 3 (mobile):

```bash
cd /Users/anujmishra/Desktop/Adr_app/mobile_app
flutter pub get
flutter run -d <DEVICE_ID> --dart-define=API_BASE_URL=http://<LAN_IP>:8000/api/v1
```

## 6) 2-minute device test
1. Login as student on mobile app.
2. Keep app in background, then close app.
3. Trigger a notification from admin/teacher API/UI.
4. Confirm:
   - Android notification bar shows it with sound.
   - Opening app -> bell count increments.
   - Read notification -> bell count decrements.
   - Read all -> bell count becomes zero.
   - Notification list shows only last 24h records.

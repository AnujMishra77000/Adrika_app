# ADR Mobile App (Flutter)

Multi-role mobile app for ADR platform.

## Supported roles in this build

- Student
- Teacher
- Parent (phase-4 flow)

## Run locally

1. Start backend first on `http://localhost:8000`
2. Install packages:
   - `flutter pub get`
3. Run on Android emulator:
   - `flutter run -d <android_device_id>`
4. Run on iOS simulator:
   - `flutter run -d <ios_simulator_id> --dart-define=API_BASE_URL=http://localhost:8000/api/v1`
5. Run on Chrome:
   - `flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api/v1`

For physical phones, pass your Mac LAN URL via `--dart-define=API_BASE_URL=...`.

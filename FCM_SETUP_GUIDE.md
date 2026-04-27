# Firebase Cloud Messaging (FCM) Configuration Guide

The project's codebase is already prepared to send FCM notifications, but the actual Firebase credentials file is currently missing. Because of this, the notifications are falling back to "mock mode" (they are only being logged to the console).

To fully enable FCM push notifications, please follow the steps below:

## 1. Generate Firebase Admin SDK Private Key

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Select your Firebase project (or create a new one if you haven't yet).
3. Click on the **Gear icon** next to "Project Overview" in the top-left sidebar and select **Project settings**.
4. Navigate to the **Service accounts** tab.
5. Make sure **Node.js** or **Python** is selected, and click the **Generate new private key** button.
6. A warning dialog will appear. Click **Generate key** to download the JSON file containing your credentials.

## 2. Add Credentials to the Project

1. Rename the downloaded JSON file to exactly `firebase-adminsdk.json`.
2. Move this file into the root directory of the project (i.e., `d:\code\python\medical_api\firebase-adminsdk.json`).
3. **IMPORTANT:** Ensure that `firebase-adminsdk.json` is listed in your `.gitignore` file. You should **never** commit this file to version control, as it contains highly sensitive private keys.

## 3. Environment Variables (Optional)

By default, the `settings.py` file is configured to look for the credentials file at the project root:
```python
FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default=str(BASE_DIR / 'firebase-adminsdk.json'))
```

If you prefer to place the file elsewhere or name it differently, you can override this by adding the following line to your `.env` file:
```env
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/your/firebase-credentials.json
```

## 4. Verification

Once the JSON file is in place, restart your Django development server. When the app attempts to send an FCM notification (or when `initialize_firebase()` is called), you should see the following log message in your console:
> "Firebase Admin SDK initialized successfully."

If the file is missing or the path is incorrect, you will see a warning:
> "Firebase credentials not found at [path]. Notifications will be mocked."

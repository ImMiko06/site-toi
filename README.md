# Site Toi

Mobile-first Django MVP for a wedding social network and digital archive.

## What is included

- Gatekeeper login with nickname and password.
- Home screen with wedding info and interactive table map.
- Album screen with feed and popular posts.
- Separate Authors screen in the bottom navigation, using a search/loupe icon.
- Upload screen for photo/video files.
- Account screen with the current guest's uploads.
- Django admin for manual upload override: `auto`, `allow`, `deny`.

## Run

This project already contains local Django dependencies in `.vendor`.

```powershell
cd "C:\Users\Acer Nitro V15\Documents\New project\site toi"
& "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe" manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/
```

Demo guest:

```text
nickname: aigerim
password: wedding123
```

Guest admin inside the app:

```text
nickname: toi_admin
password: admin12345
```

After login, open:

```text
http://127.0.0.1:8000/manage/
```

This guest can approve or reject upload requests directly in the wedding app.

## Google Drive media

By default uploads are stored locally in `media/`. To save uploaded photos and videos to a regular Google Drive folder, use OAuth with your Google account. Service account keys can read shared folders, but Google Drive does not give service accounts personal Drive storage quota.

1. Enable the Google Drive API in Google Cloud.
2. Create an OAuth Client ID: `APIs & Services` -> `Credentials` -> `Create credentials` -> `OAuth client ID` -> `Desktop app`.
3. Download the OAuth Client ID JSON file.
4. Create a folder in Google Drive and copy the folder ID from the folder URL.

```powershell
pip install -r requirements.txt
$env:GOOGLE_DRIVE_OAUTH_CLIENT_SECRETS="C:\path\to\oauth-client.json"
python manage.py authorize_google_drive

$env:GOOGLE_DRIVE_STORAGE="true"
$env:GOOGLE_DRIVE_FOLDER_ID="your-google-drive-folder-id"
python manage.py runserver 127.0.0.1:8000
```

Optional settings:

```powershell
$env:GOOGLE_DRIVE_PUBLIC="true"
$env:GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES="true"
$env:GOOGLE_DRIVE_TOKEN_FILE="C:\path\to\google-drive-token.json"
```

`GOOGLE_DRIVE_PUBLIC=true` makes each uploaded file visible to anyone with the link, so photos and videos can render in the site feed. If the file is private, visitors will not see it unless they are logged into a Google account with access.

## Admin

Local dev admin is already created:

```text
username: admin
password: admin12345
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

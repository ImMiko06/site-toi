Set-Location -LiteralPath "C:\Users\Acer Nitro V15\Documents\New project\site toi"
$env:GOOGLE_DRIVE_STORAGE = "true"
$env:GOOGLE_DRIVE_FOLDER_ID = "13HHHHfLsKXHrOxUcxLSk7YVTA94b-EEs"
& "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe" manage.py runserver 127.0.0.1:8000 --noreload

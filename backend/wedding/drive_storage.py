import io
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.core.files.storage import Storage

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


class GoogleDriveStorage(Storage):
    """Django storage backend that saves uploaded media into Google Drive."""

    def __init__(self, folder_id=None, public=None):
        self.folder_id = folder_id if folder_id is not None else settings.GOOGLE_DRIVE_FOLDER_ID
        self.public = public if public is not None else settings.GOOGLE_DRIVE_PUBLIC
        self._service = None
        self._http = None

    def _get_service(self):
        if self._service is None:
            try:
                import google.auth
                import google_auth_httplib2
                import httplib2
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
            except ImportError as error:
                raise ImportError(
                    "Google Drive storage requires google-api-python-client and google-auth. "
                    "Install them with `pip install -r requirements.txt`."
                ) from error

            scopes = ["https://www.googleapis.com/auth/drive"]
            if settings.GOOGLE_DRIVE_TOKEN_JSON:
                credentials = Credentials.from_authorized_user_info(json.loads(settings.GOOGLE_DRIVE_TOKEN_JSON), scopes)
            elif os.path.exists(settings.GOOGLE_DRIVE_TOKEN_FILE):
                credentials = Credentials.from_authorized_user_file(settings.GOOGLE_DRIVE_TOKEN_FILE, scopes)
            else:
                credentials, _ = google.auth.default(scopes=scopes)
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                Path(settings.GOOGLE_DRIVE_TOKEN_FILE).write_text(credentials.to_json(), encoding="utf-8")
            http = httplib2.Http(timeout=settings.GOOGLE_DRIVE_TIMEOUT_SECONDS)
            authed_http = google_auth_httplib2.AuthorizedHttp(credentials, http=http)
            self._http = authed_http
            self._service = build("drive", "v3", http=authed_http, cache_discovery=False)
        return self._service

    def get_file_metadata(self, file_id):
        return self._get_service().files().get(
            fileId=file_id,
            fields="id,name,mimeType,size",
            supportsAllDrives=settings.GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES,
        ).execute(num_retries=settings.GOOGLE_DRIVE_UPLOAD_RETRIES)

    def read_file(self, file_id, headers=None):
        self._get_service()
        response, content = self._http.request(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            method="GET",
            headers=headers or {},
        )
        return response, content

    def _save(self, name, content):
        try:
            from googleapiclient.http import MediaIoBaseUpload
        except ImportError as error:
            raise ImportError(
                "Google Drive storage requires google-api-python-client. "
                "Install it with `pip install -r requirements.txt`."
            ) from error

        service = self._get_service()
        file_name = Path(name).name
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        file_obj = self._seekable_file(content)

        metadata = {"name": file_name}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]

        media = MediaIoBaseUpload(
            file_obj,
            mimetype=content_type,
            chunksize=settings.GOOGLE_DRIVE_UPLOAD_CHUNK_SIZE,
            resumable=True,
        )
        upload_request = service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=settings.GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES,
        )
        drive_file = self._execute_upload(upload_request)
        file_id = drive_file["id"]

        if self.public:
            service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                fields="id",
                supportsAllDrives=settings.GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES,
            ).execute(num_retries=settings.GOOGLE_DRIVE_UPLOAD_RETRIES)

        return self._stored_name(file_id, file_name)

    def _execute_upload(self, upload_request):
        response = None
        while response is None:
            _, response = upload_request.next_chunk(num_retries=settings.GOOGLE_DRIVE_UPLOAD_RETRIES)
        return response

    def _seekable_file(self, content):
        file_obj = getattr(content, "file", content)
        try:
            file_obj.seek(0)
            return file_obj
        except (AttributeError, OSError):
            buffer = io.BytesIO()
            for chunk in content.chunks():
                buffer.write(chunk)
            buffer.seek(0)
            return buffer

    def _stored_name(self, file_id, original_name):
        suffix = Path(original_name).suffix
        return f"gdrive/{file_id}{suffix}"

    def _file_id_from_name(self, name):
        stored_name = Path(name).name
        return stored_name.split(".", 1)[0]

    def url(self, name):
        file_id = self._file_id_from_name(name)
        suffix = Path(name).suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            return f"https://drive.google.com/thumbnail?{urlencode({'id': file_id, 'sz': 'w1600'})}"
        if suffix in VIDEO_EXTENSIONS:
            return f"/drive-media/{file_id}{suffix}"
        return f"https://drive.google.com/uc?{urlencode({'export': 'download', 'id': file_id})}"

    def exists(self, name):
        return False

    def delete(self, name):
        file_id = self._file_id_from_name(name)
        self._get_service().files().delete(
            fileId=file_id,
            supportsAllDrives=settings.GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES,
        ).execute()

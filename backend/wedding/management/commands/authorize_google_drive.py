from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Authorize a regular Google account for Google Drive uploads."

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-secrets",
            default=settings.GOOGLE_DRIVE_OAUTH_CLIENT_SECRETS,
            help="Path to OAuth Client ID JSON downloaded from Google Cloud.",
        )
        parser.add_argument(
            "--token-file",
            default=settings.GOOGLE_DRIVE_TOKEN_FILE,
            help="Where to save the authorized user token JSON.",
        )

    def handle(self, *args, **options):
        client_secrets = options["client_secrets"]
        token_file = Path(options["token_file"])
        if not client_secrets:
            raise CommandError(
                "Pass --client-secrets or set GOOGLE_DRIVE_OAUTH_CLIENT_SECRETS "
                "to an OAuth Client ID JSON file."
            )
        if not Path(client_secrets).exists():
            raise CommandError(f"OAuth Client ID JSON not found: {client_secrets}")

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as error:
            raise CommandError(
                "google-auth-oauthlib is required. Install dependencies with `pip install -r requirements.txt`."
            ) from error

        scopes = ["https://www.googleapis.com/auth/drive"]
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets, scopes=scopes)
        credentials = flow.run_local_server(port=0)

        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(credentials.to_json(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Google Drive token saved: {token_file}"))

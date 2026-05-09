from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wedding", "0004_alter_uploadaccessrequest_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="weddingevent",
            name="guest_uploads_enabled",
            field=models.BooleanField(
                default=True,
                help_text="When disabled, only host guests can upload media.",
            ),
        ),
    ]

from django import forms

from .models import MediaComment, MediaPost, ReceptionTable, UploadAccessRequest


class GatekeeperForm(forms.Form):
    nickname = forms.CharField(
        min_length=2,
        max_length=40,
        widget=forms.TextInput(attrs={"placeholder": "Ваш никнейм", "autocomplete": "username"}),
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={"placeholder": "Пароль минимум 6 символов", "autocomplete": "current-password"}),
    )


class MediaUploadForm(forms.ModelForm):
    class Meta:
        model = MediaPost
        fields = ("media_type", "file", "caption")
        widgets = {
            "media_type": forms.Select(),
            "caption": forms.TextInput(attrs={"placeholder": "Подпись к моменту"}),
            "file": forms.FileInput(attrs={"accept": "image/*,video/*"}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = MediaComment
        fields = ("body",)
        widgets = {
            "body": forms.TextInput(attrs={"placeholder": "Написать комментарий"}),
        }


class UploadAccessRequestForm(forms.ModelForm):
    class Meta:
        model = UploadAccessRequest
        fields = ("message",)
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "placeholder": "Например: хочу добавить фото со стола друзей",
                    "rows": 3,
                }
            )
        }


class AddGuestToTableForm(forms.Form):
    display_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Имя и фамилия гостя"}),
    )
    table = forms.ModelChoiceField(queryset=ReceptionTable.objects.none(), empty_label=None)

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        if event is not None:
            self.fields["table"].queryset = event.tables.order_by("number")

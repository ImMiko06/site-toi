from datetime import timedelta
import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Max, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .drive_storage import GoogleDriveStorage
from .forms import AddGuestToTableForm, CommentForm, GatekeeperForm, MediaUploadForm, UploadAccessRequestForm
from .models import (
    MediaComment,
    MediaLike,
    MediaPost,
    ReceptionTable,
    TableSeat,
    UploadAccessRequest,
    WeddingEvent,
    WeddingGuest,
)


def is_timeout_error(error):
    current = error
    while current:
        if isinstance(current, TimeoutError) or "timed out" in str(current).lower():
            return True
        current = current.__cause__ or current.__context__
    return False


def parse_byte_range(range_header, size):
    if not range_header or not range_header.startswith("bytes="):
        return None
    value = range_header.replace("bytes=", "", 1).split(",", 1)[0].strip()
    if "-" not in value:
        return None
    start_value, end_value = value.split("-", 1)
    if start_value == "":
        suffix_length = int(end_value or 0)
        if suffix_length <= 0:
            return None
        return max(size - suffix_length, 0), size - 1
    start = int(start_value)
    end = int(end_value) if end_value else size - 1
    if start >= size:
        return None
    return start, min(end, size - 1)


def filename_for_post(post):
    suffix = Path(post.file.name or post.external_url or "").suffix
    if not suffix:
        suffix = ".mp4" if post.media_type == MediaPost.MediaType.VIDEO else ".jpg"
    return f"{post.event.slug}-{post.id}{suffix}"


def get_default_event():
    now = timezone.now()
    demo_starts_at = now + timedelta(days=7)
    event, created = WeddingEvent.objects.get_or_create(
        slug="aruzhan-dias",
        defaults={
            "title": "Аружан & Нурдаулет",
            "groom_name": "Нурдаулет",
            "bride_name": "Аружан",
            "venue_name": "Royal Hall",
            "venue_address": "Almaty",
            "starts_at": demo_starts_at,
            "upload_start": demo_starts_at - timedelta(hours=1),
            "upload_end": demo_starts_at + timedelta(days=1),
            "invitation_title": "Электронный пригласительный",
            "invitation_text": "Добро пожаловать в свадебную соцсеть. Здесь живут фото, эмоции и воспоминания нашего тоя.",
            "is_published": True,
        },
    )

    if created or not event.tables.exists():
        create_demo_data(event)

    ensure_event_details(event)
    ensure_banquet_tables(event)
    ensure_host_guest(event)
    ensure_gallery_samples(event)

    return event


def ensure_event_details(event):
    updates = {
        "title": "Аружан & Нурдаулет",
        "groom_name": "Нурдаулет",
        "bride_name": "Аружан",
        "venue_name": "Royal Hall",
        "venue_address": "Алматы, проспект Аль-Фараби 77/7",
        "invitation_title": "Приглашение на той",
        "invitation_text": (
            "Дорогие гости, будем рады разделить с вами этот особенный вечер. "
            "Здесь можно найти свое место за столом, открыть карту, загрузить фото и сохранить лучшие моменты праздника."
        ),
    }
    changed = []
    for field, value in updates.items():
        if getattr(event, field) != value:
            setattr(event, field, value)
            changed.append(field)
    if changed:
        event.save(update_fields=changed + ["updated_at"])


def ensure_banquet_tables(event):
    table_specs = [
        (1, "VIP 1", True),
        (2, "Родители", True),
        (3, "Родственники", False),
        (4, "Құдалар", True),
        (5, "Друзья семьи", False),
        (6, "Родня", False),
        (7, "Друзья жениха", False),
        (8, "Друзья невесты", False),
        (9, "Коллеги пары", False),
        (10, "Соседи", False),
        (11, "Гости 11", False),
        (12, "Гости 12", False),
    ]
    for number, name, is_vip in table_specs:
        table, created = ReceptionTable.objects.get_or_create(
            event=event,
            number=number,
            defaults={
                "name": name,
                "capacity": 12,
                "is_vip": is_vip,
                "position_x": 50,
                "position_y": 50,
            },
        )
        updates = []
        if table.capacity < 10:
            table.capacity = 12
            updates.append("capacity")
        if number in {1, 2, 4} and not table.is_vip:
            table.is_vip = True
            updates.append("is_vip")
        if created:
            continue
        if updates:
            table.save(update_fields=updates)


def ensure_gallery_samples(event):
    sample_author = (
        WeddingGuest.objects.filter(event=event, nickname="toi_admin").first()
        or WeddingGuest.objects.filter(event=event, upload_override=WeddingGuest.UploadOverride.ALLOW).first()
        or WeddingGuest.objects.filter(event=event).first()
    )
    if not sample_author:
        return

    samples = [
        (
            "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=900&q=80",
            "Первые кадры свадебного утра.",
        ),
        (
            "https://images.unsplash.com/photo-1529634597503-139d3726fed5?auto=format&fit=crop&w=900&q=80",
            "Нежные детали зала перед встречей гостей.",
        ),
        (
            "https://images.unsplash.com/photo-1520854221256-17451cc331bf?auto=format&fit=crop&w=900&q=80",
            "Момент, который хочется сохранить.",
        ),
        (
            "https://images.unsplash.com/photo-1537633552985-df8429e8048b?auto=format&fit=crop&w=900&q=80",
            "Праздничная атмосфера уже здесь.",
        ),
    ]
    for external_url, caption in samples:
        MediaPost.objects.get_or_create(
            event=event,
            caption=caption,
            defaults={
                "author": sample_author,
                "media_type": MediaPost.MediaType.PHOTO,
                "external_url": external_url,
                "status": MediaPost.Status.APPROVED,
            },
        )


def ensure_host_guest(event):
    host = WeddingGuest.objects.filter(event=event, nickname="toi_admin").first()
    if not host:
        host = WeddingGuest(
            event=event,
            nickname="toi_admin",
            display_name="Админ тоя",
            upload_override=WeddingGuest.UploadOverride.ALLOW,
            is_host=True,
        )
        host.set_password("admin12345")
        host.save()
        return

    changed_fields = []
    if not host.is_host:
        host.is_host = True
        changed_fields.append("is_host")
    if host.upload_override != WeddingGuest.UploadOverride.ALLOW:
        host.upload_override = WeddingGuest.UploadOverride.ALLOW
        changed_fields.append("upload_override")
    if changed_fields:
        host.save(update_fields=changed_fields)


def create_demo_data(event):
    tables = [
        ("VIP 1", 1, True, 25, 30),
        ("Друзья", 2, False, 72, 34),
        ("Родные", 3, False, 35, 66),
        ("Коллеги", 4, False, 72, 70),
    ]
    table_objects = []
    for name, number, is_vip, x, y in tables:
        table_objects.append(
            ReceptionTable.objects.create(
                event=event,
                name=name,
                number=number,
                capacity=10,
                is_vip=is_vip,
                position_x=x,
                position_y=y,
            )
        )

    guests = [
        ("aigerim", "Айгерим Омарова", table_objects[0]),
        ("azamat", "Азамат Омаров", table_objects[0]),
        ("aru_sy", "Аружан Сыздыкова", table_objects[0]),
        ("timur_photo", "Тимур Нурланов", table_objects[1]),
        ("dias_friend", "Ерлан Сапаров", table_objects[1]),
        ("madina", "Мадина Абишева", table_objects[2]),
        ("aliya", "Алия Каримова", table_objects[2]),
        ("arman", "Арман Жаксылыков", table_objects[3]),
    ]
    guest_objects = []
    for index, (nickname, display_name, table) in enumerate(guests, start=1):
        guest = WeddingGuest(
            event=event,
            table=table,
            nickname=nickname,
            display_name=display_name,
            upload_override=WeddingGuest.UploadOverride.ALLOW,
        )
        guest.set_password("wedding123")
        guest.save()
        TableSeat.objects.create(event=event, table=table, guest=guest, seat_number=index)
        guest_objects.append(guest)

    samples = [
        ("photo", "/static/wedding/img/sample-toast.svg", "Первый тост уже собрал весь зал.", guest_objects[0]),
        ("photo", "/static/wedding/img/sample-dance.svg", "Свет, музыка и самый красивый выход вечера.", guest_objects[1]),
        ("photo", "/static/wedding/img/sample-bride.svg", "Когда все подруги наконец поймали идеальный кадр.", guest_objects[2]),
    ]
    for media_type, url, caption, author in samples:
        post = MediaPost.objects.create(
            event=event,
            author=author,
            media_type=media_type,
            external_url=url,
            caption=caption,
            status=MediaPost.Status.APPROVED,
        )
        for guest in guest_objects:
            MediaLike.objects.get_or_create(post=post, guest=guest)


def session_guest(request):
    guest_id = request.session.get("guest_id")
    event_id = request.session.get("event_id")
    if not guest_id or not event_id:
        return None
    return WeddingGuest.objects.select_related("event", "table").filter(id=guest_id, event_id=event_id, is_active=True).first()


def require_guest(view_func):
    def wrapper(request, *args, **kwargs):
        get_default_event()
        guest = session_guest(request)
        if not guest:
            return redirect("wedding:gatekeeper")
        request.wedding_guest = guest
        request.wedding_event = guest.event
        return view_func(request, *args, **kwargs)

    return wrapper


def require_host_guest(view_func):
    @require_guest
    def wrapper(request, *args, **kwargs):
        if not request.wedding_guest.is_host:
            messages.error(request, "Этот раздел доступен только админу тоя.")
            return redirect("wedding:account")
        return view_func(request, *args, **kwargs)

    return wrapper


def base_context(request, active):
    guest = request.wedding_guest
    event = request.wedding_event
    seconds_until_start = max(0, int((event.starts_at - timezone.now()).total_seconds()))
    return {
        "event": event,
        "guest": guest,
        "active": active,
        "can_upload": guest.can_upload(),
        "show_invite": seconds_until_start > 0,
        "seconds_until_start": seconds_until_start,
    }


def make_table_guest_nickname(event):
    for _ in range(12):
        nickname = f"guest_{uuid4().hex[:10]}"
        if not WeddingGuest.objects.filter(event=event, nickname=nickname).exists():
            return nickname
    return f"guest_{uuid4().hex}"[:40]


def next_table_seat_number(table):
    return (table.seats.aggregate(max_seat=Max("seat_number"))["max_seat"] or 0) + 1


def gatekeeper(request):
    event = get_default_event()
    if session_guest(request):
        return redirect("wedding:home")

    form = GatekeeperForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        nickname = form.cleaned_data["nickname"].strip()
        password = form.cleaned_data["password"]
        guest = WeddingGuest.objects.filter(event=event, nickname__iexact=nickname).first()

        if guest and not guest.check_password(password):
            form.add_error("password", "Неверный пароль для этого никнейма.")
        else:
            if not guest:
                guest = WeddingGuest(event=event, nickname=nickname, display_name=nickname)
                guest.set_password(password)
                guest.save()
            guest.last_seen_at = timezone.now()
            guest.save(update_fields=["last_seen_at"])
            request.session["guest_id"] = guest.id
            request.session["event_id"] = event.id
            return redirect("wedding:home")

    return render(request, "wedding/gatekeeper.html", {"form": form, "event": event})


def logout_view(request):
    request.session.flush()
    return redirect("wedding:gatekeeper")


@require_guest
def home(request):
    tables = request.wedding_event.tables.prefetch_related("guests").all()
    featured_posts = (
        MediaPost.objects.filter(
            event=request.wedding_event,
            status=MediaPost.Status.APPROVED,
            media_type=MediaPost.MediaType.PHOTO,
        )
        .exclude(external_url__startswith="/static/wedding/img/")
        .select_related("author")
        .order_by("-created_at")[:4]
    )
    context = base_context(request, "home") | {
        "tables": tables,
        "featured_posts": featured_posts,
        "guest_count": WeddingGuest.objects.filter(event=request.wedding_event, is_active=True).count(),
        "media_count": MediaPost.objects.filter(event=request.wedding_event, status=MediaPost.Status.APPROVED).count(),
        "twogis_url": f"https://2gis.kz/almaty/search/{request.wedding_event.venue_name} {request.wedding_event.venue_address}",
    }
    return render(request, "wedding/home.html", context)


@require_guest
def tables_api(request):
    tables = request.wedding_event.tables.prefetch_related("guests").all()
    payload = [
        {
            "table_id": table.id,
            "table_number": str(table.number),
            "table_name": table.name,
            "capacity": table.capacity,
            "guests": [
                {
                    "guest_id": guest.id,
                    "name": guest.display_name or guest.nickname,
                }
                for guest in table.guests.all()
            ],
        }
        for table in tables
    ]
    return JsonResponse(payload, safe=False)


@require_host_guest
def studio(request):
    tables = list(request.wedding_event.tables.prefetch_related("guests").order_by("number"))
    total_guests = WeddingGuest.objects.filter(event=request.wedding_event, is_active=True).count()
    seated_guests = WeddingGuest.objects.filter(event=request.wedding_event, table__isnull=False, is_active=True).count()
    entry_url = request.build_absolute_uri(reverse("wedding:home"))
    context = base_context(request, "manage") | {
        "tables": tables,
        "total_guests": total_guests,
        "seated_guests": seated_guests,
        "entry_url": entry_url,
    }
    return render(request, "wedding/studio.html", context)


@require_POST
@require_host_guest
def move_guest_table(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        guest_id = int(payload["guest_id"])
        table_id = int(payload["table_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Некорректные данные."}, status=400)

    guest = get_object_or_404(WeddingGuest, id=guest_id, event=request.wedding_event, is_active=True)
    table = get_object_or_404(ReceptionTable, id=table_id, event=request.wedding_event)
    if guest.table_id != table.id and table.guests.filter(is_active=True).count() >= table.capacity:
        return JsonResponse({"ok": False, "error": "За этим столом нет свободных мест."}, status=400)

    guest.table = table
    guest.save(update_fields=["table"])

    seat = TableSeat.objects.filter(event=request.wedding_event, guest=guest).first()
    if seat:
        seat.table = table
        seat.seat_number = next_table_seat_number(table)
        seat.save(update_fields=["table", "seat_number"])
    else:
        TableSeat.objects.create(
            event=request.wedding_event,
            table=table,
            guest=guest,
            seat_number=next_table_seat_number(table),
        )

    tables = request.wedding_event.tables.prefetch_related("guests").order_by("number")
    counts = {str(item.id): item.guests.filter(is_active=True).count() for item in tables}
    return JsonResponse({"ok": True, "guest_id": guest.id, "table_id": table.id, "counts": counts})


@require_guest
def drive_media(request, file_name):
    if not settings.USE_GOOGLE_DRIVE_MEDIA:
        raise Http404()

    file_id = Path(file_name).name.split(".", 1)[0]
    storage = GoogleDriveStorage()
    metadata = storage.get_file_metadata(file_id)
    mime_type = metadata.get("mimeType") or "application/octet-stream"
    size = int(metadata.get("size") or 0)
    headers = {}
    status = 200

    byte_range = parse_byte_range(request.headers.get("Range"), size) if size else None
    if byte_range:
        start, end = byte_range
        headers["Range"] = f"bytes={start}-{end}"
        status = 206
    else:
        start, end = 0, max(size - 1, 0)

    drive_response, content = storage.read_file(file_id, headers=headers)
    if int(drive_response.status) >= 400:
        raise Http404()

    response = HttpResponse(content, content_type=mime_type, status=status)
    response["Accept-Ranges"] = "bytes"
    if size:
        response["Content-Length"] = str(len(content))
        if status == 206:
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
    return response


@require_guest
def download_media_post(request, post_id):
    post = get_object_or_404(
        MediaPost,
        id=post_id,
        event=request.wedding_event,
        status=MediaPost.Status.APPROVED,
    )
    filename = filename_for_post(post)

    if post.file and post.file.name.startswith("gdrive/"):
        file_id = Path(post.file.name).name.split(".", 1)[0]
        storage = GoogleDriveStorage()
        metadata = storage.get_file_metadata(file_id)
        drive_response, content = storage.read_file(file_id)
        if int(drive_response.status) >= 400:
            raise Http404()

        response = HttpResponse(content, content_type=metadata.get("mimeType") or "application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = str(len(content))
        return response

    if post.file:
        return FileResponse(post.file.open("rb"), as_attachment=True, filename=filename)

    return redirect(post.external_url)


@require_host_guest
def drive_check(request):
    data = {
        "use_google_drive_media": settings.USE_GOOGLE_DRIVE_MEDIA,
        "has_token_json": bool(settings.GOOGLE_DRIVE_TOKEN_JSON),
        "token_json_length": len(settings.GOOGLE_DRIVE_TOKEN_JSON),
        "token_file_exists": Path(settings.GOOGLE_DRIVE_TOKEN_FILE).exists(),
        "folder_id": settings.GOOGLE_DRIVE_FOLDER_ID,
    }

    if settings.GOOGLE_DRIVE_TOKEN_JSON:
        try:
            token_data = json.loads(settings.GOOGLE_DRIVE_TOKEN_JSON)
            data["token_json_valid"] = True
            data["token_has_refresh_token"] = bool(token_data.get("refresh_token"))
            data["token_client_id_tail"] = (token_data.get("client_id") or "")[-12:]
            data["token_scopes"] = token_data.get("scopes", [])
        except json.JSONDecodeError as error:
            data["token_json_valid"] = False
            data["token_json_error"] = str(error)

    try:
        storage = GoogleDriveStorage()
        service = storage._get_service()
        about = service.about().get(fields="user").execute(num_retries=1)
        folder = service.files().get(
            fileId=settings.GOOGLE_DRIVE_FOLDER_ID,
            fields="id,name,mimeType",
            supportsAllDrives=settings.GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES,
        ).execute(num_retries=1)
        data["google_ok"] = True
        data["google_user"] = about.get("user", {}).get("emailAddress")
        data["folder"] = folder
    except Exception as error:
        data["google_ok"] = False
        data["error_type"] = error.__class__.__name__
        data["error"] = str(error)[:1000]

    return JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 2})


@require_guest
def album(request):
    sort = request.GET.get("sort", "feed")
    posts = (
        MediaPost.objects.filter(event=request.wedding_event, status=MediaPost.Status.APPROVED)
        .select_related("author")
        .prefetch_related("comments__guest")
        .annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count("comments", filter=Q(comments__status=MediaComment.Status.VISIBLE), distinct=True),
        )
    )
    if sort == "popular":
        posts = posts.order_by("-likes_count", "-created_at")
    else:
        posts = posts.order_by("-created_at")

    liked_ids = set(MediaLike.objects.filter(guest=request.wedding_guest, post__in=posts).values_list("post_id", flat=True))
    context = base_context(request, "album") | {
        "posts": posts,
        "sort": sort,
        "liked_ids": liked_ids,
        "comment_form": CommentForm(),
    }
    return render(request, "wedding/album.html", context)


@require_guest
def authors(request):
    query = request.GET.get("q", "").strip()
    guests = WeddingGuest.objects.filter(event=request.wedding_event, is_active=True).annotate(
        posts_count=Count("media_posts", filter=Q(media_posts__status=MediaPost.Status.APPROVED), distinct=True)
    )
    if query:
        guests = guests.filter(Q(nickname__icontains=query) | Q(display_name__icontains=query))
    guests = guests.order_by("-posts_count", "nickname")

    context = base_context(request, "authors") | {"authors": guests, "query": query}
    return render(request, "wedding/authors.html", context)


@require_guest
def author_detail(request, guest_id):
    author = get_object_or_404(WeddingGuest, id=guest_id, event=request.wedding_event, is_active=True)
    posts = MediaPost.objects.filter(event=request.wedding_event, author=author, status=MediaPost.Status.APPROVED).order_by("-created_at")
    context = base_context(request, "authors") | {"author": author, "posts": posts}
    return render(request, "wedding/author_detail.html", context)


@require_guest
def upload(request):
    can_upload = request.wedding_guest.can_upload()
    form = MediaUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not can_upload:
            messages.error(request, "Сейчас архивный режим. Доступны просмотр и лайки.")
        elif form.is_valid():
            post = form.save(commit=False)
            post.event = request.wedding_event
            post.author = request.wedding_guest
            post.status = MediaPost.Status.APPROVED
            try:
                post.save()
            except Exception as error:
                message = "Не получилось загрузить файл в Google Drive. Проверьте токен и попробуйте еще раз."
                if is_timeout_error(error):
                    message = "Google Drive долго не отвечает. Попробуйте еще раз или загрузите файл меньшего размера."
                messages.error(
                    request,
                    message,
                )
                return redirect("wedding:upload")
            messages.success(request, "Момент добавлен в живую ленту.")
            return redirect("wedding:album")

    latest_request = UploadAccessRequest.objects.filter(event=request.wedding_event, guest=request.wedding_guest).first()
    pending_request = (
        latest_request
        if latest_request and latest_request.status == UploadAccessRequest.Status.PENDING
        else None
    )
    context = base_context(request, "upload") | {
        "form": form,
        "request_form": UploadAccessRequestForm(),
        "latest_request": latest_request,
        "pending_request": pending_request,
    }
    return render(request, "wedding/upload.html", context)


@require_POST
@require_guest
def request_upload_access(request):
    if request.wedding_guest.can_upload():
        messages.info(request, "У вас уже есть доступ к созданию контента.")
        return redirect("wedding:upload")

    existing = UploadAccessRequest.objects.filter(
        event=request.wedding_event,
        guest=request.wedding_guest,
        status=UploadAccessRequest.Status.PENDING,
    ).first()
    if existing:
        messages.info(request, "Заявка уже отправлена. Ожидайте решения админа.")
        return redirect("wedding:upload")

    form = UploadAccessRequestForm(request.POST)
    if form.is_valid():
        upload_request = form.save(commit=False)
        upload_request.event = request.wedding_event
        upload_request.guest = request.wedding_guest
        upload_request.save()
        messages.success(request, "Заявка отправлена админу.")
    else:
        messages.error(request, "Не получилось отправить заявку. Проверьте текст и попробуйте снова.")
    return redirect("wedding:upload")


@require_guest
def account(request):
    posts = MediaPost.objects.filter(event=request.wedding_event, author=request.wedding_guest, status=MediaPost.Status.APPROVED).order_by("-created_at")
    context = base_context(request, "account") | {"posts": posts}
    return render(request, "wedding/account.html", context)


@require_host_guest
def manage(request):
    pending_requests = (
        UploadAccessRequest.objects.filter(event=request.wedding_event, status=UploadAccessRequest.Status.PENDING)
        .select_related("guest")
        .order_by("created_at")
    )
    recent_requests = (
        UploadAccessRequest.objects.filter(event=request.wedding_event)
        .exclude(status=UploadAccessRequest.Status.PENDING)
        .select_related("guest")
        .order_by("-reviewed_at", "-created_at")[:8]
    )
    authors = WeddingGuest.objects.filter(
        event=request.wedding_event,
        upload_override=WeddingGuest.UploadOverride.ALLOW,
        is_active=True,
    ).order_by("nickname")
    media_posts = (
        MediaPost.objects.filter(event=request.wedding_event, status=MediaPost.Status.APPROVED)
        .select_related("author")
        .order_by("-created_at")[:12]
    )
    context = base_context(request, "manage") | {
        "pending_requests": pending_requests,
        "recent_requests": recent_requests,
        "authors": authors,
        "guest_form": AddGuestToTableForm(event=request.wedding_event),
        "media_posts": media_posts,
    }
    return render(request, "wedding/manage.html", context)


@require_POST
@require_host_guest
def add_guest_to_table(request):
    form = AddGuestToTableForm(request.POST, event=request.wedding_event)
    if not form.is_valid():
        messages.error(request, "Не получилось добавить гостя. Проверьте имя и стол.")
        return redirect(request.META.get("HTTP_REFERER") or reverse("wedding:manage"))

    display_name = form.cleaned_data["display_name"].strip()
    table = form.cleaned_data["table"]
    guest = next(
        (
            candidate
            for candidate in WeddingGuest.objects.filter(
                event=request.wedding_event,
                display_name__iexact=display_name,
            )
            if not candidate.has_login_access
        ),
        None,
    )
    created = guest is None

    if created:
        guest = WeddingGuest(
            event=request.wedding_event,
            nickname=make_table_guest_nickname(request.wedding_event),
            upload_override=WeddingGuest.UploadOverride.DENY,
        )
        guest.set_unusable_password()

    guest.display_name = display_name
    guest.table = table
    guest.is_active = True
    guest.save()

    seat = TableSeat.objects.filter(event=request.wedding_event, guest=guest).first()
    if seat:
        seat_table_changed = seat.table_id != table.id
        seat.table = table
        if seat_table_changed:
            seat.seat_number = next_table_seat_number(table)
            seat.save(update_fields=["table", "seat_number"])
        else:
            seat.save(update_fields=["table"])
    else:
        TableSeat.objects.create(
            event=request.wedding_event,
            table=table,
            guest=guest,
            seat_number=next_table_seat_number(table),
        )

    action = "добавлен" if created else "обновлен"
    messages.success(request, f"Гость {display_name} {action} за столом {table.name}.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("wedding:manage"))


@require_POST
@require_host_guest
def remove_guest_from_table(request, guest_id):
    guest = get_object_or_404(
        WeddingGuest.objects.select_related("table"),
        id=guest_id,
        event=request.wedding_event,
        is_active=True,
    )
    display_name = guest.display_name or guest.nickname
    table_name = guest.table.name if guest.table else "стола"

    TableSeat.objects.filter(event=request.wedding_event, guest=guest).delete()

    if guest.has_login_access:
        guest.table = None
        guest.save(update_fields=["table"])
    else:
        guest.delete()

    messages.success(request, f"Гость {display_name} удален со стола {table_name}.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("wedding:home"))


@require_POST
@require_host_guest
def approve_upload_access(request, request_id):
    upload_request = get_object_or_404(
        UploadAccessRequest,
        id=request_id,
        event=request.wedding_event,
        status=UploadAccessRequest.Status.PENDING,
    )
    upload_request.admin_note = f"Одобрено гостем-админом @{request.wedding_guest.nickname}"
    upload_request.save(update_fields=["admin_note", "updated_at"])
    upload_request.approve()
    messages.success(request, f"Доступ для @{upload_request.guest.nickname} открыт.")
    return redirect("wedding:manage")


@require_POST
@require_host_guest
def reject_upload_access(request, request_id):
    upload_request = get_object_or_404(
        UploadAccessRequest,
        id=request_id,
        event=request.wedding_event,
        status=UploadAccessRequest.Status.PENDING,
    )
    upload_request.admin_note = f"Отклонено гостем-админом @{request.wedding_guest.nickname}"
    upload_request.save(update_fields=["admin_note", "updated_at"])
    upload_request.reject()
    messages.success(request, f"Заявка @{upload_request.guest.nickname} отклонена.")
    return redirect("wedding:manage")


@require_POST
@require_host_guest
def delete_media_post(request, post_id):
    post = get_object_or_404(
        MediaPost,
        id=post_id,
        event=request.wedding_event,
        status=MediaPost.Status.APPROVED,
    )
    post.status = MediaPost.Status.HIDDEN
    post.save(update_fields=["status", "updated_at"])
    messages.success(request, "Медиа удалено из альбома.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("wedding:manage"))


@require_POST
@require_guest
def toggle_like(request, post_id):
    post = get_object_or_404(MediaPost, id=post_id, event=request.wedding_event, status=MediaPost.Status.APPROVED)
    like, created = MediaLike.objects.get_or_create(post=post, guest=request.wedding_guest)
    if not created:
        like.delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "liked": created,
                "likes_count": MediaLike.objects.filter(post=post).count(),
            }
        )
    return redirect(request.META.get("HTTP_REFERER") or reverse("wedding:album"))


@require_POST
@require_guest
def add_comment(request, post_id):
    post = get_object_or_404(MediaPost, id=post_id, event=request.wedding_event, status=MediaPost.Status.APPROVED)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.guest = request.wedding_guest
        comment.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "ok": True,
                    "comments_count": MediaComment.objects.filter(post=post, status=MediaComment.Status.VISIBLE).count(),
                    "nickname": request.wedding_guest.nickname,
                    "body": comment.body,
                }
            )
    elif request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": False, "error": "Комментарий пустой."}, status=400)
    return redirect(request.META.get("HTTP_REFERER") or reverse("wedding:album"))

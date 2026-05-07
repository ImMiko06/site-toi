from django.urls import path

from . import views


app_name = "wedding"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.gatekeeper, name="gatekeeper"),
    path("logout/", views.logout_view, name="logout"),
    path("album/", views.album, name="album"),
    path("authors/", views.authors, name="authors"),
    path("authors/<int:guest_id>/", views.author_detail, name="author_detail"),
    path("upload/", views.upload, name="upload"),
    path("studio/", views.studio, name="studio"),
    path("drive-media/<path:file_name>", views.drive_media, name="drive_media"),
    path("upload/request-access/", views.request_upload_access, name="request_upload_access"),
    path("account/", views.account, name="account"),
    path("manage/", views.manage, name="manage"),
    path("manage/guests/add/", views.add_guest_to_table, name="add_guest_to_table"),
    path("manage/guests/<int:guest_id>/remove/", views.remove_guest_from_table, name="remove_guest_from_table"),
    path("manage/upload-requests/<int:request_id>/approve/", views.approve_upload_access, name="approve_upload_access"),
    path("manage/upload-requests/<int:request_id>/reject/", views.reject_upload_access, name="reject_upload_access"),
    path("api/seating/move/", views.move_guest_table, name="move_guest_table"),
    path("api/tables/", views.tables_api, name="tables_api"),
    path("posts/<int:post_id>/delete/", views.delete_media_post, name="delete_media_post"),
    path("posts/<int:post_id>/like/", views.toggle_like, name="toggle_like"),
    path("posts/<int:post_id>/comment/", views.add_comment, name="add_comment"),
]

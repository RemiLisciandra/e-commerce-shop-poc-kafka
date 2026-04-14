"""Tests for admin items CRUD (/admin/items/*)."""
import os
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestAdminItemsList:
    def test_list_requires_login(self, client):
        r = client.get("/admin/items", follow_redirects=False)
        assert r.status_code == 302
        assert "/admin/login" in r.headers["location"]

    def test_list_items(self, auth_admin_client, make_item, db):
        make_item(title="Article A")
        make_item(title="Article B")
        r = auth_admin_client.get("/admin/items")
        assert r.status_code == 200
        assert "Article A" in r.text
        assert "Article B" in r.text


class TestAdminItemCreate:
    def test_create_form_requires_login(self, client):
        r = client.get("/admin/items/create", follow_redirects=False)
        assert r.status_code == 302

    def test_create_form(self, auth_admin_client):
        r = auth_admin_client.get("/admin/items/create")
        assert r.status_code == 200

    def test_create_item(self, auth_admin_client):
        r = auth_admin_client.post(
            "/admin/items/create",
            data={"title": "New Item", "description": "Desc", "price_ht": "10.0",
                  "tva_rate": "20.0", "quantity": "5"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_create_item_with_image(self, auth_admin_client):
        r = auth_admin_client.post(
            "/admin/items/create",
            data={"title": "With Img", "description": "", "price_ht": "10.0",
                  "tva_rate": "20.0", "quantity": "5"},
            files={"image": ("test.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_create_item_requires_login(self, client):
        r = client.post(
            "/admin/items/create",
            data={"title": "X", "price_ht": "1.0", "tva_rate": "20.0", "quantity": "1"},
            follow_redirects=False,
        )
        assert r.status_code == 302


class TestAdminItemEdit:
    def test_edit_form_requires_login(self, client):
        r = client.get("/admin/items/1/edit", follow_redirects=False)
        assert r.status_code == 302

    def test_edit_post_requires_login(self, client):
        r = client.post(
            "/admin/items/1/edit",
            data={"title": "X", "description": "", "price_ht": "5.0",
                  "tva_rate": "20.0", "quantity": "1", "remove_image": ""},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_edit_form(self, auth_admin_client, make_item, db):
        item = make_item(title="EditMe")
        r = auth_admin_client.get(f"/admin/items/{item.id}/edit")
        assert r.status_code == 200
        assert "EditMe" in r.text

    def test_edit_form_nonexistent(self, auth_admin_client):
        r = auth_admin_client.get("/admin/items/9999/edit", follow_redirects=False)
        assert r.status_code == 302

    def test_edit_item(self, auth_admin_client, make_item, db):
        item = make_item(title="Old Title")
        r = auth_admin_client.post(
            f"/admin/items/{item.id}/edit",
            data={"title": "New Title", "description": "", "price_ht": "15.0",
                  "tva_rate": "20.0", "quantity": "10", "remove_image": ""},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_edit_nonexistent_item(self, auth_admin_client):
        r = auth_admin_client.post(
            "/admin/items/9999/edit",
            data={"title": "X", "description": "", "price_ht": "5.0",
                  "tva_rate": "20.0", "quantity": "1", "remove_image": ""},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_edit_remove_image(self, auth_admin_client, make_item, db):
        item = make_item(title="HasImg", image_url="/uploads/old.jpg")
        with patch("routers.admin.items._delete_upload") as mock_del:
            r = auth_admin_client.post(
                f"/admin/items/{item.id}/edit",
                data={"title": "HasImg", "description": "", "price_ht": "10.0",
                      "tva_rate": "20.0", "quantity": "5", "remove_image": "1"},
                follow_redirects=False,
            )
            assert r.status_code == 302
            mock_del.assert_called()

    def test_edit_replace_image(self, auth_admin_client, make_item, db):
        item = make_item(title="ReplImg", image_url="/uploads/old.jpg")
        with patch("routers.admin.items._delete_upload") as mock_del:
            r = auth_admin_client.post(
                f"/admin/items/{item.id}/edit",
                data={"title": "ReplImg", "description": "", "price_ht": "10.0",
                      "tva_rate": "20.0", "quantity": "5", "remove_image": ""},
                files={"image": ("new.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
                follow_redirects=False,
            )
            assert r.status_code == 302


class TestAdminItemDelete:
    def test_delete_requires_login(self, client):
        r = client.post("/admin/items/1/delete", follow_redirects=False)
        assert r.status_code == 302

    def test_delete_item(self, auth_admin_client, make_item, db):
        item = make_item(title="ToDelete")
        with patch("routers.admin.items._delete_upload"):
            r = auth_admin_client.post(
                f"/admin/items/{item.id}/delete", follow_redirects=False,
            )
        assert r.status_code == 302

    def test_delete_nonexistent(self, auth_admin_client):
        r = auth_admin_client.post("/admin/items/9999/delete", follow_redirects=False)
        assert r.status_code == 302


class TestUploadHelpers:
    def test_save_upload_valid(self):
        from routers.admin.items import _save_upload
        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"
        mock_file.file.read.return_value = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        with patch("builtins.open", MagicMock()):
            with patch("os.makedirs"):
                result = _save_upload(mock_file)
        assert result is not None
        assert result.startswith("/uploads/")
        assert result.endswith(".jpg")

    def test_save_upload_no_file(self):
        from routers.admin.items import _save_upload
        assert _save_upload(None) is None

    def test_save_upload_no_filename(self):
        from routers.admin.items import _save_upload
        mock_file = MagicMock()
        mock_file.filename = ""
        assert _save_upload(mock_file) is None

    def test_save_upload_invalid_extension(self):
        from routers.admin.items import _save_upload
        mock_file = MagicMock()
        mock_file.filename = "data.exe"
        assert _save_upload(mock_file) is None

    def test_delete_upload_valid(self):
        from routers.admin.items import _delete_upload
        with patch("os.remove") as mock_rm:
            _delete_upload("/uploads/abc.jpg")
            mock_rm.assert_called_once_with("/app/uploads/abc.jpg")

    def test_delete_upload_none(self):
        from routers.admin.items import _delete_upload
        with patch("os.remove") as mock_rm:
            _delete_upload(None)
            mock_rm.assert_not_called()

    def test_delete_upload_non_uploads_path(self):
        from routers.admin.items import _delete_upload
        with patch("os.remove") as mock_rm:
            _delete_upload("/etc/passwd")
            mock_rm.assert_not_called()

    def test_delete_upload_oserror(self):
        from routers.admin.items import _delete_upload
        with patch("os.remove", side_effect=OSError("no file")):
            _delete_upload("/uploads/missing.jpg")  # should not raise

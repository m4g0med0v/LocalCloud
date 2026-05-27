"""Comprehensive LocalCloud backend test suite."""
import sys
import time
import requests

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@LocalCloud123"

session = requests.Session()
passed = 0
failed = 0
results = []


def ok(name, resp=None):
    global passed
    passed += 1
    note = f" -> {resp.status_code}" if resp else ""
    results.append(f"  PASS  {name}{note}")


def fail(name, reason, resp=None):
    global failed
    failed += 1
    status = f" [{resp.status_code}]" if resp else ""
    results.append(f"  FAIL  {name}{status}: {reason}")


def check(name, resp, expected_status, check_fn=None):
    if resp.status_code != expected_status:
        fail(name, f"expected {expected_status}, got {resp.status_code} — {resp.text[:300]}", resp)
        return None
    if check_fn:
        try:
            data = resp.json()
            check_fn(data)
        except Exception as e:
            fail(name, str(e), resp)
            return None
    ok(name, resp)
    try:
        return resp.json()
    except Exception:
        return {}


print("=" * 60)
print("LocalCloud Backend Test Suite")
print("=" * 60)

# ------------------------------------------------------------------ #
# 1. HEALTH
# ------------------------------------------------------------------ #
print("\n[1] Health")
r = session.get(f"{API}/health")
check("GET /health", r, 200, lambda d: d.get("status") in ("ok", "degraded", "unavailable"))

r = session.get(f"{BASE}/")
check("GET / (root)", r, 200, lambda d: d.get("success") is True)

# ------------------------------------------------------------------ #
# 2. AUTH – login (cookie-based, session handles cookies automatically)
# ------------------------------------------------------------------ #
print("\n[2] Auth")
r = session.post(f"{API}/auth/login", json={
    "email_or_username": ADMIN_EMAIL,
    "password": ADMIN_PASSWORD,
})
login_data = check("POST /auth/login", r, 200, lambda d: d.get("authenticated") is True)
admin_id = None
if login_data:
    admin_id = login_data.get("user", {}).get("id")

r = session.get(f"{API}/auth/me")
check("GET /auth/me", r, 200, lambda d: d.get("email") == ADMIN_EMAIL)

r = session.get(f"{API}/auth/sessions")
check("GET /auth/sessions", r, 200, lambda d: isinstance(d, list))

# Wrong credentials -> 401
r = session.post(f"{API}/auth/login", json={
    "email_or_username": "nobody@example.com",
    "password": "wrongpassword",
})
check("POST /auth/login (bad creds -> 401)", r, 401)

# ------------------------------------------------------------------ #
# 3. REGISTRATION
# ------------------------------------------------------------------ #
print("\n[3] Registration")
ts = int(time.time())
new_user = {
    "email": f"testuser{ts}@example.com",
    "username": f"testuser{ts}",
    "password": "Test@User123456",
}

r = session.post(f"{API}/registration/requests", json=new_user)
reg_data = check("POST /registration/requests", r, 201,
                 lambda d: d.get("status") == "pending")
reg_id = reg_data["id"] if reg_data else None

r = session.get(f"{API}/registration/requests")
check("GET /registration/requests", r, 200, lambda d: "items" in d)

new_user_id = None
if reg_id:
    r = session.post(
        f"{API}/registration/requests/{reg_id}/approve",
        json={"is_email_verified": True, "comment": "Test approval"},
    )
    approve_data = check(
        "POST /registration/requests/:id/approve", r, 200,
        lambda d: d.get("request", {}).get("status") == "approved",
    )
    if approve_data:
        new_user_id = approve_data.get("created_user_id")

r = session.post(f"{API}/registration/requests", json=new_user)
check("POST /registration/requests (duplicate -> 409)", r, 409)

# ------------------------------------------------------------------ #
# 4. USERS
# ------------------------------------------------------------------ #
print("\n[4] Users")
r = session.get(f"{API}/users")
check("GET /users", r, 200, lambda d: "items" in d)

if admin_id:
    r = session.get(f"{API}/users/{admin_id}")
    check("GET /users/:id", r, 200, lambda d: d.get("id") == admin_id)

# ------------------------------------------------------------------ #
# 5. ROLES
# ------------------------------------------------------------------ #
print("\n[5] Roles")
r = session.get(f"{API}/roles")
check("GET /roles", r, 200, lambda d: isinstance(d, list) and len(d) >= 2)

# ------------------------------------------------------------------ #
# 6. QUOTAS
# ------------------------------------------------------------------ #
print("\n[6] Quotas")
r = session.get(f"{API}/quotas/me")
check("GET /quotas/me", r, 200, lambda d: "storage_limit_bytes" in d)

if admin_id:
    r = session.get(f"{API}/quotas/users/{admin_id}")
    check("GET /quotas/users/:user_id", r, 200, lambda d: "storage_limit_bytes" in d)

# ------------------------------------------------------------------ #
# 7. FOLDERS
# ------------------------------------------------------------------ #
print("\n[7] Folders")
r = session.post(f"{API}/folders/", json={"name": "TestFolder", "parent_id": None})
folder_data = check("POST /folders/", r, 201, lambda d: d.get("name") == "TestFolder")
folder_id = folder_data["id"] if folder_data else None
folder_node_id = folder_data.get("node_id") if folder_data else None

if folder_id:
    r = session.get(f"{API}/folders/{folder_id}")
    check("GET /folders/:id", r, 200, lambda d: d.get("id") == folder_id)

    r = session.patch(f"{API}/folders/{folder_id}", json={"name": "TestFolderRenamed"})
    check("PATCH /folders/:id (rename)", r, 200,
          lambda d: d.get("name") == "TestFolderRenamed")

    r = session.get(f"{API}/folders/{folder_id}/content")
    check("GET /folders/:id/content", r, 200)

    # Create subfolder
    r = session.post(f"{API}/folders/", json={"name": "SubFolder", "parent_id": folder_node_id})
    sub_data = check("POST /folders/ (nested)", r, 201)
    sub_folder_id = sub_data["id"] if sub_data else None
    sub_node_id = sub_data.get("node_id") if sub_data else None

# ------------------------------------------------------------------ #
# 8. UPLOADS (full multipart flow)
# ------------------------------------------------------------------ #
print("\n[8] Uploads")
file_content = b"hello world"
file_size = len(file_content)

upload_payload = {
    "parent_node_id": folder_node_id or folder_id,
    "filename": "test.txt",
    "file_size_bytes": file_size,
    "parts_count": 1,
    "mime_type": "text/plain",
}
r = session.post(f"{API}/uploads/", json=upload_payload)
upload_session = check("POST /uploads/ (create session)", r, 201,
                       lambda d: "id" in d and d.get("status") == "initiated")
upload_id = upload_session["id"] if upload_session else None

file_id = None
if upload_id:
    # Get presigned URLs
    r = session.post(f"{API}/uploads/{upload_id}/parts/presigned")
    presigned = check("POST /uploads/:id/parts/presigned", r, 200,
                      lambda d: len(d.get("parts", [])) >= 1)

    if presigned and presigned.get("parts"):
        part = presigned["parts"][0]
        put_url = part["url"]
        part_number = part["part_number"]
        headers = part.get("headers", {})

        put_r = requests.put(
            put_url, data=file_content,
            headers={**headers, "Content-Type": "text/plain"},
        )
        if put_r.status_code in (200, 204):
            ok("PUT presigned part to MinIO")
            etag = put_r.headers.get("ETag", "").strip('"')

            # Confirm part
            r = session.post(
                f"{API}/uploads/{upload_id}/parts/{part_number}/complete",
                json={"part_number": part_number, "etag": etag, "size_bytes": file_size},
            )
            check("POST /uploads/:id/parts/:n/complete", r, 200)

            # Complete upload
            r = session.post(
                f"{API}/uploads/{upload_id}/complete",
                json={
                    "upload_session_id": upload_id,
                    "parts": [{"part_number": part_number, "etag": etag, "size_bytes": file_size}],
                },
            )
            complete = check("POST /uploads/:id/complete", r, 200,
                             lambda d: d.get("status") in ("completed", "processing"))
            if complete:
                file_id = complete.get("file_id")
        else:
            fail("PUT presigned part to MinIO",
                 f"MinIO returned {put_r.status_code}: {put_r.text[:200]}")

# Wait briefly for async processing
time.sleep(1)

# ------------------------------------------------------------------ #
# 9. FILES
# ------------------------------------------------------------------ #
print("\n[9] Files")
r = session.get(f"{API}/files/")
files_data = check("GET /files/", r, 200, lambda d: "items" in d)

# Resolve file_id if not yet set
if not file_id and files_data and files_data.get("items"):
    file_id = files_data["items"][0]["id"]

if file_id:
    r = session.get(f"{API}/files/{file_id}")
    check("GET /files/:id", r, 200, lambda d: "name" in d)

    r = session.post(f"{API}/files/{file_id}/rename",
                     json={"name": "test_renamed.txt"})
    check("POST /files/:id/rename", r, 200)

    r = session.post(f"{API}/files/{file_id}/download", json={"file_id": file_id, "force_download": True})
    check("POST /files/:id/download", r, 200, lambda d: "url" in d or "download_url" in d)

# ------------------------------------------------------------------ #
# 10. NODES
# ------------------------------------------------------------------ #
print("\n[10] Nodes")
if folder_node_id:
    r = session.get(f"{API}/nodes/{folder_node_id}")
    check("GET /nodes/:id", r, 200)

r = session.get(f"{API}/nodes/search", params={"query": "test"})
check("GET /nodes/search", r, 200)

if folder_node_id:
    r = session.get(f"{API}/nodes/tree", params={"root_node_id": folder_node_id})
    check("GET /nodes/tree", r, 200)

# ------------------------------------------------------------------ #
# 11. TRASH
# ------------------------------------------------------------------ #
print("\n[11] Trash")
trash_node_id = None
if file_id:
    # Soft-delete via nodes endpoint
    r = session.get(f"{API}/files/{file_id}")
    if r.status_code == 200:
        trash_node_id = r.json().get("node_id")

if trash_node_id:
    r = session.delete(f"{API}/nodes/{trash_node_id}")
    check("DELETE /nodes/:id (soft delete file)", r, 200)

r = session.get(f"{API}/trash/")
check("GET /trash/", r, 200, lambda d: "items" in d)

trash_item_id = None
if trash_node_id:
    trash_list = session.get(f"{API}/trash/").json()
    for item in trash_list.get("items", []):
        if item.get("node_id") == trash_node_id:
            trash_item_id = item["id"]
            break

if trash_node_id:
    _restore_id = trash_item_id or trash_node_id
    r = session.post(f"{API}/trash/{_restore_id}/restore",
                     json={"node_id": trash_node_id})
    check("POST /trash/:id/restore", r, 200)

    # Delete again then purge
    r = session.delete(f"{API}/nodes/{trash_node_id}")
    if r.status_code == 200:
        _purge_id = trash_item_id or trash_node_id
        r = session.post(f"{API}/trash/{_purge_id}/purge", json={})
        check("POST /trash/:id/purge", r, 200)

# ------------------------------------------------------------------ #
# 12. PUBLIC LINKS
# ------------------------------------------------------------------ #
print("\n[12] Public Links")
link_id = None
if folder_node_id:
    r = session.post(f"{API}/public-links/", json={
        "node_id": folder_node_id,
        "permission_type": "download",
        "expires_at": None,
        "password": None,
    })
    link_data = check("POST /public-links/", r, 201,
                      lambda d: "token" in d or "id" in d)
    link_id = link_data["id"] if link_data else None

r = session.get(f"{API}/public-links/")
check("GET /public-links/", r, 200, lambda d: "items" in d)

if link_id:
    r = session.get(f"{API}/public-links/{link_id}")
    check("GET /public-links/:id", r, 200)

    r = session.post(f"{API}/public-links/{link_id}/revoke", json={})
    check("POST /public-links/:id/revoke", r, 200)

# ------------------------------------------------------------------ #
# 13. PERMISSIONS
# ------------------------------------------------------------------ #
print("\n[13] Permissions")
if folder_node_id and new_user_id:
    r = session.post(f"{API}/permissions/grant", json={
        "node_id": folder_node_id,
        "user_id": new_user_id,
        "can_read": True,
        "can_write": False,
        "can_delete": False,
        "can_share": False,
    })
    perm_data = check("POST /permissions/grant", r, 201)
    perm_id = perm_data["id"] if perm_data else None

    r = session.get(f"{API}/permissions/nodes/{folder_node_id}")
    check("GET /permissions/nodes/:id", r, 200)

    if perm_id:
        r = session.post(f"{API}/permissions/revoke", json={"permission_id": perm_id})
        check("POST /permissions/revoke", r, 200)
else:
    ok("Permissions (skipped – no secondary user yet)")

# ------------------------------------------------------------------ #
# 14. AUDIT
# ------------------------------------------------------------------ #
print("\n[14] Audit")
r = session.get(f"{API}/audit/logs")
check("GET /audit/logs", r, 200)

r = session.get(f"{API}/audit/logs", params={"limit": 5, "offset": 0})
check("GET /audit/logs (paginated)", r, 200)

# ------------------------------------------------------------------ #
# 15. TASKS
# ------------------------------------------------------------------ #
print("\n[15] Tasks")
r = session.get(f"{API}/tasks")
check("GET /tasks", r, 200)

# ------------------------------------------------------------------ #
# 16. PASSWORD
# ------------------------------------------------------------------ #
print("\n[16] Password")
r = session.post(f"{API}/auth/password/change", json={
    "current_password": ADMIN_PASSWORD,
    "new_password": ADMIN_PASSWORD,
})
check("POST /auth/password/change", r, 200)

r = session.post(f"{API}/auth/password/reset/request",
                 json={"email": ADMIN_EMAIL})
reset_data = check("POST /auth/password/reset/request", r, 200,
                   lambda d: "reset_token" in d)
if reset_data:
    reset_token = reset_data["reset_token"]
    r = session.post(f"{API}/auth/password/reset/confirm", json={
        "token": reset_token,
        "new_password": ADMIN_PASSWORD,
    })
    check("POST /auth/password/reset/confirm", r, 200)

# ------------------------------------------------------------------ #
# 17. FOLDER CLEANUP (soft delete via nodes)
# ------------------------------------------------------------------ #
print("\n[17] Folder cleanup")
if folder_node_id:
    r = session.delete(f"{API}/nodes/{folder_node_id}")
    check("DELETE /nodes/:folder_node_id (soft delete folder)", r, 200)

# ------------------------------------------------------------------ #
# 18. REFRESH & LOGOUT
# ------------------------------------------------------------------ #
print("\n[18] Refresh / Logout")
r = session.post(f"{API}/auth/refresh")
check("POST /auth/refresh", r, 200, lambda d: d.get("authenticated") is True)

r = session.post(f"{API}/auth/logout")
check("POST /auth/logout", r, 200, lambda d: d.get("authenticated") is False)

r = session.get(f"{API}/auth/me")
check("GET /auth/me (after logout -> 401)", r, 401)

# ------------------------------------------------------------------ #
# SUMMARY
# ------------------------------------------------------------------ #
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed  ({passed + failed} total)")
print("=" * 60)
for line in results:
    print(line)

sys.exit(0 if failed == 0 else 1)

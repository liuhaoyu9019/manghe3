import os
from fastapi import Depends, FastAPI, HTTPException, Header, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from PIL import Image
import io

from database import get_db, init_db
from auth import hash_password, verify_password, create_token, decode_token
from schemas import (
    RegisterRequest, LoginRequest, AuthResponse,
    Pet, PetListResponse,
    ProfileResponse, PullResponse,
    CollectionItem, CollectionResponse,
    AdminUserItem, AdminUsersResponse, AdminCountResponse,
    PetUpdateRequest, PetImageResponse,
)
from pet_data import pick_pet, DAILY_LIMIT

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "pets")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_IMAGE_SIZE = (512, 512)

app = FastAPI(title="石器时代 · 宠物图鉴盲盒", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error handlers: unify to { "error": { "code": ..., "message": ... } } ──

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    errors = exc.errors()
    first = errors[0] if errors else {}
    msg = first.get("msg", "请求参数错误")
    return JSONResponse(status_code=400, content={"error": {"code": "VALIDATION_ERROR", "message": msg}})


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    elif isinstance(detail, str):
        body = {"error": {"code": "ERROR", "message": detail}}
    else:
        body = {"error": {"code": "ERROR", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.on_event("startup")
def startup():
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ──

def get_current_user(authorization: str = Header(...)) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "未提供有效的认证信息"})
    token = authorization[7:]
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(401, detail={"code": "TOKEN_EXPIRED", "message": "登录已过期，请重新登录"})
    return user_id


def _today_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _db_pet_to_dict(row) -> dict:
    image_path = row["image_path"] if row["image_path"] else None
    image_url = f"/uploads/pets/{os.path.basename(image_path)}" if image_path else None
    return {
        "id": row["id"], "name": row["name"], "rarity": row["rarity"],
        "emoji": row["emoji"], "description": row["description"],
        "image_url": image_url,
    }


# ── Auth ──

@app.post("/api/register", response_model=AuthResponse)
def register(body: RegisterRequest):
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(409, detail={"code": "USERNAME_TAKEN", "message": "用户名已被注册"})

    pw_hash = hash_password(body.password)
    cur = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                     (body.username, pw_hash))
    db.commit()
    user_id = cur.lastrowid
    token = create_token(user_id)
    db.close()
    return {"token": token, "user": {"id": user_id, "username": body.username}}


@app.post("/api/login", response_model=AuthResponse)
def login(body: LoginRequest):
    db = get_db()
    row = db.execute("SELECT id, username, password_hash FROM users WHERE username = ?",
                     (body.username,)).fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        db.close()
        raise HTTPException(401, detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"})

    token = create_token(row["id"])
    db.close()
    return {"token": token, "user": {"id": row["id"], "username": row["username"]}}


# ── Profile ──

@app.get("/api/profile", response_model=ProfileResponse)
def profile(user_id: int = Depends(get_current_user)):
    db = get_db()
    row = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404)

    today = _today_utc()
    dp = db.execute(
        "SELECT pull_count FROM daily_pulls WHERE user_id = ? AND pull_date = ?",
        (user_id, today),
    ).fetchone()
    pulls_today = dp["pull_count"] if dp else 0
    remaining = max(0, DAILY_LIMIT - pulls_today)

    total = db.execute(
        "SELECT SUM(count) as total FROM collection WHERE user_id = ?", (user_id,)
    ).fetchone()["total"] or 0

    db.close()
    return {"username": row["username"], "daily_pulls_remaining": remaining, "total_collected": total}


# ── Pull ──

@app.post("/api/pull", response_model=PullResponse)
def pull(user_id: int = Depends(get_current_user)):
    db = get_db()
    today = _today_utc()

    # Check / update daily limit
    dp = db.execute(
        "SELECT pull_count FROM daily_pulls WHERE user_id = ? AND pull_date = ?",
        (user_id, today),
    ).fetchone()

    pulls_today = dp["pull_count"] if dp else 0
    if pulls_today >= DAILY_LIMIT:
        db.close()
        raise HTTPException(429, detail={"code": "DAILY_LIMIT", "message": "今日抽卡次数已用完"})

    if dp:
        db.execute("UPDATE daily_pulls SET pull_count = pull_count + 1 WHERE user_id = ? AND pull_date = ?",
                   (user_id, today))
    else:
        db.execute("INSERT INTO daily_pulls (user_id, pull_date, pull_count) VALUES (?, ?, 1)",
                   (user_id, today))

    # Fetch all pets from DB for weighted random selection
    pet_rows = db.execute("SELECT * FROM pets").fetchall()
    pets_dicts = [dict(r) for r in pet_rows]
    pet = pick_pet(pets_dicts)

    # Upsert collection
    existing = db.execute(
        "SELECT count FROM collection WHERE user_id = ? AND pet_id = ?",
        (user_id, pet["id"]),
    ).fetchone()

    if existing:
        db.execute("UPDATE collection SET count = count + 1 WHERE user_id = ? AND pet_id = ?",
                   (user_id, pet["id"]))
        new_count = existing["count"] + 1
    else:
        db.execute("INSERT INTO collection (user_id, pet_id, count) VALUES (?, ?, 1)",
                   (user_id, pet["id"]))
        new_count = 1

    db.commit()
    db.close()

    return {"pet": _db_pet_to_dict(pet), "count": new_count}


# ── Pets ──

@app.get("/api/pets", response_model=PetListResponse)
def list_pets():
    db = get_db()
    rows = db.execute("SELECT * FROM pets ORDER BY id").fetchall()
    db.close()
    return {"pets": [_db_pet_to_dict(r) for r in rows]}


# ── Collection ──

@app.get("/api/collection", response_model=CollectionResponse)
def get_collection(user_id: int = Depends(get_current_user)):
    db = get_db()
    rows = db.execute("""
        SELECT c.pet_id, c.count, p.name, p.rarity, p.emoji, p.image_path
        FROM collection c
        JOIN pets p ON p.id = c.pet_id
        WHERE c.user_id = ?
        ORDER BY c.first_obtained_at DESC
    """, (user_id,)).fetchall()
    db.close()

    items = []
    for row in rows:
        image_url = f"/uploads/pets/{os.path.basename(row['image_path'])}" if row["image_path"] else None
        items.append(CollectionItem(
            pet_id=row["pet_id"],
            name=row["name"],
            rarity=row["rarity"],
            emoji=row["emoji"],
            count=row["count"],
            image_url=image_url,
        ))
    return {"collection": items}


# ── Admin ──

@app.get("/api/admin/users-count", response_model=AdminCountResponse)
def admin_users_count():
    db = get_db()
    row = db.execute("SELECT COUNT(*) as count FROM users").fetchone()
    db.close()
    return {"count": row["count"]}


@app.get("/api/admin/today-pulls", response_model=AdminCountResponse)
def admin_today_pulls():
    db = get_db()
    today = _today_utc()
    row = db.execute(
        "SELECT COALESCE(SUM(pull_count), 0) as count FROM daily_pulls WHERE pull_date = ?",
        (today,),
    ).fetchone()
    db.close()
    return {"count": row["count"]}


@app.get("/api/admin/users", response_model=AdminUsersResponse)
def admin_users():
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.username, u.created_at,
               COALESCE((SELECT SUM(c.count) FROM collection c WHERE c.user_id = u.id), 0) as collected
        FROM users u
        ORDER BY u.created_at DESC
    """).fetchall()
    db.close()
    return {"users": [AdminUserItem(id=r["id"], username=r["username"],
                                    created_at=r["created_at"], collected=r["collected"]) for r in rows]}


# ── Admin Pet CRUD ──

@app.put("/api/admin/pets/{pet_id}", response_model=Pet)
def admin_update_pet(pet_id: int, body: PetUpdateRequest):
    db = get_db()
    existing = db.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    if not existing:
        db.close()
        raise HTTPException(404, detail={"code": "PET_NOT_FOUND", "message": "宠物不存在"})

    db.execute(
        "UPDATE pets SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (body.name, pet_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    db.close()
    return _db_pet_to_dict(row)


@app.post("/api/admin/pets/{pet_id}/image", response_model=PetImageResponse)
def admin_upload_pet_image(pet_id: int, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail={
            "code": "INVALID_IMAGE_TYPE",
            "message": f"不支持的图片格式: {ext}，支持: png/jpg/jpeg/gif/webp",
        })

    db = get_db()
    existing = db.execute("SELECT id FROM pets WHERE id = ?", (pet_id,)).fetchone()
    if not existing:
        db.close()
        raise HTTPException(404, detail={"code": "PET_NOT_FOUND", "message": "宠物不存在"})

    contents = file.file.read()
    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
    except Exception:
        db.close()
        raise HTTPException(400, detail={"code": "INVALID_IMAGE", "message": "无法识别该图片文件"})

    img = Image.open(io.BytesIO(contents))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    img.thumbnail(MAX_IMAGE_SIZE, Image.LANCZOS)

    output_filename = f"{pet_id}.webp"
    output_path = os.path.join(UPLOAD_DIR, output_filename)

    # Clean up old files for this pet
    for old_file in os.listdir(UPLOAD_DIR):
        if old_file.startswith(f"{pet_id}."):
            os.remove(os.path.join(UPLOAD_DIR, old_file))

    img.save(output_path, "WEBP", quality=85)
    db.execute(
        "UPDATE pets SET image_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (output_path, pet_id),
    )
    db.commit()
    db.close()

    return PetImageResponse(id=pet_id, image_url=f"/uploads/pets/{output_filename}")


@app.get("/api/admin/pets/{pet_id}", response_model=Pet)
def admin_get_pet(pet_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404)
    return _db_pet_to_dict(row)


# ── Image Serving ──

@app.get("/uploads/pets/{filename}")
def serve_pet_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404)
    return FileResponse(file_path, media_type="image/webp")


# ── Startup ──

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

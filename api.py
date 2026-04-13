"""
Toolregister REST API  –  Flask + SQLAlchemy + SQLite

Extra media-endpoints (per tool):
  GET    /tools/<id>/media                → alle media-items
  POST   /tools/<id>/media/upload         → afbeelding uploaden (multipart)
  POST   /tools/<id>/media/url            → URL toevoegen + screenshot maken
  DELETE /tools/<id>/media/<mid>          → media-item verwijderen
  PUT    /tools/<id>/media/<mid>/cover    → als voorblad instellen

Auth endpoints:
  POST   /auth/login                      → inloggen
  POST   /auth/logout                     → uitloggen
  GET    /auth/me                         → huidige gebruiker

Users endpoints (admin only):
  GET    /users                           → lijst alle gebruikers
  POST   /users                           → nieuwe gebruiker aanmaken
  PUT    /users/<id>                      → gebruiker bijwerken
  DELETE /users/<id>                      → gebruiker verwijderen
"""
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, abort, send_file, send_from_directory, session
from werkzeug.security import generate_password_hash
from models import init_db, get_session, Tool, Project, Probleem, MediaItem, User

app = Flask(__name__)
app.secret_key = "toolregister-geheim-2024"
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB (video's)

MEDIA_DIR = Path(__file__).parent / "static" / "media"
VIDEO_DIR = MEDIA_DIR / "videos"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"}
ALLOWED_EXT = IMAGE_EXT | VIDEO_EXT

import re, urllib.request, subprocess


# ── Migraties ─────────────────────────────────────────────────────────────────

def run_migrations():
    """Voeg ontbrekende kolommen toe via sqlite3 direct (veilig om meerdere keren aan te roepen)."""
    db_path = Path(__file__).parent / "toolregister.db"
    if not db_path.exists():
        return  # DB bestaat nog niet, init_db doet het wel

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    migrations = [
        ("tools",       "tool_url",      "TEXT"),
        ("tools",       "beheerder_id",  "INTEGER"),
        ("tools",       "tijdbalk_start","INTEGER"),
        ("tools",       "tijdbalk_eind", "INTEGER"),
        ("projecten",   "beheerder_id",  "INTEGER"),
        ("problemen",   "beheerder_id",  "INTEGER"),
        ("media_items", "media_type",    "TEXT"),
        ("media_items", "video_url",     "TEXT"),
    ]

    for tabel, kolom, kolom_type in migrations:
        # Controleer of tabel bestaat
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabel,))
        if not cur.fetchone():
            continue
        # Controleer of kolom al bestaat
        cur.execute(f"PRAGMA table_info({tabel})")
        kolommen = [row[1] for row in cur.fetchall()]
        if kolom not in kolommen:
            try:
                cur.execute(f"ALTER TABLE {tabel} ADD COLUMN {kolom} {kolom_type}")
                print(f"[migratie] {tabel}.{kolom} toegevoegd.")
            except Exception as e:
                print(f"[migratie] Fout bij {tabel}.{kolom}: {e}")

    conn.commit()
    conn.close()


# ── Video / afbeelding helpers ────────────────────────────────────────────────

def _youtube_id(url: str):
    """Extraheer YouTube video-ID uit diverse URL-formaten."""
    for pattern in [
        r"youtube\.com/watch\?(?:.*&)?v=([^&]+)",
        r"youtu\.be/([^?&]+)",
        r"youtube\.com/embed/([^?&]+)",
        r"youtube\.com/shorts/([^?&]+)",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _vimeo_id(url: str):
    m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
    return m.group(1) if m else None


def _download_thumbnail(thumb_url: str, output_path: Path) -> bool:
    try:
        req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            output_path.write_bytes(resp.read())
        return output_path.stat().st_size > 2000
    except Exception as e:
        print(f"[thumb] {e}")
        return False


def _resize(path: Path):
    try:
        from PIL import Image
        img = Image.open(path)
        img.thumbnail((900, 563))
        img.save(path, optimize=True)
    except Exception:
        pass


def extract_video_still(video_path: Path, output_path: Path) -> bool:
    """Gebruik ffmpeg om een frame uit een video te halen."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", str(video_path), "-ss", "00:00:01",
             "-vframes", "1", "-vf", "scale=900:-1", str(output_path), "-y"],
            capture_output=True, timeout=30,
        )
        ok = output_path.exists() and output_path.stat().st_size > 1000
        if ok:
            _resize(output_path)
        return ok
    except Exception as e:
        print(f"[ffmpeg] {e}")
        return False


def capture_screenshot(url: str, output_path: Path) -> bool:
    """Schermafdruk via Playwright."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(output_path),
                            clip={"x": 0, "y": 0, "width": 1280, "height": 800})
            browser.close()
    except Exception as e:
        print(f"[screenshot] {e}")
        return False
    _resize(output_path)
    return True


def process_url(url: str, still_path: Path) -> dict:
    """
    Verwerk een URL: detecteer YouTube / Vimeo / overige.
    Retourneert dict met: media_type, video_url, ok.
    """
    yt_id = _youtube_id(url)
    if yt_id:
        thumb_ok = _download_thumbnail(
            f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg", still_path
        )
        if not thumb_ok:
            _download_thumbnail(
                f"https://img.youtube.com/vi/{yt_id}/mqdefault.jpg", still_path
            )
        _resize(still_path)
        return {"media_type": "video",
                "video_url": f"https://www.youtube.com/embed/{yt_id}?autoplay=1",
                "ok": still_path.exists()}

    vm_id = _vimeo_id(url)
    if vm_id:
        try:
            req = urllib.request.Request(
                f"https://vimeo.com/api/v2/video/{vm_id}.json",
                headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                import json
                data = json.loads(resp.read())[0]
            thumb_ok = _download_thumbnail(data.get("thumbnail_large", ""), still_path)
        except Exception:
            thumb_ok = False
        return {"media_type": "video",
                "video_url": f"https://player.vimeo.com/video/{vm_id}?autoplay=1",
                "ok": thumb_ok}

    # Overige URL → screenshot
    ok = capture_screenshot(url, still_path)
    return {"media_type": "image", "video_url": None, "ok": ok}


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

def now():
    return datetime.utcnow()


def get_or_404(session, model, id_):
    obj = session.get(model, id_)
    if obj is None:
        abort(404, description=f"{model.__tablename__} met id {id_} niet gevonden.")
    return obj


def apply_fields(obj, data, fields):
    for f in fields:
        if f in data:
            setattr(obj, f, data[f])


def _first_cover(tool):
    """Zorg dat altijd precies één item cover is als er media zijn."""
    items = tool.media_items
    if not items:
        return
    if not any(m.is_cover for m in items):
        items[0].is_cover = True


# ── Auth helpers ───────────────────────────────────────────────────────────────

def get_current_user():
    """Lees session['user_id'] en retourneer User object of None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_session() as s:
        return s.get(User, user_id)


def require_login(f):
    """Decorator: retourneert 401 JSON als niet ingelogd."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"fout": "Niet ingelogd."}), 401
        # Controleer of user nog bestaat en actief is
        with get_session() as s:
            user = s.get(User, user_id)
            if not user or not user.actief:
                session.pop("user_id", None)
                return jsonify({"fout": "Niet ingelogd."}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator: retourneert 403 als gebruiker geen admin is."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"fout": "Niet ingelogd."}), 401
        with get_session() as s:
            user = s.get(User, user_id)
            if not user or not user.actief:
                session.pop("user_id", None)
                return jsonify({"fout": "Niet ingelogd."}), 401
            if user.rol != "admin":
                return jsonify({"fout": "Toegang geweigerd. Admin rechten vereist."}), 403
        return f(*args, **kwargs)
    return decorated


def is_owner(item, user):
    """True als user.id == item.beheerder_id OF user.rol == 'admin'."""
    if user is None:
        return False
    if user.rol == "admin":
        return True
    return item.beheerder_id == user.id


# ── Statische bestanden ───────────────────────────────────────────────────────

@app.get("/")
def index():
    return send_file(Path(__file__).parent / "index.html")


@app.get("/static/media/<path:filename>")
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)


@app.get("/static/media/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@app.post("/auth/login")
def auth_login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    wachtwoord = data.get("wachtwoord") or ""
    if not email or not wachtwoord:
        return jsonify({"fout": "Email en wachtwoord zijn verplicht."}), 400
    with get_session() as s:
        user = s.query(User).filter_by(email=email).first()
        if not user or not user.actief or not user.check_password(wachtwoord):
            return jsonify({"fout": "Ongeldige inloggegevens."}), 401
        session["user_id"] = user.id
        return jsonify(user.to_dict()), 200


@app.post("/auth/admin-login")
def auth_admin_login():
    data = request.get_json(force=True)
    wachtwoord = data.get("wachtwoord") or ""
    if not wachtwoord:
        return jsonify({"fout": "Wachtwoord is verplicht."}), 400
    with get_session() as s:
        admin = s.query(User).filter_by(rol="admin", actief=True).first()
        if not admin or not admin.check_password(wachtwoord):
            return jsonify({"fout": "Ongeldig wachtwoord."}), 401
        session["user_id"] = admin.id
        return jsonify(admin.to_dict()), 200


@app.post("/auth/logout")
def auth_logout():
    session.pop("user_id", None)
    return jsonify({"bericht": "Uitgelogd."}), 200


@app.get("/auth/me")
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"fout": "Niet ingelogd."}), 401
    with get_session() as s:
        user = s.get(User, user_id)
        if not user or not user.actief:
            session.pop("user_id", None)
            return jsonify({"fout": "Niet ingelogd."}), 401
        return jsonify(user.to_dict()), 200


# ── Users endpoints (admin only) ───────────────────────────────────────────────

@app.get("/users")
@require_admin
def list_users():
    with get_session() as s:
        users = s.query(User).order_by(User.naam).all()
        return jsonify([u.to_dict() for u in users])


@app.post("/users")
@require_admin
def create_user():
    data = request.get_json(force=True)
    naam = (data.get("naam") or "").strip()
    email = (data.get("email") or "").strip().lower()
    wachtwoord = data.get("wachtwoord") or ""
    rol = data.get("rol", "gebruiker")
    if not naam or not email or not wachtwoord:
        abort(400, "Naam, email en wachtwoord zijn verplicht.")
    if rol not in ("admin", "gebruiker"):
        abort(400, "Rol moet 'admin' of 'gebruiker' zijn.")
    with get_session() as s:
        bestaand = s.query(User).filter_by(email=email).first()
        if bestaand:
            return jsonify({"fout": "Email al in gebruik."}), 409
        u = User(naam=naam, email=email, rol=rol, aangemaakt_datum=now())
        u.set_password(wachtwoord)
        s.add(u)
        s.commit()
        s.refresh(u)
        return jsonify(u.to_dict()), 201


@app.put("/users/<int:id>")
@require_admin
def update_user(id):
    data = request.get_json(force=True)
    with get_session() as s:
        u = get_or_404(s, User, id)
        if "naam" in data:
            u.naam = data["naam"].strip()
        if "email" in data:
            nieuw_email = data["email"].strip().lower()
            bestaand = s.query(User).filter(User.email == nieuw_email, User.id != id).first()
            if bestaand:
                return jsonify({"fout": "Email al in gebruik."}), 409
            u.email = nieuw_email
        if "rol" in data:
            if data["rol"] not in ("admin", "gebruiker"):
                abort(400, "Ongeldige rol.")
            u.rol = data["rol"]
        if "actief" in data:
            u.actief = bool(data["actief"])
        if "wachtwoord" in data and data["wachtwoord"]:
            u.set_password(data["wachtwoord"])
        s.commit()
        s.refresh(u)
        return jsonify(u.to_dict())


@app.delete("/users/<int:id>")
@require_admin
def delete_user(id):
    current_id = session.get("user_id")
    if current_id == id:
        return jsonify({"fout": "Je kunt jezelf niet verwijderen."}), 400
    with get_session() as s:
        u = get_or_404(s, User, id)
        s.delete(u)
        s.commit()
        return jsonify({"bericht": f"Gebruiker {id} verwijderd."}), 200


# ── Tools ─────────────────────────────────────────────────────────────────────

TOOL_FIELDS = ["naam", "eigenaar", "beschrijving", "status",
               "ingebracht_door", "gewijzigd_door",
               "tijdbalk_start", "tijdbalk_eind", "tool_url"]


def validate_tijdbalk(data):
    for key in ("tijdbalk_start", "tijdbalk_eind"):
        v = data.get(key)
        if v is None:
            continue
        if v == "" or v == 0:
            data[key] = None
            continue
        try:
            v = int(v)
        except (TypeError, ValueError):
            abort(400, f"{key} moet een getal zijn.")
        if not (1 <= v <= 99):
            abort(400, f"{key} moet tussen 1 en 99 liggen.")
        data[key] = v
    s = data.get("tijdbalk_start")
    e = data.get("tijdbalk_eind")
    if s and e and s >= e:
        abort(400, "tijdbalk_start moet kleiner zijn dan tijdbalk_eind.")


@app.get("/tools")
@require_login
def list_tools():
    with get_session() as s:
        tools = s.query(Tool).order_by(Tool.naam).all()
        return jsonify([t.to_dict(include_relations=True) for t in tools])


@app.get("/tools/<int:id>")
@require_login
def get_tool(id):
    with get_session() as s:
        t = get_or_404(s, Tool, id)
        return jsonify(t.to_dict(include_relations=True))


@app.post("/tools")
@require_login
def create_tool():
    data = request.get_json(force=True)
    if not data.get("naam"):
        abort(400, "Veld 'naam' is verplicht.")
    validate_tijdbalk(data)
    user_id = session.get("user_id")
    with get_session() as s:
        user = s.get(User, user_id)
        t = Tool(ingebracht_datum=now(), gewijzigd_datum=now())
        t.beheerder_id = user_id
        # Auto-fill ingebracht_door met naam van ingelogde gebruiker als niet opgegeven
        if not data.get("ingebracht_door") and user:
            data["ingebracht_door"] = user.naam
        apply_fields(t, data, TOOL_FIELDS)
        s.add(t)
        s.commit()
        s.refresh(t)
        return jsonify(t.to_dict()), 201


@app.put("/tools/<int:id>")
@require_login
def update_tool(id):
    data = request.get_json(force=True)
    validate_tijdbalk(data)
    user_id = session.get("user_id")
    with get_session() as s:
        t = get_or_404(s, Tool, id)
        user = s.get(User, user_id)
        if not is_owner(t, user):
            return jsonify({"fout": "Geen rechten om dit item te bewerken."}), 403
        # Auto-fill gewijzigd_door met naam van ingelogde gebruiker
        if user and not data.get("gewijzigd_door"):
            data["gewijzigd_door"] = user.naam
        apply_fields(t, data, TOOL_FIELDS)
        t.gewijzigd_datum = now()
        s.commit()
        s.refresh(t)
        return jsonify(t.to_dict(include_relations=True))


@app.delete("/tools/<int:id>")
@require_login
def delete_tool(id):
    user_id = session.get("user_id")
    with get_session() as s:
        t = get_or_404(s, Tool, id)
        user = s.get(User, user_id)
        if not is_owner(t, user):
            return jsonify({"fout": "Geen rechten om dit item te verwijderen."}), 403
        # Verwijder mediabestanden van schijf
        for m in t.media_items:
            _remove_file(m.bestand)
        s.delete(t)
        s.commit()
        return jsonify({"bericht": f"Tool {id} verwijderd."}), 200


# ── Media ─────────────────────────────────────────────────────────────────────

@app.get("/tools/<int:tid>/media")
@require_login
def list_media(tid):
    with get_session() as s:
        tool = get_or_404(s, Tool, tid)
        return jsonify([m.to_dict() for m in tool.media_items])


@app.post("/tools/<int:tid>/media/upload")
@require_login
def upload_media(tid):
    """Bestand uploaden (multipart/form-data, veld 'file'). Afbeelding of video."""
    if "file" not in request.files:
        abort(400, "Geen bestand meegestuurd.")
    f = request.files["file"]
    if not f.filename:
        abort(400, "Lege bestandsnaam.")
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        abort(400, f"Toegestane bestandstypen: afbeeldingen en video's.")

    uid = uuid4().hex
    is_video = ext in VIDEO_EXT

    if is_video:
        # Sla video op in videos/
        video_bestand = f"{uid}{ext}"
        video_pad = VIDEO_DIR / video_bestand
        f.save(video_pad)

        # Extraheer still met ffmpeg
        still_bestand = f"{uid}_still.jpg"
        still_pad = MEDIA_DIR / still_bestand
        still_ok = extract_video_still(video_pad, still_pad)

        if not still_ok:
            still_bestand = None

        media_type = "video"
        video_url   = f"/static/media/videos/{video_bestand}"
        bestand     = still_bestand
    else:
        bestand_naam = f"{uid}{ext}"
        f.save(MEDIA_DIR / bestand_naam)
        _resize(MEDIA_DIR / bestand_naam)
        media_type = "image"
        video_url  = None
        bestand    = bestand_naam

    with get_session() as s:
        tool = get_or_404(s, Tool, tid)
        is_cover = len(tool.media_items) == 0
        item = MediaItem(
            tool_id=tid, type="upload",
            media_type=media_type,
            video_url=video_url,
            bestand=bestand,
            is_cover=is_cover,
            volgorde=len(tool.media_items),
        )
        s.add(item)
        s.commit()
        s.refresh(item)
        return jsonify(item.to_dict()), 201


@app.post("/tools/<int:tid>/media/url")
@require_login
def add_url_media(tid):
    """URL toevoegen: YouTube/Vimeo → thumbnail, overige → screenshot."""
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    if not url:
        abort(400, "URL is verplicht.")

    still_bestand = f"{uuid4().hex}.jpg"
    still_pad = MEDIA_DIR / still_bestand

    result = process_url(url, still_pad)
    if not result["ok"]:
        abort(500, "Kon geen thumbnail/screenshot ophalen. Controleer de URL.")

    with get_session() as s:
        tool = get_or_404(s, Tool, tid)
        is_cover = len(tool.media_items) == 0
        item = MediaItem(
            tool_id=tid, type="url",
            media_type=result["media_type"],
            bron_url=url,
            video_url=result["video_url"],
            bestand=still_bestand,
            is_cover=is_cover,
            volgorde=len(tool.media_items),
        )
        s.add(item)
        s.commit()
        s.refresh(item)
        return jsonify(item.to_dict()), 201


@app.delete("/tools/<int:tid>/media/<int:mid>")
@require_login
def delete_media(tid, mid):
    with get_session() as s:
        item = s.get(MediaItem, mid)
        if not item or item.tool_id != tid:
            abort(404)
        was_cover = item.is_cover
        bestand   = item.bestand
        s.delete(item)
        s.flush()
        # Herbenoem cover als dit item de cover was
        if was_cover:
            tool = get_or_404(s, Tool, tid)
            _first_cover(tool)
        s.commit()
    _remove_file(bestand)
    return jsonify({"bericht": "Media verwijderd."}), 200


@app.put("/tools/<int:tid>/media/<int:mid>/cover")
@require_login
def set_cover(tid, mid):
    with get_session() as s:
        tool = get_or_404(s, Tool, tid)
        found = False
        for item in tool.media_items:
            item.is_cover = (item.id == mid)
            if item.id == mid:
                found = True
        if not found:
            abort(404)
        s.commit()
        return jsonify({"bericht": "Voorblad ingesteld."}), 200


def _remove_file(bestand):
    if not bestand:
        return
    try:
        (MEDIA_DIR / bestand).unlink(missing_ok=True)
    except Exception:
        pass


# ── Projecten ─────────────────────────────────────────────────────────────────

PROJECT_FIELDS = ["naam", "projectleider", "opdrachtgever", "status",
                  "opmerkingen", "ingebracht_door", "gewijzigd_door"]


@app.get("/projecten")
@require_login
def list_projecten():
    with get_session() as s:
        items = s.query(Project).order_by(Project.naam).all()
        return jsonify([p.to_dict(include_relations=True) for p in items])


@app.get("/projecten/<int:id>")
@require_login
def get_project(id):
    with get_session() as s:
        p = get_or_404(s, Project, id)
        return jsonify(p.to_dict(include_relations=True))


@app.post("/projecten")
@require_login
def create_project():
    data = request.get_json(force=True)
    if not data.get("naam"):
        abort(400, "Veld 'naam' is verplicht.")
    user_id = session.get("user_id")
    with get_session() as s:
        user = s.get(User, user_id)
        p = Project(ingebracht_datum=now(), gewijzigd_datum=now())
        p.beheerder_id = user_id
        if not data.get("ingebracht_door") and user:
            data["ingebracht_door"] = user.naam
        apply_fields(p, data, PROJECT_FIELDS)
        s.add(p)
        s.commit()
        s.refresh(p)
        return jsonify(p.to_dict()), 201


@app.put("/projecten/<int:id>")
@require_login
def update_project(id):
    data = request.get_json(force=True)
    user_id = session.get("user_id")
    with get_session() as s:
        p = get_or_404(s, Project, id)
        user = s.get(User, user_id)
        if not is_owner(p, user):
            return jsonify({"fout": "Geen rechten om dit item te bewerken."}), 403
        if user and not data.get("gewijzigd_door"):
            data["gewijzigd_door"] = user.naam
        apply_fields(p, data, PROJECT_FIELDS)
        p.gewijzigd_datum = now()
        s.commit()
        s.refresh(p)
        return jsonify(p.to_dict(include_relations=True))


@app.delete("/projecten/<int:id>")
@require_login
def delete_project(id):
    user_id = session.get("user_id")
    with get_session() as s:
        p = get_or_404(s, Project, id)
        user = s.get(User, user_id)
        if not is_owner(p, user):
            return jsonify({"fout": "Geen rechten om dit item te verwijderen."}), 403
        s.delete(p)
        s.commit()
        return jsonify({"bericht": f"Project {id} verwijderd."}), 200


# ── Problemen ─────────────────────────────────────────────────────────────────

PROBLEEM_FIELDS = ["titel", "beschrijving", "status", "opmerkingen",
                   "ingebracht_door", "gewijzigd_door"]


@app.get("/problemen")
@require_login
def list_problemen():
    with get_session() as s:
        items = s.query(Probleem).order_by(Probleem.titel).all()
        return jsonify([p.to_dict(include_relations=True) for p in items])


@app.get("/problemen/<int:id>")
@require_login
def get_probleem(id):
    with get_session() as s:
        p = get_or_404(s, Probleem, id)
        return jsonify(p.to_dict(include_relations=True))


@app.post("/problemen")
@require_login
def create_probleem():
    data = request.get_json(force=True)
    if not data.get("titel"):
        abort(400, "Veld 'titel' is verplicht.")
    user_id = session.get("user_id")
    with get_session() as s:
        user = s.get(User, user_id)
        p = Probleem(ingebracht_datum=now(), gewijzigd_datum=now())
        p.beheerder_id = user_id
        if not data.get("ingebracht_door") and user:
            data["ingebracht_door"] = user.naam
        apply_fields(p, data, PROBLEEM_FIELDS)
        s.add(p)
        s.commit()
        s.refresh(p)
        return jsonify(p.to_dict()), 201


@app.put("/problemen/<int:id>")
@require_login
def update_probleem(id):
    data = request.get_json(force=True)
    user_id = session.get("user_id")
    with get_session() as s:
        p = get_or_404(s, Probleem, id)
        user = s.get(User, user_id)
        if not is_owner(p, user):
            return jsonify({"fout": "Geen rechten om dit item te bewerken."}), 403
        if user and not data.get("gewijzigd_door"):
            data["gewijzigd_door"] = user.naam
        apply_fields(p, data, PROBLEEM_FIELDS)
        p.gewijzigd_datum = now()
        s.commit()
        s.refresh(p)
        return jsonify(p.to_dict(include_relations=True))


@app.delete("/problemen/<int:id>")
@require_login
def delete_probleem(id):
    user_id = session.get("user_id")
    with get_session() as s:
        p = get_or_404(s, Probleem, id)
        user = s.get(User, user_id)
        if not is_owner(p, user):
            return jsonify({"fout": "Geen rechten om dit item te verwijderen."}), 403
        s.delete(p)
        s.commit()
        return jsonify({"bericht": f"Probleem {id} verwijderd."}), 200


# ── Koppelingen ───────────────────────────────────────────────────────────────

@app.post("/tools/<int:tid>/projecten/<int:pid>")
@require_login
def koppel_tool_project(tid, pid):
    with get_session() as s:
        tool    = get_or_404(s, Tool, tid)
        project = get_or_404(s, Project, pid)
        if project not in tool.projecten:
            tool.projecten.append(project)
            s.commit()
        return jsonify({"bericht": f"Tool {tid} gekoppeld aan project {pid}."}), 200


@app.delete("/tools/<int:tid>/projecten/<int:pid>")
@require_login
def ontkoppel_tool_project(tid, pid):
    with get_session() as s:
        tool    = get_or_404(s, Tool, tid)
        project = get_or_404(s, Project, pid)
        if project in tool.projecten:
            tool.projecten.remove(project)
            s.commit()
        return jsonify({"bericht": f"Tool {tid} ontkoppeld van project {pid}."}), 200


@app.post("/tools/<int:tid>/problemen/<int:pid>")
@require_login
def koppel_tool_probleem(tid, pid):
    with get_session() as s:
        tool     = get_or_404(s, Tool, tid)
        probleem = get_or_404(s, Probleem, pid)
        if probleem not in tool.problemen:
            tool.problemen.append(probleem)
            s.commit()
        return jsonify({"bericht": f"Tool {tid} gekoppeld aan probleem {pid}."}), 200


@app.delete("/tools/<int:tid>/problemen/<int:pid>")
@require_login
def ontkoppel_tool_probleem(tid, pid):
    with get_session() as s:
        tool     = get_or_404(s, Tool, tid)
        probleem = get_or_404(s, Probleem, pid)
        if probleem in tool.problemen:
            tool.problemen.remove(probleem)
            s.commit()
        return jsonify({"bericht": f"Tool {tid} ontkoppeld van probleem {pid}."}), 200


# ── Foutafhandeling ───────────────────────────────────────────────────────────

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def http_error(e):
    return jsonify({"fout": str(e)}), e.code


# ── Start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_migrations()
    init_db()
    from seed_data import seed, update_tijdbalk, ensure_admin
    seed()
    update_tijdbalk()
    ensure_admin()
    print("\nToolregister API gestart op http://localhost:8181\n")
    app.run(host="127.0.0.1", port=8181, debug=False, use_reloader=False)

"""
Toolregister – SQLAlchemy ORM modellen
Datamodel: Tools / Projecten / Problemen + twee koppeltabellen + MediaItem + User
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Boolean,
    Table, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = "sqlite:///toolregister.db"

engine = create_engine(DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


# ── Koppeltabellen ────────────────────────────────────────────────────────────

tool_project = Table(
    "tool_project", Base.metadata,
    Column("tool_id",    Integer, ForeignKey("tools.id"),     primary_key=True),
    Column("project_id", Integer, ForeignKey("projecten.id"), primary_key=True),
)

tool_probleem = Table(
    "tool_probleem", Base.metadata,
    Column("tool_id",     Integer, ForeignKey("tools.id"),     primary_key=True),
    Column("probleem_id", Integer, ForeignKey("problemen.id"), primary_key=True),
)


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    naam             = Column(String(200), nullable=False)
    email            = Column(String(200), nullable=False, unique=True)
    wachtwoord_hash  = Column(String(512), nullable=False)
    rol              = Column(String(20), default="gebruiker")  # 'admin' | 'gebruiker'
    aangemaakt_datum = Column(DateTime, default=datetime.utcnow)
    actief           = Column(Boolean, default=True)

    def set_password(self, wachtwoord: str):
        self.wachtwoord_hash = generate_password_hash(wachtwoord, method="pbkdf2:sha256")

    def check_password(self, wachtwoord: str) -> bool:
        return check_password_hash(self.wachtwoord_hash, wachtwoord)

    def to_dict(self):
        return {
            "id":               self.id,
            "naam":             self.naam,
            "email":            self.email,
            "rol":              self.rol,
            "aangemaakt_datum": self.aangemaakt_datum.isoformat() if self.aangemaakt_datum else None,
            "actief":           self.actief,
        }


# ── MediaItem ─────────────────────────────────────────────────────────────────

class MediaItem(Base):
    __tablename__ = "media_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    tool_id       = Column(Integer, ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    type          = Column(String(20), default="upload")  # 'upload' | 'url'
    media_type    = Column(String(10), default="image")   # 'image' | 'video'
    bron_url      = Column(Text)    # originele URL (type='url') of afspeelpad (video)
    video_url     = Column(Text)    # afspeelbare URL (embed of /static/media/videos/…)
    bestand       = Column(String(500))  # still/thumbnail bestandsnaam in static/media/
    is_cover      = Column(Boolean, default=False)
    volgorde      = Column(Integer, default=0)

    tool = relationship("Tool", back_populates="media_items")

    def to_dict(self):
        return {
            "id":         self.id,
            "type":       self.type,
            "media_type": self.media_type or "image",
            "bron_url":   self.bron_url,
            "video_url":  self.video_url,
            "bestand":    self.bestand,
            "url":        f"/static/media/{self.bestand}" if self.bestand else None,
            "is_cover":   self.is_cover,
            "volgorde":   self.volgorde,
        }


# ── Hoofdtabellen ─────────────────────────────────────────────────────────────

class Tool(Base):
    __tablename__ = "tools"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    naam             = Column(String(200), nullable=False)
    eigenaar         = Column(String(200))
    beschrijving     = Column(Text)
    status           = Column(String(50))
    tijdbalk_start   = Column(Integer)   # 1–99
    tijdbalk_eind    = Column(Integer)   # 1–99, > start
    tool_url         = Column(String(500))  # link naar de tool
    beheerder_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    ingebracht_door  = Column(String(200))
    ingebracht_datum = Column(DateTime, default=datetime.utcnow)
    gewijzigd_door   = Column(String(200))
    gewijzigd_datum  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projecten   = relationship("Project",   secondary=tool_project,  back_populates="tools")
    problemen   = relationship("Probleem",  secondary=tool_probleem, back_populates="tools")
    media_items = relationship("MediaItem", back_populates="tool",
                               cascade="all, delete-orphan",
                               order_by="MediaItem.volgorde")
    beheerder   = relationship("User", foreign_keys=[beheerder_id])

    def to_dict(self, include_relations=False):
        d = {
            "id":               self.id,
            "naam":             self.naam,
            "eigenaar":         self.eigenaar,
            "beschrijving":     self.beschrijving,
            "status":           self.status,
            "tool_url":         self.tool_url,
            "beheerder_id":     self.beheerder_id,
            "beheerder":        {"id": self.beheerder.id, "naam": self.beheerder.naam} if self.beheerder else None,
            "media_items":      [m.to_dict() for m in self.media_items],
            "tijdbalk_start":   self.tijdbalk_start,
            "tijdbalk_eind":    self.tijdbalk_eind,
            "ingebracht_door":  self.ingebracht_door,
            "ingebracht_datum": self.ingebracht_datum.isoformat() if self.ingebracht_datum else None,
            "gewijzigd_door":   self.gewijzigd_door,
            "gewijzigd_datum":  self.gewijzigd_datum.isoformat() if self.gewijzigd_datum else None,
        }
        if include_relations:
            d["projecten"] = [{"id": p.id, "naam": p.naam} for p in self.projecten]
            d["problemen"] = [{"id": p.id, "titel": p.titel} for p in self.problemen]
        return d


class Project(Base):
    __tablename__ = "projecten"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    naam             = Column(String(200), nullable=False)
    projectleider    = Column(String(200))
    opdrachtgever    = Column(String(200))
    status           = Column(String(50))
    opmerkingen      = Column(Text)
    beheerder_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    ingebracht_door  = Column(String(200))
    ingebracht_datum = Column(DateTime, default=datetime.utcnow)
    gewijzigd_door   = Column(String(200))
    gewijzigd_datum  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tools     = relationship("Tool", secondary=tool_project, back_populates="projecten")
    beheerder = relationship("User", foreign_keys=[beheerder_id])

    def to_dict(self, include_relations=False):
        d = {
            "id":               self.id,
            "naam":             self.naam,
            "projectleider":    self.projectleider,
            "opdrachtgever":    self.opdrachtgever,
            "status":           self.status,
            "opmerkingen":      self.opmerkingen,
            "beheerder_id":     self.beheerder_id,
            "beheerder":        {"id": self.beheerder.id, "naam": self.beheerder.naam} if self.beheerder else None,
            "ingebracht_door":  self.ingebracht_door,
            "ingebracht_datum": self.ingebracht_datum.isoformat() if self.ingebracht_datum else None,
            "gewijzigd_door":   self.gewijzigd_door,
            "gewijzigd_datum":  self.gewijzigd_datum.isoformat() if self.gewijzigd_datum else None,
        }
        if include_relations:
            d["tools"] = [{"id": t.id, "naam": t.naam} for t in self.tools]
        return d


class Probleem(Base):
    __tablename__ = "problemen"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    titel            = Column(String(300), nullable=False)
    beschrijving     = Column(Text)
    status           = Column(String(50))
    beheerder_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    ingebracht_door  = Column(String(200))
    ingebracht_datum = Column(DateTime, default=datetime.utcnow)
    gewijzigd_door   = Column(String(200))
    gewijzigd_datum  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    opmerkingen      = Column(Text)

    tools     = relationship("Tool", secondary=tool_probleem, back_populates="problemen")
    beheerder = relationship("User", foreign_keys=[beheerder_id])

    def to_dict(self, include_relations=False):
        d = {
            "id":               self.id,
            "titel":            self.titel,
            "beschrijving":     self.beschrijving,
            "status":           self.status,
            "beheerder_id":     self.beheerder_id,
            "beheerder":        {"id": self.beheerder.id, "naam": self.beheerder.naam} if self.beheerder else None,
            "ingebracht_door":  self.ingebracht_door,
            "ingebracht_datum": self.ingebracht_datum.isoformat() if self.ingebracht_datum else None,
            "gewijzigd_door":   self.gewijzigd_door,
            "gewijzigd_datum":  self.gewijzigd_datum.isoformat() if self.gewijzigd_datum else None,
            "opmerkingen":      self.opmerkingen,
        }
        if include_relations:
            d["tools"] = [{"id": t.id, "naam": t.naam} for t in self.tools]
        return d


def init_db():
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)

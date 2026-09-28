import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session

# --- Настройка БД ---
# Локально — sqlite. На проде подставь DATABASE_URL из Supabase, режим psycopg3:
# postgresql+psycopg://postgres.xxxx:[PASSWORD]@aws-...pooler.supabase.com:6543/postgres
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./demo.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Client(Base):
    __tablename__ = "client"

    # Намеренно без Mapped[...]-аннотаций и без Optional — на Python 3.14
    # сканирование таких аннотаций в SQLAlchemy 2.0.36 падает с TypeError
    # (баг в de_stringify_union_elements). Старый стиль Column полностью
    # обходит этот код и работает одинаково на любой версии Python.
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_tg_id = Column(Integer, default=0)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    category = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    last_visit = Column(DateTime(timezone=True), default=now_utc)
    visit_count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_tg_id": self.owner_tg_id,
            "name": self.name,
            "phone": self.phone,
            "category": self.category,
            "notes": self.notes,
            "last_visit": self.last_visit.isoformat(),
            "visit_count": self.visit_count,
            "created_at": self.created_at.isoformat(),
        }


def create_db_and_tables() -> None:
    Base.metadata.create_all(engine)


app = FastAPI(title="Client Base MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


def status_color(last_visit: datetime) -> str:
    lv = last_visit if last_visit.tzinfo else last_visit.replace(tzinfo=timezone.utc)
    days = (now_utc() - lv).days
    if days < 14:
        return "green"
    if days < 30:
        return "yellow"
    return "red"


@app.get("/api/clients")
def list_clients(category: Optional[str] = None, owner_tg_id: Optional[int] = None):
    with Session(engine) as session:
        query = select(Client)
        if category:
            query = query.where(Client.category == category)
        if owner_tg_id:
            query = query.where(Client.owner_tg_id == owner_tg_id)
        clients = session.execute(query.order_by(Client.last_visit)).scalars().all()
        out = []
        for c in clients:
            d = c.to_dict()
            d["status"] = status_color(c.last_visit)
            lv = c.last_visit if c.last_visit.tzinfo else c.last_visit.replace(tzinfo=timezone.utc)
            d["days_since"] = (now_utc() - lv).days
            out.append(d)
        return out


@app.post("/api/clients")
def create_client(payload: dict = Body(...)):
    name = payload.get("name")
    phone = payload.get("phone")
    if not name or not phone:
        raise HTTPException(400, "Нужны name и phone")
    with Session(engine) as session:
        client = Client(
            name=name,
            phone=phone,
            category=payload.get("category", "Другое"),
            notes=payload.get("notes"),
            owner_tg_id=payload.get("owner_tg_id", 0),
        )
        session.add(client)
        session.commit()
        session.refresh(client)
        return client.to_dict()


@app.patch("/api/clients/{client_id}/visit")
def mark_visit(client_id: int):
    with Session(engine) as session:
        client = session.get(Client, client_id)
        if not client:
            raise HTTPException(404, "Клиент не найден")
        client.last_visit = now_utc()
        client.visit_count += 1
        session.commit()
        session.refresh(client)
        return client.to_dict()


@app.patch("/api/clients/{client_id}")
def update_client(client_id: int, payload: dict = Body(...)):
    with Session(engine) as session:
        client = session.get(Client, client_id)
        if not client:
            raise HTTPException(404, "Клиент не найден")
        for key in ("name", "phone", "category", "notes"):
            if key in payload:
                setattr(client, key, payload[key])
        session.commit()
        session.refresh(client)
        return client.to_dict()


@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int):
    with Session(engine) as session:
        client = session.get(Client, client_id)
        if not client:
            raise HTTPException(404, "Клиент не найден")
        session.delete(client)
        session.commit()
        return {"ok": True}


@app.get("/api/stats")
def get_stats(owner_tg_id: Optional[int] = None):
    with Session(engine) as session:
        query = select(Client)
        if owner_tg_id:
            query = query.where(Client.owner_tg_id == owner_tg_id)
        clients = session.execute(query).scalars().all()
        green = yellow = red = 0
        for c in clients:
            s = status_color(c.last_visit)
            if s == "green":
                green += 1
            elif s == "yellow":
                yellow += 1
            else:
                red += 1
        return {"green": green, "yellow": yellow, "red": red, "total": len(clients)}


@app.get("/api/cron/check-sleeping")
def check_sleeping():
    """Дергается cron-job.org раз в день. Позже сюда добавим отправку
    сообщения мастеру в Telegram через aiogram Bot API."""
    with Session(engine) as session:
        clients = session.execute(select(Client)).scalars().all()
        sleeping = [c for c in clients if status_color(c.last_visit) == "red"]
        return {"sleeping_count": len(sleeping), "names": [c.name for c in sleeping]}


@app.get("/api/ping")
def ping():
    """Дергается cron-job.org каждые 10 минут, чтобы бесплатный инстанс не засыпал."""
    return {"status": "alive"}


# Отдаём WebApp как статику — один сервис вместо двух деплоев
app.mount("/", StaticFiles(directory="static", html=True), name="static")

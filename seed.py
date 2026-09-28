import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from main import Client, Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./demo.db")
engine = create_engine(DATABASE_URL)

def seed_db():
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        # 1. Очищаем таблицу от дубликатов
        session.execute(delete(Client))
        session.commit()

        # 2. Создаем чистый список из 7 клиентов
        demo_clients = [
            Client(name="Наталья", phone="+79001112233", category="Массаж спины", notes="Любит крепкий массаж", last_visit=now - timedelta(days=45)),
            Client(name="Ольга", phone="+79002223344", category="Йога", notes="Хочет вечернюю группу", last_visit=now - timedelta(days=35)),
            Client(name="Жанна", phone="+79003334455", category="Бодифлекс", notes="", last_visit=now - timedelta(days=25)),
            Client(name="Светлана", phone="+79004445566", category="Массаж спины", notes="Аллергия на масло с запахом", last_visit=now - timedelta(days=20)),
            Client(name="Елена", phone="+79005556677", category="Йога", notes="", last_visit=now - timedelta(days=10)),
            Client(name="Ирина", phone="+79006667788", category="Бодифлекс", notes="Ходит регулярно", last_visit=now - timedelta(days=5)),
            Client(name="Мария", phone="+79007778899", category="Массаж спины", notes="", last_visit=now - timedelta(days=2)),
        ]

        session.add_all(demo_clients)
        session.commit()
        print("База полностью очищена и заново добавлено 7 демо-клиентов.")

if __name__ == "__main__":
    seed_db()

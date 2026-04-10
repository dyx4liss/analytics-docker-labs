from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import and_
import os
import time
from datetime import date, time

# Ожидание готовности БД (для надёжности в K8s)
time.sleep(5)

# Параметры подключения к БД из переменных окружения
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "postgres-service")
DB_NAME = os.getenv("DB_NAME", "booking_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель таблицы бронирований
class Booking(Base):
    tablename = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    room = Column(String, index=True)
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    booked_by = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Pydantic модели для запросов/ответов
class BookingCreate(BaseModel):
    room: str
    date: date
    start_time: time
    end_time: time
    booked_by: str

class BookingResponse(BookingCreate):
    id: int

    class Config:
        orm_mode = True

# Проверка конфликта бронирования
def is_overlapping(db, room: str, date_val: date, start: time, end: time, exclude_id: int = None):
    query = db.query(Booking).filter(
        and_(
            Booking.room == room,
            Booking.date == date_val,
            # Пересечение интервалов: start1 < end2 AND start2 < end1
            Booking.start_time < end,
            Booking.end_time > start
        )
    )
    if exclude_id is not None:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None

@app.get("/bookings", response_model=list[BookingResponse])
def get_bookings(room: str = None, date: date = None):
    db = SessionLocal()
    query = db.query(Booking)
    if room:
        query = query.filter(Booking.room == room)
    if date:
        query = query.filter(Booking.date == date)
    bookings = query.all()
    db.close()
    return bookings

@app.post("/bookings", response_model=BookingResponse)
def add_booking(booking: BookingCreate):
    db = SessionLocal()
    # Проверка конфликта
    if is_overlapping(db, booking.room, booking.date, booking.start_time, booking.end_time):
        db.close()
        raise HTTPException(status_code=400, detail="Room is already booked for this time slot")
    new_booking = Booking(**booking.dict())
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    db.close()
    return new_booking

@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: int):
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        db.close()
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    db.close()
    return {"message": "Booking deleted"}
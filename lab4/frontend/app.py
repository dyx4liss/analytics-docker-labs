import streamlit as st
import requests
import pandas as pd
import os
from datetime import date, time, datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend-service:8000")

st.set_page_config(page_title="Booking System", layout="wide")
st.title("📅 Бронирование переговорных комнат")

# --- Боковая панель: фильтры ---
st.sidebar.header("Фильтры")
filter_room = st.sidebar.text_input("Комната")
filter_date = st.sidebar.date_input("Дата", value=None)
if st.sidebar.button("Сбросить фильтры"):
    filter_room = ""
    filter_date = None

# --- Форма добавления бронирования ---
st.header("➕ Новое бронирование")
with st.form("booking_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        room = st.selectbox("Комната", ["Переговорная 101", "Переговорная 102", "Конференц-зал", "Зал совещаний"])
    with col2:
        booking_date = st.date_input("Дата", value=date.today())
    with col3:
        booked_by = st.text_input("Кто бронирует")
    col4, col5 = st.columns(2)
    with col4:
        start_time = st.time_input("Время начала", value=time(9, 0))
    with col5:
        end_time = st.time_input("Время окончания", value=time(10, 0))

    submitted = st.form_submit_button("Забронировать")

    if submitted:
        if not booked_by:
            st.error("Введите имя бронирующего")
        elif start_time >= end_time:
            st.error("Время окончания должно быть позже времени начала")
        else:
            payload = {
                "room": room,
                "date": booking_date.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "booked_by": booked_by
            }
            try:
                resp = requests.post(f"{BACKEND_URL}/bookings", json=payload)
                if resp.status_code == 200:
                    st.success("✅ Бронирование успешно создано!")
                else:
                    detail = resp.json().get("detail", "Ошибка сервера")
                    st.error(f"❌ Ошибка: {detail}")
            except Exception as e:
                st.error(f"❌ Нет связи с бэкендом: {e}")

# --- Отображение бронирований ---
st.header("📋 Список бронирований")

def load_bookings():
    params = {}
    if filter_room:
        params["room"] = filter_room
    if filter_date:
        params["date"] = filter_date.isoformat()
    try:
        resp = requests.get(f"{BACKEND_URL}/bookings", params=params)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error("Ошибка загрузки данных")
            return []
    except Exception as e:
        st.error(f"Нет соединения с бэкендом: {BACKEND_URL}")
        return []

if st.button("🔄 Обновить данные"):
    st.experimental_rerun()

bookings = load_bookings()
if bookings:
    df = pd.DataFrame(bookings)
    # Преобразуем колонки для читаемости
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["start_time"] = pd.to_datetime(df["start_time"], format="%H:%M:%S").dt.time
    df["end_time"] = pd.to_datetime(df["end_time"], format="%H:%M:%S").dt.time
    st.dataframe(df[["room", "date", "start_time", "end_time", "booked_by"]], use_container_width=True)
else:
    st.info("Нет бронирований, удовлетворяющих фильтрам.")
"""
Модуль для работы с базой данных SQLite
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager


class Database:
    def __init__(self, db_path: str = "office_visits.db"):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с подключением"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица посещений офиса
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS office_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    visit_date DATE NOT NULL,
                    was_in_office BOOLEAN NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, visit_date)
                )
            """)
            
            # Индексы для быстрого поиска
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_visits_user_date 
                ON office_visits(user_id, visit_date)
            """)
    
    def add_or_update_user(self, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None):
        """Добавить или обновить пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name
            """, (user_id, username, first_name, last_name))
    
    def mark_visit(self, user_id: int, date: datetime, was_in_office: bool, note: str = None):
        """Отметить посещение офиса"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            date_str = date.strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO office_visits (user_id, visit_date, was_in_office, note)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, visit_date) DO UPDATE SET
                    was_in_office = excluded.was_in_office,
                    note = excluded.note,
                    created_at = CURRENT_TIMESTAMP
            """, (user_id, date_str, was_in_office, note))
    
    def get_visit(self, user_id: int, date: datetime) -> Optional[dict]:
        """Получить информацию о посещении в конкретную дату"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            date_str = date.strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT * FROM office_visits 
                WHERE user_id = ? AND visit_date = ?
            """, (user_id, date_str))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_visits_by_period(self, user_id: int, start_date: datetime, 
                            end_date: datetime) -> List[dict]:
        """Получить все посещения за период"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM office_visits 
                WHERE user_id = ? AND visit_date BETWEEN ? AND ?
                ORDER BY visit_date
            """, (user_id, start_date.strftime("%Y-%m-%d"), 
                  end_date.strftime("%Y-%m-%d")))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_month_visits(self, user_id: int, year: int, month: int) -> List[dict]:
        """Получить все посещения за месяц"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        return self.get_visits_by_period(user_id, start_date, end_date)
    
    def get_week_visits(self, user_id: int, date: datetime) -> List[dict]:
        """Получить посещения за неделю"""
        from datetime import timedelta
        monday = date - timedelta(days=date.weekday())
        sunday = monday + timedelta(days=6)
        return self.get_visits_by_period(user_id, monday, sunday)
    
    def get_visits_stats(self, user_id: int, year: int, month: int) -> Tuple[int, int]:
        """
        Получить статистику посещений за месяц
        
        Returns:
            (количество дней в офисе, количество рабочих дней)
        """
        visits = self.get_month_visits(user_id, year, month)
        in_office_count = sum(1 for v in visits if v['was_in_office'])
        return in_office_count, len(visits)
    
    def delete_visit(self, user_id: int, date: datetime):
        """Удалить отметку о посещении"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            date_str = date.strftime("%Y-%m-%d")
            cursor.execute("""
                DELETE FROM office_visits 
                WHERE user_id = ? AND visit_date = ?
            """, (user_id, date_str))

"""
Рабочий календарь России на 2026 год
"""

from datetime import datetime, timedelta
from typing import List, Set

# Праздничные и нерабочие дни в 2026 году (официальные выходные)
HOLIDAYS_2026 = [
    # Новогодние каникулы
    "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04",
    "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08",
    # Рождество (перенос)
    "2026-01-09",
    # День защитника Отечества
    "2026-02-23",
    # Международный женский день
    "2026-03-08",
    # Праздник Весны и Труда
    "2026-05-01",
    # День Победы
    "2026-05-09",
    # День России
    "2026-06-12",
    # День народного единства
    "2026-11-04",
]

# Сокращенные предпраздничные дни
SHORTENED_DAYS_2026 = [
    "2026-02-20",  # Пятница перед 23 февраля
    "2026-03-07",  # Суббота перед 8 марта
    "2026-04-30",  # Четверг перед 1 мая
    "2026-05-08",  # Пятница перед 9 мая
    "2026-06-11",  # Четверг перед 12 июня
    "2026-11-03",  # Вторник перед 4 ноября
    "2026-12-31",  # Четверг перед Новым годом
]

# Перенесенные выходные дни (когда праздник попадает на выходной)
# В 2026 году потребуется проверить официальный календарь
TRANSFERRED_HOLIDAYS_2026 = [
    "2026-05-11",  # Перенос с субботы 9 мая
]


def get_holidays() -> Set[datetime]:
    """Получить set всех праздничных дней"""
    holidays = set()
    for date_str in HOLIDAYS_2026 + TRANSFERRED_HOLIDAYS_2026:
        holidays.add(datetime.strptime(date_str, "%Y-%m-%d").date())
    return holidays


def is_working_day(date: datetime) -> bool:
    """
    Проверить, является ли день рабочим
    
    Args:
        date: Дата для проверки
        
    Returns:
        True если день рабочий, False если выходной/праздник
    """
    date_obj = date.date() if isinstance(date, datetime) else date
    
    # Проверка на праздники
    holidays = get_holidays()
    if date_obj in holidays:
        return False
    
    # Проверка на выходные (суббота=5, воскресенье=6)
    if date_obj.weekday() in [5, 6]:
        return False
    
    return True


def get_work_week_dates(date: datetime) -> List[datetime]:
    """
    Получить все рабочие дни текущей рабочей недели
    
    Args:
        date: Любая дата в неделе
        
    Returns:
        Список рабочих дней в этой неделе
    """
    # Находим понедельник этой недели
    monday = date - timedelta(days=date.weekday())
    
    work_days = []
    for i in range(7):
        current_day = monday + timedelta(days=i)
        if is_working_day(current_day):
            work_days.append(current_day)
    
    return work_days


def get_week_number(date: datetime) -> int:
    """
    Получить номер рабочей недели в году
    
    Args:
        date: Дата
        
    Returns:
        Номер недели (ISO формат)
    """
    return date.isocalendar()[1]


def get_month_working_days(year: int, month: int) -> List[datetime]:
    """
    Получить все рабочие дни в месяце
    
    Args:
        year: Год
        month: Месяц (1-12)
        
    Returns:
        Список рабочих дней в месяце
    """
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    work_days = []
    current = first_day
    while current <= last_day:
        if is_working_day(current):
            work_days.append(current)
        current += timedelta(days=1)
    
    return work_days


def format_date_ru(date: datetime) -> str:
    """Форматировать дату на русском"""
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    weekdays_ru = [
        "Понедельник", "Вторник", "Среда", "Четверг", 
        "Пятница", "Суббота", "Воскресенье"
    ]
    
    return f"{weekdays_ru[date.weekday()]}, {date.day} {months_ru[date.month - 1]} {date.year}"

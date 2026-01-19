"""
Генератор отчетов о посещениях офиса
"""

from datetime import datetime, timedelta
from typing import List, Dict
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import calendar_data
from database import Database


class ReportGenerator:
    def __init__(self, db: Database):
        self.db = db
    
    def generate_text_report(self, user_id: int, year: int, month: int) -> str:
        """Генерация текстового отчета"""
        # Получаем рабочие дни месяца
        work_days = calendar_data.get_month_working_days(year, month)
        
        # Получаем данные о посещениях
        visits = self.db.get_month_visits(user_id, year, month)
        visits_dict = {v['visit_date']: v for v in visits}
        
        # Группируем по неделям
        weeks = {}
        for day in work_days:
            week_num = calendar_data.get_week_number(day)
            if week_num not in weeks:
                weeks[week_num] = []
            weeks[week_num].append(day)
        
        # Формируем отчет
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        
        report = f"📊 <b>Отчет о посещениях офиса</b>\n"
        report += f"📅 <b>{month_names[month - 1]} {year}</b>\n\n"
        
        total_work_days = len(work_days)
        total_office_days = sum(1 for v in visits if v['was_in_office'])
        total_home_days = sum(1 for v in visits if not v['was_in_office'])
        
        report += f"📈 <b>Общая статистика:</b>\n"
        report += f"  • Всего рабочих дней: {total_work_days}\n"
        report += f"  • В офисе: {total_office_days} дней\n"
        report += f"  • Удаленно: {total_home_days} дней\n"
        if total_work_days > 0:
            office_percent = (total_office_days / total_work_days) * 100
            report += f"  • Процент посещений: {office_percent:.1f}%\n"
        report += "\n"
        
        # Отчет по неделям
        report += f"📋 <b>По неделям:</b>\n\n"
        
        for week_num in sorted(weeks.keys()):
            week_days = weeks[week_num]
            office_count = 0
            week_status = []
            
            for day in week_days:
                date_str = day.strftime("%Y-%m-%d")
                if date_str in visits_dict:
                    visit = visits_dict[date_str]
                    if visit['was_in_office']:
                        office_count += 1
                        status = "🏢"
                    else:
                        status = "🏠"
                else:
                    status = "❓"
                
                day_str = day.strftime("%d.%m")
                week_status.append(f"{day_str} {status}")
            
            # Проверяем выполнение требования (минимум 1 день в неделю)
            requirement_met = "✅" if office_count >= 1 else "⚠️"
            
            report += f"<b>Неделя {week_num}</b> {requirement_met}\n"
            report += f"  Дней в офисе: {office_count}\n"
            for status_line in week_status:
                report += f"  {status_line}\n"
            report += "\n"
        
        # Легенда
        report += "━━━━━━━━━━━━━━━━━━━\n"
        report += "🏢 - в офисе\n"
        report += "🏠 - удаленно\n"
        report += "❓ - не отмечено\n"
        report += "✅ - норма выполнена\n"
        report += "⚠️ - требуется посещение\n"
        
        return report
    
    def generate_image_report(self, user_id: int, year: int, month: int) -> BytesIO:
        """Генерация графического отчета (таблица-календарь)"""
        # Получаем данные
        work_days = calendar_data.get_month_working_days(year, month)
        visits = self.db.get_month_visits(user_id, year, month)
        visits_dict = {v['visit_date']: v for v in visits}
        
        # Настройки изображения
        cell_width = 80
        cell_height = 60
        header_height = 80
        margin = 20
        
        # Размеры изображения
        days_in_month = (datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)) - datetime(year, month, 1)
        days_in_month = days_in_month.days
        
        first_day = datetime(year, month, 1)
        first_weekday = first_day.weekday()
        
        weeks_count = ((days_in_month + first_weekday) + 6) // 7
        
        img_width = 7 * cell_width + 2 * margin
        img_height = weeks_count * cell_height + header_height + 2 * margin
        
        # Создаем изображение
        img = Image.new('RGB', (img_width, img_height), color='#f5f5f5')
        draw = ImageDraw.Draw(img)
        
        # Пытаемся загрузить шрифт, если не получается - используем стандартный
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_day = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font_title = ImageFont.load_default()
            font_day = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Заголовок
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        title = f"{month_names[month - 1]} {year}"
        
        # Рисуем заголовок
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((img_width - title_width) // 2, margin), title, fill='#2c3e50', font=font_title)
        
        # Дни недели
        weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        y_offset = margin + 50
        
        for i, day_name in enumerate(weekdays):
            x = margin + i * cell_width + cell_width // 2
            day_bbox = draw.textbbox((0, 0), day_name, font=font_day)
            day_width = day_bbox[2] - day_bbox[0]
            draw.text((x - day_width // 2, y_offset), day_name, fill='#34495e', font=font_day)
        
        # Рисуем календарь
        y_offset = header_height + margin
        current_date = datetime(year, month, 1)
        
        for week in range(weeks_count):
            for day_of_week in range(7):
                if week == 0 and day_of_week < first_weekday:
                    continue
                
                if current_date.month != month:
                    break
                
                x = margin + day_of_week * cell_width
                y = y_offset + week * cell_height
                
                # Рисуем ячейку
                is_working = calendar_data.is_working_day(current_date)
                
                if not is_working:
                    # Выходной день - серый
                    cell_color = '#e0e0e0'
                    text_color = '#95a5a6'
                else:
                    cell_color = '#ffffff'
                    text_color = '#2c3e50'
                
                draw.rectangle([x, y, x + cell_width - 2, y + cell_height - 2], 
                             fill=cell_color, outline='#bdc3c7', width=1)
                
                # Номер дня
                day_num = str(current_date.day)
                day_bbox = draw.textbbox((0, 0), day_num, font=font_day)
                day_width = day_bbox[2] - day_bbox[0]
                draw.text((x + 5, y + 5), day_num, fill=text_color, font=font_day)
                
                # Статус посещения
                if is_working:
                    date_str = current_date.strftime("%Y-%m-%d")
                    if date_str in visits_dict:
                        visit = visits_dict[date_str]
                        if visit['was_in_office']:
                            # В офисе - зеленый круг
                            draw.ellipse([x + cell_width - 25, y + 5, x + cell_width - 10, y + 20], 
                                       fill='#27ae60', outline='#229954')
                            draw.text((x + cell_width - 22, y + 6), "🏢", font=font_small)
                        else:
                            # Удаленно - синий круг
                            draw.ellipse([x + cell_width - 25, y + 5, x + cell_width - 10, y + 20], 
                                       fill='#3498db', outline='#2980b9')
                            draw.text((x + cell_width - 22, y + 6), "🏠", font=font_small)
                    else:
                        # Не отмечено - серый
                        draw.ellipse([x + cell_width - 25, y + 5, x + cell_width - 10, y + 20], 
                                   fill='#95a5a6', outline='#7f8c8d')
                        draw.text((x + cell_width - 22, y + 6), "?", fill='white', font=font_small)
                
                current_date += timedelta(days=1)
        
        # Легенда внизу
        legend_y = y_offset + weeks_count * cell_height + 10
        draw.text((margin, legend_y), "🏢 - в офисе  🏠 - удаленно  ? - не отмечено", 
                 fill='#34495e', font=font_small)
        
        # Сохраняем в BytesIO
        bio = BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        
        return bio
    
    def get_current_week_status(self, user_id: int) -> str:
        """Получить статус текущей недели"""
        today = datetime.now()
        week_days = calendar_data.get_work_week_dates(today)
        
        visits = self.db.get_week_visits(user_id, today)
        visits_dict = {v['visit_date']: v for v in visits}
        
        office_count = sum(1 for v in visits if v['was_in_office'])
        
        status = f"📅 <b>Текущая неделя (неделя {calendar_data.get_week_number(today)})</b>\n\n"
        
        for day in week_days:
            date_str = day.strftime("%Y-%m-%d")
            day_name = calendar_data.format_date_ru(day).split(',')[0]
            day_date = day.strftime("%d.%m")
            
            if date_str in visits_dict:
                visit = visits_dict[date_str]
                icon = "🏢" if visit['was_in_office'] else "🏠"
                status_text = "в офисе" if visit['was_in_office'] else "удаленно"
            else:
                if day.date() > today.date():
                    icon = "⏳"
                    status_text = "планируется"
                else:
                    icon = "❓"
                    status_text = "не отмечено"
            
            status += f"{icon} {day_name} ({day_date}) - {status_text}\n"
        
        status += f"\n<b>Дней в офисе: {office_count}</b>\n"
        
        if office_count >= 1:
            status += "✅ <b>Норма выполнена!</b>"
        else:
            status += "⚠️ <b>Требуется минимум 1 посещение офиса</b>"
        
        return status

import customtkinter as ctk
import os
from tkcalendar import Calendar
from datetime import datetime, timedelta
import uuid
from PIL import Image
from storage import Storage
from notifier import play_alert_sound, stop_alert_sound
import tkinter.simpledialog as sd

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ЛОГИКИ ДАТ ---
def get_next_run_date(task):
    """Определяет ближайшую дату выполнения задачи."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    mode = task.get("mode")
    
    if mode == "once":
        return task.get("date_start", "9999-12-31")
    
    if mode == "specific":
        dates = [d for d in task.get("specific_dt_map", {}).keys() if d >= today_str]
        return min(dates) if dates else "9999-12-31"
    
    if mode == "repeat":
        # Упрощенная логика для сортировки: если задача ежедневная, то сегодня или завтра
        # Для базовой сортировки используем дату старта или сегодня
        start_date = task.get("date_start", today_str)
        return start_date if start_date >= today_str else today_str
        
    return "9999-12-31"

def format_date_display(date_str):
    """Превращает ГГГГ-ММ-ДД в СЕГОДНЯ, ЗАВТРА или ДД.ММ"""
    if date_str == "9999-12-31": return "АРХИВ"
    
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    
    if target == today:
        return "СЕГОДНЯ"
    elif target == today + timedelta(days=1):
        return "ЗАВТРА"
    else:
        return target.strftime("%d.%m")

# Конфигурация шрифтов
HEADER_FONT = ("Impact", 34)
LOGO_FONT = ("Impact", 30)
SUBHEADER_FONT = ("Impact", 24)
NORMAL_FONT = ("Consolas", 12, "bold")
BRUTAL_FONT = ("Consolas", 14, "bold")
BTN_LARGE_FONT = ("Consolas", 16, "bold")
SMALL_FONT = ("Consolas", 9)

ICONS_LIST = [
    "💊", "💪", "🎬", "📌", "🍔", "🏃", "📚", "🎮", "🚗", "💻", 
    "🍎", "☕", "🛌", "🚿", "🧹", "🛒", "🏢", "✈️", "📱", "🔋",
    "🎨", "🎵", "📷", "🐶", "🐱"
]

class IconPicker(ctk.CTkToplevel):
    def __init__(self, master, on_select):
        super().__init__(master)
        self.title("ВЫБОР ИКОНКИ")
        self.geometry("300x400")
        self.on_select = on_select
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        for i, icon in enumerate(ICONS_LIST):
            btn = ctk.CTkButton(frame, text=icon, width=40, font=("Segoe UI Emoji", 20),
                               fg_color="transparent", text_color=("black", "white"), 
                               command=lambda ic=icon: self.select(ic))
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)
    def select(self, icon):
        self.on_select(icon)
        self.destroy()

class TaskDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback, storage, task=None):
        super().__init__(master)
        self.title("PancirTimer 4.0 Pro - РЕДАКТОР")
        self.geometry("800x950")
        self.storage = storage
        self.on_save_callback = on_save_callback
        self.task = task or {}
        self.specific_dt_map = self.task.get("specific_dt_map", {})
        self.selected_icon = "📌"
        if self.task.get("category"):
            for ic in ICONS_LIST:
                if ic in self.task["category"]:
                    self.selected_icon = ic
                    break
        self.setup_ui()
        self.grab_set()

    def setup_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(self.scroll, text="ПАРАМЕТРЫ УВЕДОМЛЕНИЯ", font=SUBHEADER_FONT, text_color="#FF8C00").pack(pady=(0, 20))

        ctk.CTkLabel(self.scroll, text="ЧТО СДЕЛАТЬ?:", font=NORMAL_FONT, text_color="#FF8C00").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(self.scroll, placeholder_text="НАЗВАНИЕ...", height=45, font=BRUTAL_FONT)
        self.name_entry.pack(fill="x", pady=(5, 15))
        if self.task.get("name"): self.name_entry.insert(0, self.task["name"])

        cat_input_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        cat_input_frame.pack(fill="x", pady=5)
        self.icon_btn = ctk.CTkButton(cat_input_frame, text=self.selected_icon, width=50, height=45, 
                                     font=("Segoe UI Emoji", 20), fg_color="#FF8C00", command=self.open_icon_picker)
        self.icon_btn.pack(side="left")
        self.cat_entry = ctk.CTkEntry(cat_input_frame, placeholder_text="ИМЯ КАТЕГОРИИ...", height=45, font=BRUTAL_FONT)
        self.cat_entry.pack(side="left", fill="x", expand=True, padx=10)
        if self.task.get("category"):
            name = self.task["category"]
            for ic in ICONS_LIST: name = name.replace(ic, "").strip()
            self.cat_entry.insert(0, name)
        else: self.cat_entry.insert(0, "ОБЩЕЕ")

        ctk.CTkLabel(self.scroll, text="ОПИСАНИЕ (ЧТО ИМЕННО СДЕЛАТЬ?):", font=NORMAL_FONT, text_color="#FF8C00").pack(anchor="w", pady=(15, 5))
        self.desc_text = ctk.CTkTextbox(self.scroll, height=100, font=NORMAL_FONT, border_width=1, border_color="#FF8C00")
        self.desc_text.pack(fill="x", pady=(0, 15))
        if self.task.get("description"): self.desc_text.insert("1.0", self.task["description"])

        self.mode_var = ctk.StringVar(value=self.task.get("mode", "repeat"))
        mode_frame = ctk.CTkFrame(self.scroll, corner_radius=10, border_width=1, border_color="#FF8C00")
        mode_frame.pack(fill="x", pady=15)
        ctk.CTkRadioButton(mode_frame, text="ЦИКЛИЧНЫЙ ПОВТОР", variable=self.mode_var, value="repeat", command=self.update_mode_ui, fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)
        ctk.CTkRadioButton(mode_frame, text="ВРУЧНУЮ ПО ДАТАМ", variable=self.mode_var, value="specific", command=self.update_mode_ui, fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)
        ctk.CTkRadioButton(mode_frame, text="РАЗОВЫЙ ПОВТОР", variable=self.mode_var, value="once", command=self.update_mode_ui, fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)

        # --- SOUND SELECTION ---
        ctk.CTkLabel(self.scroll, text="ВЫБОР МЕЛОДИИ УВЕДОМЛЕНИЯ:", font=NORMAL_FONT, text_color="#FF8C00").pack(anchor="w", pady=(10, 5))
        self.sound_var = ctk.StringVar(value=self.task.get("sound_type", "quiet"))
        sound_frame = ctk.CTkFrame(self.scroll, corner_radius=10, border_width=1, border_color="#FF8C00")
        sound_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkRadioButton(sound_frame, text="БЕЗ ЗВУКА", variable=self.sound_var, value="none", fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)
        ctk.CTkRadioButton(sound_frame, text="СТАНДАРТ", variable=self.sound_var, value="default", fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)
        ctk.CTkRadioButton(sound_frame, text="ТИХАЯ (HTC)", variable=self.sound_var, value="quiet", fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)
        ctk.CTkRadioButton(sound_frame, text="ГРОМКАЯ (ALARM)", variable=self.sound_var, value="loud", fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10, pady=15)
        # ------------------------


        self.content_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True)

        self.rep_sec = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.rep_cal = Calendar(self.rep_sec, selectmode='day', locale='ru_RU')
        self.rep_cal.pack(pady=(0, 10))
        if self.task.get("date_start"):
            try: self.rep_cal.selection_set(datetime.strptime(self.task["date_start"], "%Y-%m-%d"))
            except: pass

        self.rtype_var = ctk.StringVar(value=self.task.get("repeat_type", "interval"))
        rtype_row = ctk.CTkFrame(self.rep_sec, fg_color="transparent")
        rtype_row.pack(fill="x", pady=5)
        for t, v in [("ЕЖЕДНЕВНО", "daily"), ("ИНТЕРВАЛ", "interval"), ("ДНИ НЕДЕЛИ", "weekly")]:
            ctk.CTkRadioButton(rtype_row, text=t, variable=self.rtype_var, value=v, command=self.update_rep_logic_ui, fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=10)

        self.rep_logic_frame = ctk.CTkFrame(self.rep_sec, fg_color="transparent")
        self.rep_logic_frame.pack(fill="x", pady=0)
        self.int_frame = ctk.CTkFrame(self.rep_logic_frame, fg_color="transparent")
        ctk.CTkLabel(self.int_frame, text="КАЖДЫЕ (ДНЕЙ):", font=NORMAL_FONT).pack(side="left")
        self.int_entry = ctk.CTkEntry(self.int_frame, width=60, font=NORMAL_FONT)
        self.int_entry.insert(0, str(self.task.get("repeat_interval", 1)))
        self.int_entry.pack(side="left", padx=10)

        self.week_frame = ctk.CTkFrame(self.rep_logic_frame, fg_color="transparent")
        self.d_vars = {}
        for t, i in [("ПН",0),("ВТ",1),("СР",2),("ЧТ",3),("ПТ",4),("СБ",5),("ВС",6)]:
            v = ctk.BooleanVar(value=i in self.task.get("repeat_days", []))
            self.d_vars[i] = v
            ctk.CTkCheckBox(self.week_frame, text=t, variable=v, width=45, fg_color="#FF8C00", font=NORMAL_FONT).pack(side="left", padx=2)

        t_row = ctk.CTkFrame(self.rep_sec, fg_color="transparent")
        t_row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(t_row, text="ВРЕМЯ:", font=NORMAL_FONT, text_color="#FF8C00").pack(side="left")
        time_part = self.task.get("time", "09:00").split(":")
        self.rh, self.rm = ctk.StringVar(value=time_part[0]), ctk.StringVar(value=time_part[1])
        ctk.CTkComboBox(t_row, values=[f"{i:02d}" for i in range(24)], width=80, variable=self.rh, font=NORMAL_FONT).pack(side="left", padx=5)
        ctk.CTkComboBox(t_row, values=[f"{i:02d}" for i in range(0,60,5)], width=80, variable=self.rm, font=NORMAL_FONT).pack(side="left", padx=5)

        self.spec_sec = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.spec_cal = Calendar(self.spec_sec, selectmode='day', locale='ru_RU')
        self.spec_cal.pack(pady=10)
        self.spec_cal.bind("<<CalendarSelected>>", self.on_spec_date_click)
        self.spec_list = ctk.CTkScrollableFrame(self.spec_sec, height=200)
        self.spec_list.pack(fill="x", pady=10)

        self.once_sec = ctk.CTkFrame(self.content_container, fg_color="transparent")
        ctk.CTkLabel(self.once_sec, text="ВЫБЕРИТЕ ДАТУ ДЛЯ РАЗОВОГО ПОВТОРА:", font=NORMAL_FONT, text_color="#FF8C00").pack(anchor="w", pady=(0, 10))
        self.once_cal = Calendar(self.once_sec, selectmode='day', locale='ru_RU')
        self.once_cal.pack(pady=10)
        ot_row = ctk.CTkFrame(self.once_sec, fg_color="transparent")
        ot_row.pack(fill="x", pady=10)
        ctk.CTkLabel(ot_row, text="ВРЕМЯ:", font=NORMAL_FONT).pack(side="left")
        self.oh, self.om = ctk.StringVar(value="09"), ctk.StringVar(value="00")
        ctk.CTkComboBox(ot_row, values=[f"{i:02d}" for i in range(24)], width=80, variable=self.oh).pack(side="left", padx=5)
        ctk.CTkComboBox(ot_row, values=[f"{i:02d}" for i in range(0,60,5)], width=80, variable=self.om).pack(side="left", padx=5)

        self.update_mode_ui(); self.update_rep_logic_ui(); self.render_spec_list()
        self.save_btn = ctk.CTkButton(self, text="СОХРАНИТЬ", height=70, font=SUBHEADER_FONT, fg_color="#FF8C00", hover_color="#E67E00", command=self.save)
        self.save_btn.pack(fill="x", padx=30, pady=20)

    def open_icon_picker(self): IconPicker(self, self.set_icon)
    def set_icon(self, icon): self.selected_icon = icon; self.icon_btn.configure(text=icon)
    def on_spec_date_click(self, e):
        d = self.spec_cal.selection_get().strftime("%Y-%m-%d")
        if d in self.specific_dt_map: del self.specific_dt_map[d]
        else: self.specific_dt_map[d] = "09:00"
        self.render_spec_list()
    def render_spec_list(self):
        for c in self.spec_list.winfo_children(): c.destroy()
        for d, t in sorted(self.specific_dt_map.items()):
            r = ctk.CTkFrame(self.spec_list); r.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(r, text=d, font=NORMAL_FONT, width=120).pack(side="left")
            h, m = t.split(":"); hv, mv = ctk.StringVar(value=h), ctk.StringVar(value=m)
            def up(d=d, h=hv, m=mv): self.specific_dt_map[d] = f"{h.get()}:{m.get()}"
            ctk.CTkComboBox(r, values=[f"{i:02d}" for i in range(24)], width=70, variable=hv, command=lambda _: up()).pack(side="left", padx=2)
            ctk.CTkComboBox(r, values=[f"{i:02d}" for i in range(0,60,5)], width=70, variable=mv, command=lambda _: up()).pack(side="left", padx=2)
            ctk.CTkButton(r, text="УДАЛИТЬ", width=80, fg_color="red", command=lambda d=d: self.rem_d(d)).pack(side="right", padx=5)
    def rem_d(self, d): del self.specific_dt_map[d]; self.render_spec_list()
    def update_mode_ui(self):
        for s in [self.rep_sec, self.spec_sec, self.once_sec]: s.pack_forget()
        m = self.mode_var.get()
        if m == "repeat": self.rep_sec.pack(fill="both")
        elif m == "specific": self.spec_sec.pack(fill="both")
        elif m == "once": self.once_sec.pack(fill="both")
    def update_rep_logic_ui(self):
        # Сначала скрываем всё
        self.int_frame.pack_forget()
        self.week_frame.pack_forget()
        
        # Показываем только нужное
        current_rtype = self.rtype_var.get()
        if current_rtype == "interval":
            self.int_frame.pack(fill="x", pady=10) # Добавили небольшой отступ для красоты
        elif current_rtype == "weekly":
            self.week_frame.pack(fill="x", pady=10)
        # Если выбрано "daily" (Ежедневно), ничего не пакуем, 
        # и блок времени поднимется выше к кнопкам выбора режима.
    def save(self):
        try:
            cat_name = f"{self.selected_icon} {self.cat_entry.get().strip().upper()}"
            m = self.mode_var.get()
            d = {
                "id": self.task.get("id") or str(uuid.uuid4()), 
                "name": self.name_entry.get().upper(), 
                "category": cat_name, 
                "description": self.desc_text.get("1.0", "end").strip(), 
                "mode": m, 
                "enabled": True,
                "sound_type": self.sound_var.get()
            }
            if m == "repeat": d.update({"repeat_type": self.rtype_var.get(), "repeat_interval": int(self.int_entry.get() or 1), "repeat_days": [i for i, v in self.d_vars.items() if v.get()], "time": f"{self.rh.get()}:{self.rm.get()}", "date_start": self.rep_cal.selection_get().strftime("%Y-%m-%d")})
            elif m == "specific": d["specific_dt_map"] = self.specific_dt_map
            elif m == "once": d.update({"time": f"{self.oh.get()}:{self.om.get()}", "date_start": self.once_cal.selection_get().strftime("%Y-%m-%d")})
            self.on_save_callback(d); self.destroy()
        except Exception as e: print(f"Error saving: {e}")

class TaskItem(ctk.CTkFrame):
    def __init__(self, master, task, on_edit, on_delete, **kwargs):
        super().__init__(master, **kwargs)
        self.task = task
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.expanded = False
        self.setup_ui()

    def setup_ui(self):
        # --- ШАПКА КАРТОЧКИ ---
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=10, pady=5)
        self.header.bind("<Button-1>", lambda e: self.toggle())
        
        self.expand_btn = ctk.CTkLabel(self.header, text="+", font=("Consolas", 20, "bold"), text_color="#FF8C00", width=30)
        self.expand_btn.pack(side="left", padx=5)
        self.expand_btn.bind("<Button-1>", lambda e: self.toggle())
        
        self.name_lbl = ctk.CTkLabel(self.header, text=self.task["name"], font=BRUTAL_FONT, text_color="#FF8C00")
        self.name_lbl.pack(side="left", padx=10)
        self.name_lbl.bind("<Button-1>", lambda e: self.toggle())
        
        # Ближайшее время в шапке
        next_d = get_next_run_date(self.task)
        display_date = format_date_display(next_d)
        t_val = self.task.get('time', '--:--')
        if self.task.get("mode") == "specific" and next_d in self.task.get("specific_dt_map", {}):
            t_val = self.task["specific_dt_map"][next_d]

        self.time_lbl = ctk.CTkLabel(self.header, text=f"📅 {display_date} ⏰ {t_val}", font=NORMAL_FONT)
        self.time_lbl.pack(side="left", padx=20)
        
        actions = ctk.CTkFrame(self.header, fg_color="transparent")
        actions.pack(side="right", padx=0)
        self.edit_btn = ctk.CTkButton(actions, text="✏️", width=24, height=24, font=("Consolas", 10), fg_color="transparent", text_color=("#000000", "#FFFFFF"), hover_color=("#FFFFFF", "#444444"), command=lambda: self.on_edit(self.task))
        self.edit_btn.pack(side="left", padx=1)
        self.rem_btn = ctk.CTkButton(actions, text="❌", width=24, height=24, font=("Consolas", 10), fg_color="transparent", text_color=("#000000", "#FFFFFF"), hover_color=("#FFFFFF", "#444444"), command=lambda: self.on_delete(self.task))
        self.rem_btn.pack(side="left", padx=1)

        # --- ДЕТАЛЬНАЯ ИНФОРМАЦИЯ (РАЗВОРАЧИВАЕТСЯ) ---
        self.details = ctk.CTkFrame(self, fg_color="transparent")
        
        # Собираем детальную строку
        m_map = {"repeat": "ЦИКЛИЧНЫЙ ПОВТОР", "specific": "РУЧНОЙ ВЫБОР ДАТ", "once": "РАЗОВОЕ УВЕДОМЛЕНИЕ"}
        mode_str = m_map.get(self.task.get('mode'), 'НЕИЗВЕСТНО')
        
        info = f"РЕЖИМ: {mode_str}\n"
        
        # Детализация в зависимости от режима
        mode = self.task.get("mode")
        
        if mode == "specific":
            info += "СПИСОК УСТАНОВЛЕННЫХ ДАТ:\n"
            dt_map = self.task.get("specific_dt_map", {})
            if dt_map:
                # Сортируем даты по порядку
                for d_str in sorted(dt_map.keys()):
                    info += f"  • {d_str} в {dt_map[d_str]}\n"
            else:
                info += "  (даты не выбраны)\n"

        elif mode == "repeat":
            rt = self.task.get("repeat_type")
            if rt == "daily":
                info += f"ПОВТОР: КАЖДЫЙ ДЕНЬ В {self.task.get('time')}\n"
            elif rt == "interval":
                info += f"ПОВТОР: КАЖДЫЕ {self.task.get('repeat_interval')} ДН. В {self.task.get('time')}\n"
            elif rt == "weekly":
                days_map = {0:"ПН", 1:"ВТ", 2:"СР", 3:"ЧТ", 4:"ПТ", 5:"СБ", 6:"ВС"}
                selected_days = [days_map[d] for d in sorted(self.task.get("repeat_days", []))]
                days_str = ", ".join(selected_days) if selected_days else "НЕ ВЫБРАНЫ"
                info += f"ПОВТОР ПО ДНЯМ: {days_str}\n"
                info += f"ВРЕМЯ: {self.task.get('time')}\n"
            info += f"ДАТА СТАРТА: {self.task.get('date_start')}\n"

        elif mode == "once":
            info += f"ДАТА: {self.task.get('date_start')} В {self.task.get('time')}\n"

        if self.task.get("description"):
            info += f"\nОПИСАНИЕ:\n{self.task['description'].upper()}"

        # Создаем текстовый блок с деталями
        self.info_lbl = ctk.CTkLabel(
            self.details, 
            text=info, 
            font=NORMAL_FONT, 
            justify="left", 
            anchor="w",
            # ("#000000", "#FFFFFF") сделает текст черным в светлой теме и белым в темной
            text_color=("#000000", "#FFFFFF") 
        )
        self.info_lbl.pack(fill="both", padx=60, pady=(0, 15))

    def toggle(self):
        if self.expanded:
            self.details.pack_forget()
            self.expand_btn.configure(text="+")
        else:
            self.details.pack(fill="both")
            self.expand_btn.configure(text="-")
        self.expanded = not self.expanded
class CategoryGroup(ctk.CTkFrame):
    def __init__(self, master, cat_name, tasks, on_edit, on_delete, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        h = ctk.CTkFrame(self, corner_radius=12, border_width=2, border_color="#FF8C00")
        h.pack(fill="x", pady=5)
        ctk.CTkLabel(h, text=cat_name.upper(), font=SUBHEADER_FONT, text_color="#FF8C00").pack(side="left", padx=20, pady=10)
        
        # Сортируем задачи внутри категории по ближайшей дате
        sorted_tasks = sorted(tasks, key=lambda x: get_next_run_date(x))
        for t in sorted_tasks:
            TaskItem(self, t, on_edit, on_delete, corner_radius=10, border_width=1, border_color="#DDDDDD").pack(fill="x", pady=3, padx=15)

# (StopwatchPage, TimerPage, SettingsPage остаются без изменений...)
class StopwatchPage(ctk.CTkFrame):
    def __init__(self, master, storage, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.storage = storage; self.running = False; self.start_t = None; self.elapsed = timedelta(); self.setup_ui()
    def setup_ui(self):
        ctk.CTkLabel(self, text="СЕКУНДОМЕР", font=HEADER_FONT, text_color="#FF8C00").pack(pady=30)
        self.outer = ctk.CTkFrame(self, corner_radius=100, border_width=5, border_color="#FF8C00", width=420, height=220); self.outer.pack(pady=10); self.outer.pack_propagate(False)
        self.lbl = ctk.CTkLabel(self.outer, text="00:00:00.0", font=("Consolas", 60, "bold"), text_color="#FF8C00"); self.lbl.place(relx=0.5, rely=0.5, anchor="center")
        f = ctk.CTkFrame(self, fg_color="transparent"); f.pack(pady=30)
        btn_style = {"width":180, "height":65, "font":BTN_LARGE_FONT, "fg_color":"#FF8C00", "hover_color":("#FFFFFF", "#EEEEEE")}
        self.btn = ctk.CTkButton(f, text="ПУСК", command=self.toggle, **btn_style); self.btn.pack(side="left", padx=10)
        ctk.CTkButton(f, text="ЗАПИСЬ", command=self.save_record, **btn_style).pack(side="left", padx=10)
        ctk.CTkButton(f, text="СБРОС", command=self.reset, width=160, height=65, font=BTN_LARGE_FONT, fg_color="#666666", hover_color=("#FFFFFF", "#EEEEEE")).pack(side="left", padx=10)
        ctk.CTkLabel(self, text="ИСТОРИЯ:", font=NORMAL_FONT, text_color="#FF8C00").pack(pady=5)
        self.rec_area = ctk.CTkScrollableFrame(self, height=280, width=550); self.rec_area.pack(pady=5); self.load_recs()
    def toggle(self):
        if not self.running: self.running = True; self.start_t = datetime.now() - self.elapsed; self.btn.configure(text="СТОП", fg_color="red"); self.update_c()
        else: self.running = False; self.btn.configure(text="ПУСК", fg_color="#FF8C00")
    def update_c(self):
        if self.running:
            self.elapsed = datetime.now() - self.start_t; ts = int(self.elapsed.total_seconds()); h, r = divmod(ts, 3600); m, s = divmod(r, 60); ms = int(self.elapsed.microseconds / 100000)
            self.lbl.configure(text=f"{h:02d}:{m:02d}:{s:02d}.{ms}"); self.after(50, self.update_c)
    def save_record(self):
        name = sd.askstring("Запись", "Введите название записи:", initialvalue="Рекорд")
        if name:
            s = self.storage.load_settings(); rs = s.get("stopwatch_records", []); rs.insert(0, {"id":str(uuid.uuid4()), "name":name, "time":self.lbl.cget("text"), "date":datetime.now().strftime("%d.%m %H:%M")})
            s["stopwatch_records"] = rs[:20]; self.storage.save_settings(s); self.load_recs()
    def load_recs(self):
        for c in self.rec_area.winfo_children(): c.destroy()
        s = self.storage.load_settings()
        for r in s.get("stopwatch_records", []):
            f = ctk.CTkFrame(self.rec_area); f.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(f, text=f"{r['name']}: {r['time']} ({r['date']})", font=NORMAL_FONT, anchor="w").pack(side="left", padx=20, fill="x", expand=True)
            ctk.CTkButton(f, text="✏️", width=30, fg_color="transparent", text_color="gray", command=lambda x=r: self.edit_rec(x)).pack(side="right")
            ctk.CTkButton(f, text="🗑", width=30, fg_color="transparent", text_color="red", command=lambda x=r: self.del_rec(x)).pack(side="right")
    def edit_rec(self, r):
        nn = sd.askstring("Редактировать", "Новое название:", initialvalue=r["name"])
        if nn:
            s = self.storage.load_settings(); rs = s["stopwatch_records"]
            for i in rs: 
                if i["id"] == r["id"]: i["name"] = nn
            self.storage.save_settings(s); self.load_recs()
    def del_rec(self, r):
        s = self.storage.load_settings(); rs = s["stopwatch_records"]
        s["stopwatch_records"] = [i for i in rs if i["id"] != r["id"]]; self.storage.save_settings(s); self.load_recs()
    def reset(self): self.running = False; self.elapsed = timedelta(); self.lbl.configure(text="00:00:00.0"); self.btn.configure(text="ПУСК", fg_color="#FF8C00")

class TimerPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.rem = 0; self.running = False; self.setup_ui()
    def setup_ui(self):
        ctk.CTkLabel(self, text="ТАЙМЕР", font=HEADER_FONT, text_color="#FF8C00").pack(pady=20)
        tf = ctk.CTkFrame(self, fg_color="transparent"); tf.pack(pady=10)
        for i in range(1, 6): 
            ctk.CTkButton(tf, text=f"{i} МИН", width=80, font=NORMAL_FONT, fg_color="#FF8C00", command=lambda m=i: self.set_tm(m)).pack(side="left", padx=5)
        ib = ctk.CTkFrame(self, fg_color="transparent"); ib.pack(pady=10)
        self.h_in = ctk.CTkEntry(ib, width=80, font=SUBHEADER_FONT, placeholder_text="00", justify="center"); self.h_in.pack(side="left", padx=5)
        self.m_in = ctk.CTkEntry(ib, width=80, font=SUBHEADER_FONT, placeholder_text="00", justify="center"); self.m_in.pack(side="left", padx=5)
        self.s_in = ctk.CTkEntry(ib, width=80, font=SUBHEADER_FONT, placeholder_text="00", justify="center"); self.s_in.pack(side="left", padx=5)
        
        # --- TIMER SOUND SELECTION ---
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.pack(pady=10)
        ctk.CTkLabel(sf, text="ЗВУК ТАЙМЕРА:", font=NORMAL_FONT, text_color="#FF8C00").pack(side="left", padx=10)
        self.timer_sound_var = ctk.StringVar(value="quiet")
        ctk.CTkRadioButton(sf, text="БЕЗ ЗВУКА", variable=self.timer_sound_var, value="none", font=NORMAL_FONT, fg_color="#FF8C00").pack(side="left", padx=5)
        ctk.CTkRadioButton(sf, text="СТАНДАРТ", variable=self.timer_sound_var, value="default", font=NORMAL_FONT, fg_color="#FF8C00").pack(side="left", padx=5)
        ctk.CTkRadioButton(sf, text="ТИХИЙ", variable=self.timer_sound_var, value="quiet", font=NORMAL_FONT, fg_color="#FF8C00").pack(side="left", padx=5)
        ctk.CTkRadioButton(sf, text="ГРОМКИЙ", variable=self.timer_sound_var, value="loud", font=NORMAL_FONT, fg_color="#FF8C00").pack(side="left", padx=5)
        
        self.outer = ctk.CTkFrame(self, corner_radius=100, border_width=5, border_color="#FF8C00", width=420, height=220); self.outer.pack(pady=10); self.outer.pack_propagate(False)
        self.lbl = ctk.CTkLabel(self.outer, text="00:05:00", font=("Consolas", 80, "bold"), text_color="#FF8C00"); self.lbl.place(relx=0.5, rely=0.5, anchor="center")
        f = ctk.CTkFrame(self, fg_color="transparent"); f.pack(pady=30)
        btn_hl_style = {"width":240, "height":70, "font":BTN_LARGE_FONT, "fg_color":"#FF8C00", "hover_color":("#FFFFFF", "#EEEEEE")}
        self.btn = ctk.CTkButton(f, text="СТАРТ", command=self.start, **btn_hl_style); self.btn.pack(side="left", padx=10)
        ctk.CTkButton(f, text="СБРОС", width=140, height=70, font=BTN_LARGE_FONT, fg_color="#666666", hover_color=("#FFFFFF", "#EEEEEE"), command=self.reset).pack(side="left", padx=10)
    def set_tm(self, mins): self.reset(); self.rem = mins * 60; h, r = divmod(self.rem, 3600); m, s = divmod(r, 60); self.lbl.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
    def start(self):
        if not self.running:
            if self.rem <= 0: h = int(self.h_in.get() or 0); m = int(self.m_in.get() or 0); s = int(self.s_in.get() or 0); self.rem = h*3600 + m*60 + s
            if self.rem > 0: self.running = True; self.btn.configure(text="ПАУЗА", fg_color="red"); self.tick()
        else: self.running = False; self.btn.configure(text="ПУСК", fg_color="#FF8C00")
    def tick(self):
        if self.running and self.rem > 0:
            h, r = divmod(self.rem, 3600); m, s = divmod(r, 60); self.lbl.configure(text=f"{h:02d}:{m:02d}:{s:02d}"); self.rem -= 1; self.after(1000, self.tick)
        elif self.rem == 0 and self.running: self.lbl.configure(text="ВРЕМЯ!"); play_alert_sound(self.timer_sound_var.get()); self.running = False; self.btn.configure(text="СТАРТ")
    def reset(self): 
        self.running = False
        self.rem = 0
        self.lbl.configure(text="00:05:00")
        self.btn.configure(text="СТАРТ", fg_color="#FF8C00")
        stop_alert_sound()

class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, storage, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.storage = storage; self.settings = storage.load_settings(); self.setup_ui()
    def setup_ui(self):
        ctk.CTkLabel(self, text="НАСТРОЙКИ", font=HEADER_FONT, text_color="#FF8C00").pack(pady=40)
        f = ctk.CTkFrame(self, corner_radius=15, border_width=2, border_color="#FF8C00"); f.pack(padx=100, fill="x", pady=20)
        ctk.CTkLabel(f, text="ТЕМА:", font=NORMAL_FONT, text_color="#FF8C00").pack(pady=(20,5), padx=30, anchor="w")
        self.theme_var = ctk.StringVar(value=self.settings.get("theme", "light"))
        theme_btn = ctk.CTkSegmentedButton(f, values=["light", "dark"], variable=self.theme_var, command=self.change_theme, font=NORMAL_FONT, fg_color="#EEEEEE", selected_color="#FF8C00"); theme_btn.pack(pady=10, padx=30, fill="x")
        self.sound_var = ctk.BooleanVar(value=self.settings.get("notification_sound", True))
        ctk.CTkCheckBox(f, text="ЗВУК", variable=self.sound_var, command=self.save, font=NORMAL_FONT, fg_color="#FF8C00").pack(pady=20, padx=30, anchor="w")
        ctk.CTkLabel(self, text="АВТОР: СВИРИДОВ АЛЕКСЕЙ", font=NORMAL_FONT, text_color="#999999").pack(side="bottom", pady=20)
    def change_theme(self, theme): ctk.set_appearance_mode(theme); self.save()
    def save(self): self.settings["theme"] = self.theme_var.get(); self.settings["notification_sound"] = self.sound_var.get(); self.storage.save_settings(self.settings)

class AppUI(ctk.CTk):
    def __init__(self, on_close_callback):
        super().__init__()
        self.storage = Storage(); self.settings = self.storage.load_settings(); ctk.set_appearance_mode(self.settings.get("theme", "light"))
        self.on_close_callback = on_close_callback; self.title("PancirTimer 4.0 Pro"); self.geometry("1200x900")
        self.setup_ui(); self.protocol("WM_DELETE_WINDOW", self.on_close)
    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=340, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        # --- LOGO IMAGE ---
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(300, 150))
                self.logo_label = ctk.CTkLabel(self.sidebar, image=logo_ctk, text="")
                self.logo_label.pack(fill="x", pady=(10, 10))
            else:
                ctk.CTkLabel(self.sidebar, text="PancirTimer", font=LOGO_FONT, text_color="#FF8C00").pack(pady=15)
        except Exception as e:
            print(f"Error loading logo: {e}")
            ctk.CTkLabel(self.sidebar, text="PancirTimer", font=LOGO_FONT, text_color="#FF8C00").pack(pady=15)

        self.nav = {}
        items = [("УВЕДОМЛЕНИЯ", "tasks", "📅"), ("СЕКУНДОМЕР", "stopwatch", "⏱"), ("ТАЙМЕР", "timer", "⏳"), ("НАСТРОЙКИ", "settings", "⚙")]
        for t, p, i in items:
            b = ctk.CTkButton(self.sidebar, text=f"{i}  {t}", font=BRUTAL_FONT, fg_color="transparent", text_color=("#000000", "#FF8C00"), anchor="w", height=70, hover_color=("#D3D3D3", "#333333"), command=lambda x=p: self.show_page(x))
            b.pack(fill="x", padx=15, pady=5); self.nav[p] = b
        self.container = ctk.CTkFrame(self, fg_color="transparent"); self.container.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        self.pages = {"tasks": self.create_tasks_page(), "stopwatch": StopwatchPage(self.container, self.storage), "timer": TimerPage(self.container), "settings": SettingsPage(self.container, self.storage)}
        self.show_page("tasks")
        ctk.CTkLabel(self.sidebar, text="АВТОР: СВИРИДОВ АЛЕКСЕЙ", font=SMALL_FONT, text_color="#666666").pack(side="bottom", pady=20)
    def create_tasks_page(self):
        p = ctk.CTkFrame(self.container, fg_color="transparent"); h = ctk.CTkFrame(p, fg_color="transparent"); h.pack(fill="x", pady=20)
        ctk.CTkLabel(h, text="ЗАДАЧИ", font=HEADER_FONT, text_color="#FF8C00").pack(side="left"); ctk.CTkButton(h, text="+ СОЗДАТЬ", font=SUBHEADER_FONT, fg_color="#FF8C00", command=self.open_dialog).pack(side="right")
        self.list_area = ctk.CTkScrollableFrame(p, fg_color="transparent"); self.list_area.pack(fill="both", expand=True); self.refresh(); return p
    def show_page(self, name):
        for b in self.nav.values(): b.configure(fg_color="transparent")
        self.nav[name].configure(fg_color=("#EEEEEE", "#333333")); [page.pack_forget() for page in self.pages.values()]; self.pages[name].pack(fill="both", expand=True)
    
    def refresh(self):
        [c.destroy() for c in self.list_area.winfo_children()]
        ts = self.storage.load_tasks()
        
        # Группируем задачи по категориям
        groups = {}
        for t in ts:
            cat = t.get("category", "📌 ОБЩЕЕ")
            groups.setdefault(cat, []).append(t)
            
        # --- СОРТИРОВКА КАТЕГОРИЙ ---
        # Вычисляем минимальную дату выполнения для каждой категории
        cat_priority = []
        for cat, tasks in groups.items():
            min_date = min([get_next_run_date(t) for t in tasks])
            cat_priority.append((cat, min_date, tasks))
        
        # Сортируем список категорий по этой минимальной дате
        cat_priority.sort(key=lambda x: x[1])
        
        # Рендерим отсортированные категории
        for cat, _, t_list in cat_priority:
            CategoryGroup(self.list_area, cat, t_list, self.open_dialog, self.delete_task).pack(fill="x", pady=10)

    def open_dialog(self, task=None): TaskDialog(self, self.save_task, self.storage, task)
    def save_task(self, data): ts = self.storage.load_tasks(); ts = [t for t in ts if t["id"] != data["id"]]; ts.append(data); self.storage.save_tasks(ts); self.refresh()
    def delete_task(self, task): ts = self.storage.load_tasks(); ts = [t for t in ts if t["id"] != task["id"]]; self.storage.save_tasks(ts); self.refresh()
    def on_close(self): self.on_close_callback()
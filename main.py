import threading
import time
import os
import sys
from datetime import datetime
import pystray
from PIL import Image, ImageDraw
from gui import AppUI
from storage import Storage
from notifier import send_notification, play_alert_sound, stop_alert_sound
import customtkinter as ctk
import tkinter.messagebox as mb

class PancirTimerApp:
    def __init__(self):
        self.storage = Storage()
        self.gui = None
        self.stop_event = threading.Event()
        self.tray_icon = None
        self.icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if not os.path.exists(self.icon_path): self.create_default_icon()
        self.setup_tray()
        self.check_thread = threading.Thread(target=self.notification_loop, daemon=True)
        self.check_thread.start()

    def create_default_icon(self):
        w, h = 64, 64; img = Image.new('RGB', (w, h), color='#FFFFFF'); dc = ImageDraw.Draw(img)
        dc.ellipse([10, 10, 54, 54], fill='#FF8C00', outline='#E67E00'); img.save(self.icon_path)

    def should_notify(self, task, now):
        if not task.get("enabled", True): return False
        now_minute_str = now.strftime("%Y-%m-%d %H:%M")
        if task.get("last_notified") == now_minute_str: return False
        
        current_time_str = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        mode = task.get("mode", "repeat")

        if mode == "once":
            if task.get("date_start") == today_str and task.get("time") == current_time_str:
                return True
        elif mode == "specific":
            dt_map = task.get("specific_dt_map", {})
            if today_str in dt_map: return dt_map[today_str] == current_time_str
        elif mode == "repeat":
            if task.get("time") != current_time_str: return False
            rt = task.get("repeat_type", "daily")
            if rt == "daily": return True
            if rt == "weekly": return now.weekday() in task.get("repeat_days", [])
            if rt == "interval":
                start_date = datetime.strptime(task.get("date_start", today_str), "%Y-%m-%d").date()
                delta = (now.date() - start_date).days
                return delta >= 0 and delta % task.get("repeat_interval", 1) == 0
        return False

    def notification_loop(self):
        while not self.stop_event.is_set():
            now = datetime.now()
            tasks = self.storage.load_tasks()
            updated = False
            to_del = []
        
            for task in tasks:
                if self.should_notify(task, now):
                    # 1. Сначала запускаем звук
                    play_alert_sound(task.get("sound_type", "quiet"))
                    
                    # 2. Отправляем уведомление и передаем функцию остановки звука
                    send_notification(
                        title=f"PancirTimer: {task['name']}",
                        message=f"Категория: {task.get('category', 'Общее')}\n{task.get('description', '')}",
                        sound_type=task.get("sound_type", "quiet"),
                        on_dismissed_callback=stop_alert_sound
                    )
                    
                    task["last_notified"] = now.strftime("%Y-%m-%d %H:%M")
                    if task.get("mode") == "once": 
                        to_del.append(task["id"])
                    updated = True
            
            if to_del: 
                tasks = [t for t in tasks if t["id"] not in to_del]
            
            if updated:
                self.storage.save_tasks(tasks)
                if self.gui: 
                    self.gui.after(0, self.gui.refresh)
                    
            time.sleep(20)

    def setup_tray(self):
        image = Image.open(self.icon_path)
        menu = pystray.Menu(pystray.MenuItem("Открыть PancirTimer", self.safe_show_gui), pystray.MenuItem("Сводка на сегодня", self.show_daily_summary), pystray.Menu.SEPARATOR, pystray.MenuItem("Выход", self.exit_app))
        self.tray_icon = pystray.Icon("PancirTimer", image, "PancirTimer 4.0", menu)

    def show_daily_summary(self, icon, item):
        tasks = self.storage.load_tasks(); today_str = datetime.now().strftime("%Y-%m-%d"); now = datetime.now(); summary = []
        for t in tasks:
            is_today = False
            if t.get("mode") == "once" and t.get("date_start") == today_str: is_today = True
            elif t.get("mode") == "specific" and today_str in t.get("specific_dt_map", {}): is_today = True
            elif t.get("mode") == "repeat":
                rt = t.get("repeat_type", "daily")
                if rt == "daily": is_today = True
                elif rt == "weekly" and now.weekday() in t.get("repeat_days", []): is_today = True
                elif rt == "interval":
                    start = datetime.strptime(t.get("date_start", today_str), "%Y-%m-%d").date()
                    if (now.date() - start).days % t.get("repeat_interval", 1) == 0: is_today = True
            if is_today:
                time_val = t.get("time") if t.get("mode") != "specific" else t.get("specific_dt_map", {}).get(today_str)
                summary.append(f"• {time_val} — {t['name']}")
        msg = "\n".join(summary) if summary else "На сегодня задач нет."
        root = mb.tk.Tk(); root.withdraw(); mb.showinfo("План на сегодня", msg); root.destroy()

    def safe_show_gui(self, icon=None, item=None):
        if self.gui: self.gui.after(0, self.gui.deiconify); self.gui.after(0, self.gui.focus_force)
    def hide_gui(self):
        if self.gui: self.gui.withdraw()
    def exit_app(self, icon, item):
        self.stop_event.set()
        self.tray_icon.stop()
        if self.gui:
            self.gui.after(0, self.gui.destroy)
        sys.exit(0)
    def run(self):
        # Запускаем иконку в трее в отдельном потоке
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        # Инициализируем и запускаем главное окно
        self.gui = AppUI(on_close_callback=self.hide_gui)
        self.gui.mainloop()

if __name__ == "__main__":
    app = PancirTimerApp(); app.run()

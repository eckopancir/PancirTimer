import json
import os
import sys
import uuid
from datetime import datetime

class Storage:
    def __init__(self, filename="tasks.json"):
        # Если запущено как exe, берем путь до exe, иначе путь до скрипта
        if getattr(sys, 'frozen', False):
            self.dir = os.path.dirname(sys.executable)
        else:
            self.dir = os.path.dirname(os.path.abspath(__file__))
            
        self.filename = os.path.join(self.dir, filename)
        self.settings_file = os.path.join(self.dir, "settings.json")
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(self.filename):
            self.save_tasks([])
        if not os.path.exists(self.settings_file):
            self.save_settings({
                "theme": "light",
                "accent_color": "#FF8C00",
                "notification_sound": True,
                "categories": [
                    {"name": "Таблетки", "icon": "💊"},
                    {"name": "Тренировки", "icon": "💪"},
                    {"name": "Сериалы", "icon": "🎬"},
                    {"name": "Общее", "icon": "📌"}
                ]
            })

    def load_tasks(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []

    def save_tasks(self, tasks):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)

    def load_settings(self):
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}

    def save_settings(self, settings):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

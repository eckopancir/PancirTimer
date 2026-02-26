from winotify import Notification, audio
import os
import winsound
import threading
import time

try:
    import pygame.mixer as mixer
    pygame_available = True
except ImportError:
    pygame_available = False

def stop_alert_sound():
    """Мгновенно останавливает любое текущее воспроизведение музыки."""
    try:
        if pygame_available and mixer.get_init():
            mixer.music.stop()
    except Exception as e:
        print(f"Ошибка при остановке звука: {e}")

def send_notification(title, message, sound_type="Reminder", on_dismissed_callback=None):
    """Отправляет уведомление Windows. Параметр on_dismissed_callback нужен для стопа звука."""
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    
    sound_map = {
        "Reminder": "ms-winsoundevent:Notification.Reminder",
        "Alarm": "ms-winsoundevent:Notification.Looping.Alarm",
        "Mail": "ms-winsoundevent:Notification.Mail",
        "SMS": "ms-winsoundevent:Notification.SMS"
    }
    
    toast = Notification(
        app_id="PancirTimer",
        title=title,
        msg=message,
        duration="long",
        icon=icon_path if os.path.exists(icon_path) else None
    )
    
    # Привязываем действие на закрытие уведомления (задачу 2)
    if on_dismissed_callback:
        toast.on_dismissed = on_dismissed_callback
    
    # Логика выбора звука:
    # 1. Если "none" или играем MP3 (quiet/loud), отключаем звук самого уведомления
    if sound_type in ["none", "quiet", "loud"]:
        toast.set_audio(audio.Silent, loop=False)
    # 2. Если "default", используем стандартный звук Windows
    elif sound_type == "default":
        toast.set_audio(audio.Default, loop=False)
    # 3. Иначе ищем в карте или берем Reminder
    else:
        chosen_sound = sound_map.get(sound_type, "ms-winsoundevent:Notification.Reminder")
        toast.set_audio(chosen_sound, loop=False)
    
    try:
        toast.show()
    except Exception as e:
        print(f"Ошибка уведомления: {e}")

def play_alert_sound(sound_type="quiet"):
    """Запускает проигрывание MP3 в фоновом потоке."""
    # Если звук не нужен или выбран стандартный звук Windows, ничего не играем через pygame
    if sound_type in ["none", "default"]:
        return

    def _play():
        try:
            if not pygame_available:
                for _ in range(3): winsound.Beep(1000, 500)
                return

            file_map = {"quiet": "quiet.mp3", "loud": "loud.mp3"}
            sound_file = file_map.get(sound_type, "quiet.mp3")
            assets_dir = os.path.join(os.path.dirname(__file__), "assets")
            sound_path = os.path.join(assets_dir, sound_file)
            
            if not os.path.exists(sound_path):
                for _ in range(3): winsound.Beep(1000, 500)
                return

            if not mixer.get_init():
                mixer.init()
            
            mixer.music.load(sound_path)
            mixer.music.play()
            
            # Важно: цикл работает пока музыка играет. 
            # Как только вызовется mixer.music.stop(), get_busy() станет False.
            while mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error playing sound: {e}")

    threading.Thread(target=_play, daemon=True).start()

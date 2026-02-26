import os
import sys
import winreg as reg

def add_to_startup():
    # Get path to the main.py or the executable if compiled
    # For now, we assume it's running via python
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    # If it's a .py file, we need to run it with pythonw (no console)
    python_path = sys.executable.replace("python.exe", "pythonw.exe")
    cmd = f'"{python_path}" "{app_path}"'
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(key, "PillReminder", 0, reg.REG_SZ, cmd)
        reg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error adding to startup: {e}")
        return False

def remove_from_startup():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
        reg.DeleteValue(key, "PillReminder")
        reg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True # Already removed
    except Exception as e:
        print(f"Error removing from startup: {e}")
        return False

if __name__ == "__main__":
    # Test script
    add_to_startup()

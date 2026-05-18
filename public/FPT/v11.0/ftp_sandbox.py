import subprocess
import sys
import time
import re
import os
import ctypes
from ftp_utils import COLORS, progress_bar, get_key

def run_in_sandbox(filename, timeout=10):
    print(f"\n{COLORS['ORANGE']}Запуск '{filename}' в изолированной песочнице... (таймаут {timeout}с){COLORS['RESET']}")
    progress_bar(COLORS['ORANGE'], COLORS['GREEN'], 1.0)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        
        print(f"\n{COLORS['GREEN']}--- РЕЗУЛЬТАТ ВЫПОЛНЕНИЯ ({duration:.2f} сек) ---{COLORS['RESET']}")
        
        if result.stdout:
            print(f"Вывод (stdout):\n{COLORS['RESET']}{result.stdout.strip()}")
        else:
            print(f"{COLORS['RESET']}Вывод (stdout): [Пусто]")
            
        if result.stderr:
            print(f"\n{COLORS['RED']}Ошибки во время работы (stderr):\n{result.stderr.strip()}{COLORS['RESET']}")
            
            # --- НОВАЯ МАГИЯ: Авто-установка библиотек в отдельном CMD (от Админа) ---
            match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", result.stderr)
            if match:
                module_name = match.group(1)
                print(f"\n{COLORS['RED']}Обнаружен пропущенный модуль!{COLORS['RESET']} Хотите, чтобы FTP попробовала установить его автоматически через {COLORS['ORANGE']}pip install {module_name}{COLORS['RESET']}? {COLORS['BLUE']}[Y/N]{COLORS['RESET']}")
                
                while True:
                    ans = get_key()
                    if ans in ('Y', 'N'):
                        break
                        
                if ans == 'Y':
                    print(f"\n{COLORS['ORANGE']}Запрашиваю права администратора для установки {module_name}...{COLORS['RESET']}")
                    
                    if os.name == 'nt': # Для Windows
                        # Параметры: выполняем pip install, делаем отступ (echo.) и просим нажать любую кнопку (pause)
                        cmd_params = f'/c ""{sys.executable}" -m pip install {module_name} & echo. & pause"'
                        
                        try:
                            # Вызов отдельного системного CMD с запросом прав Администратора (runas)
                            # Сама программа FTP при этом работает как обычный юзер!
                            shell_result = ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", cmd_params, None, 1)
                            
                            if shell_result > 32:
                                print(f"\n{COLORS['GREEN']}Команда успешно отправлена в новое окно с правами Администратора!{COLORS['RESET']}")
                                print(f"{COLORS['GREEN']}Пожалуйста, дождитесь завершения установки в том окне, а затем снова введите команду {COLORS['ORANGE']}run{COLORS['GREEN']}.{COLORS['RESET']}")
                            else:
                                print(f"\n{COLORS['RED']}Отказ в правах администратора или ошибка запуска.{COLORS['RESET']}")
                        except Exception as e:
                            print(f"\n{COLORS['RED']}Не удалось вызвать окно администратора: {e}{COLORS['RESET']}")
                    else:
                        # Для Linux/macOS используем sudo в той же консоли
                        pip_result = subprocess.run(["sudo", sys.executable, "-m", "pip", "install", module_name])
                        if pip_result.returncode == 0:
                            print(f"\n{COLORS['GREEN']}Модуль '{module_name}' успешно установлен! Теперь вы можете снова запустить файл через команду run.{COLORS['RESET']}")
                        else:
                            print(f"\n{COLORS['RED']}Не удалось установить модуль '{module_name}'.{COLORS['RESET']}")
                else:
                    print(f"\n{COLORS['ORANGE']}Автоматическая установка отменена.{COLORS['RESET']}")
            # -----------------------------------------------
            
        elif result.returncode != 0:
            print(f"\n{COLORS['RED']}Процесс завершился с кодом: {result.returncode}{COLORS['RESET']}")
        else:
            print(f"\n{COLORS['GREEN']}Программа успешно завершилась без Runtime-ошибок!{COLORS['RESET']}")
            
    except subprocess.TimeoutExpired:
        print(f"\n{COLORS['RED']}--- КРИТИЧЕСКАЯ ОШИБКА РАБОТЫ ---{COLORS['RESET']}")
        print(f"{COLORS['RED']}Программа зависла (превышен лимит в {timeout} сек). Обнаружен бесконечный цикл или блокировка!{COLORS['RESET']}")
    except Exception as e:
        print(f"\n{COLORS['RED']}Ошибка запуска песочницы: {e}{COLORS['RESET']}")
import subprocess
import sys
import time
from ftp_utils import COLORS, progress_bar

def run_in_sandbox(filename, timeout=10):
    print(f"\n{COLORS['ORANGE']}Запуск '{filename}' в изолированной песочнице... (таймаут {timeout}с){COLORS['RESET']}")
    progress_bar(COLORS['ORANGE'], COLORS['GREEN'], 1.0)
    
    start_time = time.time()
    try:
        # Запускаем скрипт как отдельный процесс
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
        elif result.returncode != 0:
            print(f"\n{COLORS['RED']}Процесс завершился с кодом: {result.returncode}{COLORS['RESET']}")
        else:
            print(f"\n{COLORS['GREEN']}Программа успешно завершилась без Runtime-ошибок!{COLORS['RESET']}")
            
    except subprocess.TimeoutExpired:
        print(f"\n{COLORS['RED']}--- КРИТИЧЕСКАЯ ОШИБКА РАБОТЫ ---{COLORS['RESET']}")
        print(f"{COLORS['RED']}Программа зависла (превышен лимит в {timeout} сек). Обнаружен бесконечный цикл или блокировка!{COLORS['RESET']}")
    except Exception as e:
        print(f"\n{COLORS['RED']}Ошибка запуска песочницы: {e}{COLORS['RESET']}")
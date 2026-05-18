import os
import urllib.request
import json
import traceback
import datetime
from ftp_utils import COLORS, get_key, clear_screen, progress_bar
from ftp_analyzer import analyze_and_fix
from ftp_sandbox import run_in_sandbox

CURRENT_VERSION = "v10.1"
FIREBASE_PROJECT_ID = "fix-this-python"
current_dir_files = []

def get_latest_version():
    """Получает последнюю версию программы из Firestore REST API"""
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/app_info/version"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('fields', {}).get('latest', {}).get('stringValue', CURRENT_VERSION)
    except Exception:
        # Если нет интернета или ошибка базы, считаем, что текущая версия актуальна
        return CURRENT_VERSION

def send_error_log(error_traceback):
    """Отправляет лог ошибки в базу Firestore"""
    print(f"\n{COLORS['ORANGE']}Отправка лога...{COLORS['RESET']}")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/error_logs"
    try:
        data = {
            "fields": {
                "timestamp": {"stringValue": datetime.datetime.utcnow().isoformat() + "Z"},
                "error": {"stringValue": error_traceback},
                "version": {"stringValue": CURRENT_VERSION}
            }
        }
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"{COLORS['GREEN']}Лог успешно отправлен! Спасибо за помощь в улучшении программы.{COLORS['RESET']}")
    except Exception as ex:
        print(f"{COLORS['RED']}Не удалось отправить лог. Возможно, блокировка или проблема с интернетом.{COLORS['RESET']}")

def update_dir_list():
    global current_dir_files
    current_dir_files = []
    try:
        items = sorted(os.listdir('.'))
        files = [f for f in items if os.path.isfile(f) and not f.startswith('.')]
        if 0 < len(files) <= 99:
            print(f"\n{COLORS['ORANGE']}Файлы в текущей директории:{COLORS['RESET']}")
            for i, f in enumerate(files):
                print(f"{i + 1}. {f}")
            current_dir_files = files
    except Exception as e:
        print(f"{COLORS['RED']}Ошибка чтения директории: {e}{COLORS['RESET']}")

def resolve_filename(arg):
    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(current_dir_files):
            return current_dir_files[idx]
        else:
            print(f"{COLORS['RED']}Ошибка: Файл с номером {arg} не найден.{COLORS['RESET']}")
            return None
    return arg

def cmd_check(arg):
    filename = resolve_filename(arg)
    if not filename: return
    if not os.path.exists(filename):
        print(f"{COLORS['RED']}Ошибка: Файл '{filename}' не найден.{COLORS['RESET']}")
        return

    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print("\nПодождите, идёт выявление ошибок...")
    progress_bar(COLORS['RED'], COLORS['GREEN'], 2.0)
    
    errors = analyze_and_fix(lines)
    if not errors:
        print(f"         {COLORS['GREEN']}Ошибок синтаксиса не выявлено!{COLORS['RESET']}\n")
        return

    print(f"         {COLORS['RED']}Найдено ошибок: {len(errors)}{COLORS['RESET']}")
    for err in errors:
        print(f"         Строка {err['idx'] + 1}: {COLORS['RED']}{err['original']}{COLORS['RESET']}")
    print("")

def cmd_fix(arg):
    filename = resolve_filename(arg)
    if not filename: return
    if not os.path.exists(filename):
        print(f"{COLORS['RED']}Ошибка: Файл '{filename}' не найден.{COLORS['RESET']}")
        return

    while True:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        original_lines = lines.copy()

        print("\nПодождите, идёт подготовка починки файла...")
        progress_bar(COLORS['RED'], COLORS['GREEN'], 1.5)

        print("\nПодождите, идёт выявление ошибок...")
        progress_bar(COLORS['RED'], COLORS['GREEN'], 2.0)
        
        errors = analyze_and_fix(lines)
        if not errors:
            print(f"         {COLORS['GREEN']}Ошибок синтаксиса не выявлено!{COLORS['RESET']}\n")
            return

        print("         Найдено:")
        for err in errors:
            print(f"         {err['idx'] + 1}. {err['original']}")

        print("\nПодождите, идёт поиск исправлений...")
        progress_bar(COLORS['GREEN'], COLORS['GREEN'], 2.0)
        print("         Найдено:")
        for err in errors:
            if err["auto"] and err["fixed"] != err["original"]:
                print(f"         {err['original']} > {COLORS['GREEN']}{err['fixed']}{COLORS['RESET']}")
            else:
                print(f"         {err['original']} > {COLORS['RED']}{err['fixed']} [ОШИБКА, НАЖМИТЕ 'E']{COLORS['RESET']}")

        action_cancelled = False
        while True:
            print("\nНажмите ENTER для подтверждения... E чтобы изменить исправление... ESC для отмены...")
            key = get_key()

            if key == 'ESC':
                print("\nВыбрано: Отмена. Исправление прервано.\n")
                action_cancelled = True
                break
            elif key == 'ENTER':
                print("\nВыбрано: \"Подтвердить\"...\n")
                break
            elif key == 'E':
                clear_screen()
                print("\nКакую строку изменить? (ESC для возврата):")
                for i, err in enumerate(errors):
                    color = COLORS['GREEN'] if err["auto"] else COLORS['RED']
                    print(f"         {i + 1}. {color}{err['fixed']}{COLORS['RESET']} (Было: {err['original']})")
                
                cwd = os.getcwd()
                choice = input(f"\nFTP>{cwd}>")
                if choice.upper() == 'ESC': continue
                    
                try:
                    choice_idx = int(choice) - 1
                    if choice_idx < 0 or choice_idx >= len(errors): raise ValueError
                except ValueError:
                    print(f"{COLORS['RED']}Неверный номер строки.{COLORS['RESET']}")
                    continue

                print("\nИзменить на что? (ESC для возврата)")
                new_text = input(f"\nFTP>{cwd}>")
                if new_text.upper() == 'ESC': continue

                errors[choice_idx]['fixed'] = new_text
                errors[choice_idx]['auto'] = True
                
                print("")
                progress_bar(COLORS['ORANGE'], COLORS['GREEN'], 1.0)
                print("Изменения записаны...")

        if action_cancelled:
            return

        print("Подождите, идёт применение исправлений...")
        progress_bar(COLORS['GREEN'], COLORS['GREEN'], 1.5)
        for err in errors:
            lines[err['idx']] = err['fixed'] + '\n'

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"\n--- ИСПРАВЛЕНИЕ ЗАВЕРШЕНО ---")
        
        print(f"{COLORS['RED']}Было (Весь файл):{COLORS['RESET']}")
        for i, line in enumerate(original_lines):
            if lines[i] != line:
                print(f"{COLORS['RED']}{i+1:3d} | {line.rstrip('\n')}{COLORS['RESET']}")
            else:
                print(f"{i+1:3d} | {line.rstrip('\n')}")

        print(f"\n{COLORS['GREEN']}Стало (Весь файл):{COLORS['RESET']}")
        for i, line in enumerate(lines):
            if original_lines[i] != line:
                print(f"{COLORS['GREEN']}{i+1:3d} | {line.rstrip('\n')}{COLORS['RESET']}")
            else:
                print(f"{i+1:3d} | {line.rstrip('\n')}")

        print("\nПодождите, идёт выявление ошибок...")
        progress_bar(COLORS['RED'], COLORS['GREEN'], 1.5)
        
        final_errors = analyze_and_fix(lines)
        if not final_errors:
            print(f"         {COLORS['GREEN']}ошибок не выявлено!{COLORS['RESET']}\n")
            break
        else:
            print(f"         {COLORS['RED']}Остались ошибки ({len(final_errors)} шт.){COLORS['RESET']}\n")
            print("Нажмите Y для продолжения исправления. Нажмите N для выхода.")
            while True:
                ans = get_key()
                if ans in ('Y', 'N'): break
            if ans == 'N': break
            else:
                clear_screen()
                continue

def main():
    latest_version = get_latest_version()
    
    print(f"{COLORS['GREEN']}Программа FTP (Fix This Python) {CURRENT_VERSION}{COLORS['RESET']}")
    print("Команды: cd <папка>, check <файл/номер>, fix <файл/номер>, run <файл/номер>, help, exit")
    
    if latest_version != CURRENT_VERSION:
        print(f"\n{COLORS['ORANGE']}ВНИМАНИЕ: Вышла версия {latest_version} пожалуйста обновите утилиту для корректной работы. Для этого зайдите на fix-this-python.vercel.app и скачайте версию {latest_version}.{COLORS['RESET']}\n")
    
    update_dir_list()
    
    while True:
        try:
            cwd = os.getcwd()
            cmd_input = input(f"\nFTP>{cwd}>").strip()
            
            if not cmd_input: continue
            cmd_parts = cmd_input.split()
            cmd_base = cmd_parts[0].lower()
            arg = " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else ""
            
            if cmd_base == 'exit': break
                
            elif cmd_base == 'help':
                print(f"\n{COLORS['GREEN']}Доступные команды:{COLORS['RESET']}")
                print("  cd <папка>         - перейти в указанную директорию")
                print("  check <файл/номер> - проверить файл на наличие синтаксических ошибок")
                print("  fix <файл/номер>   - автоматически исправить ошибки в файле")
                print("  run <файл/номер>   - ЗАПУСТИТЬ файл в безопасной песочнице")
                print("  help               - показать эту справку")
                print("  exit               - выйти из программы\n")
                
            elif cmd_base == 'cd' and arg:
                try: 
                    os.chdir(arg)
                    update_dir_list()
                except Exception as e: 
                    print(f"{COLORS['RED']}Ошибка: {e}{COLORS['RESET']}")
                    
            elif cmd_base == 'check' and arg:
                cmd_check(arg)
                
            elif cmd_base == 'fix' and arg:
                cmd_fix(arg)
                
            elif cmd_base == 'run' and arg:
                filename = resolve_filename(arg)
                if filename and os.path.exists(filename):
                    run_in_sandbox(filename)
                else:
                    print(f"{COLORS['RED']}Ошибка: Файл не найден.{COLORS['RESET']}")
                
            else:
                print(f"Неизвестная команда или отсутствуют аргументы. Доступны: cd, check, fix, run, help, exit")
                
        except KeyboardInterrupt:
            print("\nВыход...")
            break
            
        except Exception as e:
            # Получаем полный Traceback (историю вызовов для точного понимания ошибки разработчиком)
            error_traceback = traceback.format_exc()
            
            print(f"\n{COLORS['RED']}Критическая ошибка программы: {e}{COLORS['RESET']}")
            
            if latest_version != CURRENT_VERSION:
                print(f"{COLORS['ORANGE']}Попробуйте обновиться с {CURRENT_VERSION} до {latest_version} для решения проблемы. Для этого зайдите на fix-this-python.vercel.app и скачайте версию {latest_version}.{COLORS['RESET']}")
            
            # --- БЛОК ЗАПРОСА ОТПРАВКИ ЛОГОВ ---
            print("\nХотите отправить лог ошибки разработчикам для улучшения программы?")
            print("[Y] - Да, отправить   [N] - Нет   [R] - Что будет отправлено и политика")
            
            while True:
                key = get_key()
                if key in ('Y', 'N', 'R'):
                    if key == 'R':
                        print(f"\n{COLORS['ORANGE']}--- ПОЛИТИКА ОТПРАВКИ ЛОГОВ ---{COLORS['RESET']}")
                        print("Будет отправлен исключительно технический текст сбоя (Traceback) и версия программы.")
                        print("Никакие ваши личные файлы, исходный код ваших проектов или персональные данные НЕ передаются.")
                        print("Эти данные будут использоваться разработчиком только для исправления внутренних багов утилиты.")
                        print(f"{COLORS['ORANGE']}-------------------------------{COLORS['RESET']}\n")
                        print("Отправить лог? [Y] - Да, отправить   [N] - Нет")
                    elif key == 'Y':
                        send_error_log(error_traceback)
                        break
                    elif key == 'N':
                        print(f"{COLORS['ORANGE']}Отправка лога отменена.{COLORS['RESET']}")
                        break

if __name__ == "__main__":
    main()
import os
import urllib.request
import urllib.error
import json
import traceback
import datetime
import sys
from ftp_utils import COLORS, get_key, clear_screen, progress_bar
from ftp_analyzer import analyze_and_fix
from ftp_sandbox import run_in_sandbox

CURRENT_VERSION = "v11.1"
FIREBASE_PROJECT_ID = "fix-this-python"
current_dir_files = []

def get_latest_version():
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/app_info/version"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('fields', {}).get('latest', {}).get('stringValue', CURRENT_VERSION)
    except Exception:
        return CURRENT_VERSION

def send_error_log(log_text):
    print(f"\n{COLORS['ORANGE']}Отправка лога...{COLORS['RESET']}")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/error_logs"
    
    upload_success = False
    
    try:
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = utc_now.isoformat().replace('+00:00', 'Z')
        if not timestamp_str.endswith('Z'): timestamp_str += 'Z'
        
        data = {
            "fields": {
                "timestamp": {"stringValue": timestamp_str},
                "error": {"stringValue": log_text},
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
            print(f"{COLORS['GREEN']}Лог успешно отправлен на сервер! Спасибо за помощь в улучшении программы.{COLORS['RESET']}")
            upload_success = True
            
    except Exception as ex:
        err_msg = str(ex)
        print(f"{COLORS['RED']}Не удалось отправить лог на сервер. Ошибка: {err_msg}{COLORS['RESET']}")
            
    if not upload_success:
        local_log_file = "ftp_crash_report.txt"
        try:
            with open(local_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- LOG {datetime.datetime.now().isoformat()} ---\n")
                f.write(log_text + "\n")
            print(f"{COLORS['GREEN']}Лог успешно сохранён ЛОКАЛЬНО в файл '{local_log_file}'. Вы можете передать его разработчику вручную!{COLORS['RESET']}")
        except Exception as local_ex:
            print(f"{COLORS['RED']}Также не удалось сохранить лог локально: {local_ex}{COLORS['RESET']}")

def ask_to_send_log(log_text, is_crash=True):
    if is_crash:
        print("\nХотите отправить лог ошибки разработчикам для улучшения программы?")
    else:
        print("\nПрограмма не смогла исправить все ошибки. Хотите отправить отчёт разработчику для улучшения алгоритмов?")
        
    print("[Y] - Да, отправить   [N] - Нет   [R] - Что будет отправлено и политика")
    
    while True:
        key = get_key()
        if key in ('Y', 'N', 'R'):
            if key == 'R':
                print(f"\n{COLORS['ORANGE']}--- ПОЛИТИКА ОТПРАВКИ ЛОГОВ ---{COLORS['RESET']}")
                print("Будет отправлена исключительно техническая информация. Ваши проекты в безопасности.")
                print(f"{COLORS['ORANGE']}-------------------------------{COLORS['RESET']}\n")
                print("Отправить лог? [Y] - Да, отправить   [N] - Нет")
            elif key == 'Y':
                send_error_log(log_text)
                break
            elif key == 'N':
                print(f"{COLORS['ORANGE']}Отправка лога отменена.{COLORS['RESET']}")
                break

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

                orig_line = errors[choice_idx]['original']
                indent_str = orig_line[:len(orig_line) - len(orig_line.lstrip())]
                if new_text.lstrip() == new_text:
                    new_text = indent_str + new_text

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

        # --- WATERMARK ДОБАВЛЕНИЕ СВЕРХУ ---
        has_watermark = False
        for l in lines[:5]:
            if "Fix This Python» fixed this python" in l:
                has_watermark = True
                break
                
        if not has_watermark:
            watermark_1 = "# «Fix This Python» fixed this python | fix-this-python.vercel.app Fixes your Python\n"
            watermark_2 = f"# FTP {CURRENT_VERSION} - fixed this script | fix-this-python.vercel.app Fixes your Python\n"
            lines.insert(0, watermark_2)
            lines.insert(0, watermark_1)

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"\n--- ИСПРАВЛЕНИЕ ЗАВЕРШЕНО ---")
        
        print(f"{COLORS['RED']}Было (Весь файл):{COLORS['RESET']}")
        for i, line in enumerate(original_lines):
            clean_line = line.rstrip('\n')
            was_fixed = any(err['idx'] == i for err in errors)
            if was_fixed:
                print(f"{COLORS['RED']}{i+1:3d} | {clean_line}{COLORS['RESET']}")
            else:
                print(f"{i+1:3d} | {clean_line}")

        print(f"\n{COLORS['GREEN']}Стало (Весь файл):{COLORS['RESET']}")
        for i, line in enumerate(lines):
            clean_line = line.rstrip('\n')
            if not has_watermark and i < 2:
                # Новые строки копирайта красим в зеленый как исправленные
                print(f"{COLORS['GREEN']}{i+1:3d} | {clean_line}{COLORS['RESET']}")
            else:
                # Синхронизируем индекс с оригинальным списком строк
                orig_idx = i - 2 if not has_watermark else i
                was_fixed = any(err['idx'] == orig_idx for err in errors)
                if was_fixed:
                    print(f"{COLORS['GREEN']}{i+1:3d} | {clean_line}{COLORS['RESET']}")
                else:
                    print(f"{i+1:3d} | {clean_line}")

        print("\nПодождите, идёт выявление ошибок...")
        progress_bar(COLORS['RED'], COLORS['GREEN'], 1.5)
        
        final_errors = analyze_and_fix(lines)
        if not final_errors:
            print(f"         {COLORS['GREEN']}ошибок не выявлено!{COLORS['RESET']}\n")
            break
        else:
            print(f"         {COLORS['RED']}Остались ошибки ({len(final_errors)} шт.){COLORS['RESET']}\n")
            
            unresolved_log = "Unresolved errors after fix command:\n"
            for err in final_errors:
                unresolved_log += f"Line {err['idx'] + 1}: {err['original']}\n"
            
            ask_to_send_log(unresolved_log, is_crash=False)
            
            print("\nНажмите Y для продолжения попытки исправления. Нажмите N для выхода.")
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
    print("Команды: cd, check, fix, run, read, write, del comments, libs, help, exit")
    
    if latest_version != CURRENT_VERSION and latest_version not in ("v10.3", "v10.4", "v10.5", "v10.6"):
        print(f"\n{COLORS['ORANGE']}ВНИМАНИЕ: Вышла версия {latest_version}. Скачайте на fix-this-python.vercel.app{COLORS['RESET']}\n")
    
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
                print("  cd <путь>          - перейти в указанную директорию")
                print("  check <файл/номер>  - проверить файл на наличие синтаксических ошибок")
                print("  fix <файл/номер>    - автоматически исправить ошибки в файле")
                print("  run <файл/номер>    - ЗАПУСТИТЬ файл в безопасной песочнице")
                print("  read <файл/номер>   - вывести содержимое файла в консоль")
                print("  write <файл/номер>  - перезаписать файл вручную (до ввода END)")
                print("  del comments <файл/номер> - удалить все комментарии из файла")
                print("  libs                - показать все установленные библиотеки (pip list)")
                print("  libs <название>          - проверить, установлена ли конкретная библиотека")
                print("  help                - показать эту справку")
                print("  exit                - выйти из программы\n")
                
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
                    
            elif cmd_base == 'read' and arg:
                filename = resolve_filename(arg)
                if filename and os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                        print(f"\n{COLORS['ORANGE']}--- Содержимое '{filename}' ---{COLORS['RESET']}")
                        print(f.read().strip())
                        print(f"{COLORS['ORANGE']}--------------------------------{COLORS['RESET']}")
                else:
                    print(f"{COLORS['RED']}Ошибка: Файл не найден.{COLORS['RESET']}")

            elif cmd_base == 'write' and arg:
                filename = resolve_filename(arg)
                if filename:
                    print(f"\n{COLORS['GREEN']}Вводите новый текст для файла '{filename}'.{COLORS['RESET']}")
                    print(f"{COLORS['ORANGE']}Для завершения ввода напишите строку 'END' или 'КОНЕЦ'{COLORS['RESET']}")
                    new_content = []
                    while True:
                        user_line = input()
                        if user_line.strip().upper() in ('END', 'КОНЕЦ'):
                            break
                        new_content.append(user_line + '\n')
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.writelines(new_content)
                    print(f"{COLORS['GREEN']}Файл '{filename}' успешно перезаписан!{COLORS['RESET']}")

            elif cmd_base == 'del' and arg.lower().startswith('comments'):
                file_arg = arg[len('comments'):].strip()
                filename = resolve_filename(file_arg)
                if filename and os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        file_lines = f.readlines()
                        
                    new_lines = []
                    in_multiline = False
                    multiline_char = ""
                    
                    for original_line in file_lines:
                        l = original_line
                        idx_to_cut = -1
                        in_str = False
                        q_char = None
                        i = 0
                        
                        while i < len(l):
                            if not in_str and not in_multiline:
                                if l[i:i+3] in ('"""', "'''"):
                                    in_multiline = True
                                    multiline_char = l[i:i+3]
                                    i += 3
                                    continue
                                elif l[i] in "\"'":
                                    in_str = True
                                    q_char = l[i]
                                elif l[i] == '#':
                                    idx_to_cut = i
                                    break
                            elif in_multiline:
                                if l[i:i+3] == multiline_char:
                                    in_multiline = False
                                    i += 3
                                    continue
                                if l[i] == '\\':  # Защита от экранирования
                                    i += 2
                                    continue
                            elif in_str:
                                if l[i] == '\\':
                                    i += 2
                                    continue
                                elif l[i] == q_char:
                                    in_str = False
                            i += 1
                            
                        if idx_to_cut != -1:
                            l = l[:idx_to_cut].rstrip() + '\n'
                            
                        # Сжатие образовавшихся пустых строк
                        if not l.strip():
                            if original_line.strip() != "":
                                # Строка была с комментарием, стала пустой -> Полностью удаляем ее
                                continue
                            else:
                                # Строка и так была пустой -> Добавляем, только если предыдущая строка не пустая (макс. 1 пробел)
                                if new_lines and new_lines[-1].strip() != "":
                                    new_lines.append('\n')
                        else:
                            new_lines.append(l)
                            
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    print(f"{COLORS['GREEN']}Комментарии успешно удалены из файла '{filename}', а пустые строки сжаты!{COLORS['RESET']}")
                else:
                    print(f"{COLORS['RED']}Ошибка: Файл не найден.{COLORS['RESET']}")

            elif cmd_base in ('libs', 'lib'):
                if arg:
                    print(f"\nПоиск библиотеки '{arg}'...")
                    try:
                        import importlib.util
                        spec = importlib.util.find_spec(arg)
                        if spec:
                            print(f"{COLORS['GREEN']}Библиотека '{arg}' УСТАНОВЛЕНА!{COLORS['RESET']}")
                            print(f"Путь: {spec.origin}")
                            try:
                                mod = __import__(arg)
                                if hasattr(mod, '__version__'):
                                    print(f"Версия: {mod.__version__}")
                            except Exception:
                                pass
                        else:
                            print(f"{COLORS['RED']}Библиотека '{arg}' НЕ НАЙДЕНА в Python.{COLORS['RESET']}")
                            print(f"{COLORS['ORANGE']}Чтобы установить, используйте в системной консоли: pip install {arg}{COLORS['RESET']}")
                    except Exception as e:
                        print(f"{COLORS['RED']}Ошибка при поиске библиотеки: {e}{COLORS['RESET']}")
                else:
                    print(f"\n{COLORS['ORANGE']}Список установленных библиотек (pip list):{COLORS['RESET']}")
                    try:
                        import subprocess
                        subprocess.run([sys.executable, "-m", "pip", "list"])
                    except Exception as e:
                        print(f"{COLORS['RED']}Не удалось запустить pip: {e}{COLORS['RESET']}")
                
            else:
                print(f"Неизвестная команда. Доступны: cd, check, fix, run, read, write, del comments, libs, help, exit")
                
        except KeyboardInterrupt:
            print("\nВыход...")
            break
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"\n{COLORS['RED']}Критическая ошибка программы: {e}{COLORS['RESET']}")
            ask_to_send_log(error_traceback, is_crash=True)

if __name__ == "__main__":
    main()
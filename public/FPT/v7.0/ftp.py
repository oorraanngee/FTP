import os
from ftp_utils import COLORS, get_key, clear_screen, progress_bar
from ftp_analyzer import analyze_and_fix

# Глобальный список файлов в директории
current_dir_files = []

def update_dir_list():
    """Обновляет список файлов текущей директории и выводит его, если файлов <= 99"""
    global current_dir_files
    current_dir_files = []
    try:
        items = sorted(os.listdir('.'))
        files = [f for f in items if os.path.isfile(f)]
        if 0 < len(files) <= 99:
            print(f"\n{COLORS['ORANGE']}Файлы в текущей директории:{COLORS['RESET']}")
            for i, f in enumerate(files):
                print(f"{i + 1}. {f}")
            current_dir_files = files
    except Exception as e:
        print(f"{COLORS['RED']}Ошибка чтения директории: {e}{COLORS['RESET']}")

def resolve_filename(arg):
    """Преобразует индекс (строку из цифр) в имя файла или возвращает имя как есть"""
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
        print(f"         {COLORS['GREEN']}ошибок не выявлено!{COLORS['RESET']}\n")
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
            print(f"         {COLORS['GREEN']}ошибок не выявлено!{COLORS['RESET']}\n")
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
            print("\nНажмите ENTER для того чтобы подтвердить... Нажмите E чтобы изменить исправление... Нажмите ESC чтобы отменить исправление файла...")
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
                print("\nКакую строку изменить? (Если вы не хотите изменить нажмите ESC чтобы вернутся к прошлому выбору):")
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

                print("\nИзменить на что? (Если вы не хотите изменить напишите ESC чтобы вернутся к прошлому выбору)")
                new_text = input(f"\nFTP>{cwd}>")
                if new_text.upper() == 'ESC': continue

                errors[choice_idx]['fixed'] = new_text
                errors[choice_idx]['auto'] = True
                
                print("")
                progress_bar(COLORS['ORANGE'], COLORS['GREEN'], 1.0)
                print("Изменения записаны...")
                print(f"         {errors[choice_idx]['original']} > {COLORS['GREEN']}{errors[choice_idx]['fixed']}{COLORS['RESET']}")

        if action_cancelled:
            return

        print("Подождите, идёт применение исправлений...")
        progress_bar(COLORS['GREEN'], COLORS['GREEN'], 1.5)
        print("         Сделано:")
        for err in errors:
            print(f"         {err['original']} > {err['fixed']}")
            lines[err['idx']] = err['fixed'] + '\n'

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"\n--- ИСПРАВЛЕНИЕ ЗАВЕРШЕНО ---")
        
        # Вывод ВСЕГО кода БЫЛО
        print(f"{COLORS['RED']}Было (Весь файл):{COLORS['RESET']}")
        for i, line in enumerate(original_lines):
            # Подсветка измененных строк красным
            if lines[i] != line:
                print(f"{COLORS['RED']}{i+1:3d} | {line.rstrip('\n')}{COLORS['RESET']}")
            else:
                print(f"{i+1:3d} | {line.rstrip('\n')}")

        print(f"\n{COLORS['GREEN']}Стало (Весь файл):{COLORS['RESET']}")
        for i, line in enumerate(lines):
            # Подсветка измененных строк зеленым
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
            print("Чтобы перезапустить процесс исправления файла нажмите Y. Если вы желаете закончить исправление файлов то нажмите N.")
            
            ans = None
            while True:
                ans = get_key()
                if ans in ('Y', 'N'):
                    break
            
            if ans == 'N':
                print("")
                break
            else:
                clear_screen()
                continue

def main():
    print(f"{COLORS['GREEN']}Программа FTP (Fix This Python) v7.0{COLORS['RESET']}")
    print("Команды: cd <папка>, check <файл/номер>, fix <файл/номер>, exit")
    
    # Показываем список файлов при запуске
    update_dir_list()
    
    while True:
        try:
            cwd = os.getcwd()
            cmd_input = input(f"\nFTP>{cwd}>").strip()
            
            if not cmd_input: continue
            if cmd_input.lower() == 'exit': break
                
            elif cmd_input.startswith("cd "):
                path = cmd_input[3:].strip()
                try: 
                    os.chdir(path)
                    update_dir_list()
                except Exception as e: 
                    print(f"{COLORS['RED']}Ошибка: {e}{COLORS['RESET']}")
                    
            elif cmd_input.startswith("check "):
                cmd_check(cmd_input[6:].strip())
                
            elif cmd_input.startswith("fix "):
                cmd_fix(cmd_input[4:].strip())
                
            else:
                print(f"Неизвестная команда: '{cmd_input}'. Доступны: cd, check, fix, exit")
                
        except KeyboardInterrupt:
            print("\nВыход...")
            break
        except Exception as e:
            print(f"{COLORS['RED']}Критическая ошибка: {e}{COLORS['RESET']}")

if __name__ == "__main__":
    main()

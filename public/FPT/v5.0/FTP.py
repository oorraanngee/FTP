import os
import sys
import time
import re
import ast
import builtins
import difflib

if os.name == 'nt':
    os.system('color')

RED = "\033[91m"
GREEN = "\033[92m"
ORANGE = "\033[33m"
RESET = "\033[0m"

def get_key():
    try:
        import msvcrt
        char = msvcrt.getch()
        if char in (b'\r', b'\n'): return 'ENTER'
        if char == b'\x1b': return 'ESC'
        return char.decode('utf-8', errors='ignore').upper()
    except ImportError:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch in ('\r', '\n'): return 'ENTER'
            if ch == '\x1b': return 'ESC'
            return ch.upper()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def progress_bar(dash_color, spinner_color, duration=2.0):
    chars = ['/', '-', '\\', '|']
    steps = 20
    for i in range(steps):
        spin = chars[i % 4]
        dashes = "-" * steps
        bar = f"{dash_color}{dashes}{RESET} {spinner_color}{spin}{RESET}"
        sys.stdout.write(f"\rПрогресс: {bar}")
        sys.stdout.flush()
        time.sleep(duration / steps)
    bar = f"{dash_color}{'-' * steps}{RESET} {spinner_color}+{RESET}"
    sys.stdout.write(f"\rПрогресс: {bar}\n")

def fix_print_heuristics(line):
    original = line
    line = line.rstrip('\n')
    line = line.replace('«', '"').replace('»', '"')
    
    typos = [
        "prnt", "prit", "pnt", "pprint", "printt", "pirnt", "prnit", "pirtn",
        "orint", "purnt", "pribt", "prinf", "orjbt", "pi", "rint", "pri",
        "prt", "zkute", "зрт"
    ]
    
    typo_pattern = r'^( *\t*)(?:' + '|'.join(typos) + r')(?=[\(\'\"\sА-Яа-яЁё]|$)(.*)$'
    m = re.match(typo_pattern, line)
    if m:
        line = m.group(1) + "print" + m.group(2)
        
    m = re.match(r'^( *\t*)print([А-Яа-яЁёa-zA-Z0-9_].*)$', line)
    if m:
        content = m.group(2)
        if content.endswith(')'): content = content[:-1]
        line = f"{m.group(1)}print({content})"
        
    line = re.sub(r'^( *\t*)print\s+\(', r'\1print(', line)
    line = re.sub(r'^( *\t*)print\s*(["\'])(.*?)\2\s*$', r'\1print(\2\3\2)', line)
    line = re.sub(r'^( *\t*)print\s*(["\'])(.*?)\2\s*\)\s*$', r'\1print(\2\3\2)', line)
    
    m = re.match(r'^( *\t*)print\s+(?!\()(.*?)\s*(\)?)\s*$', line)
    if m:
        content = m.group(2)
        if content.endswith(')'): content = content[:-1]
        line = f"{m.group(1)}print({content})"
        
    line = re.sub(r'print\(\s*"([^"]*?)\'\s*\)', r'print("\1")', line)
    line = re.sub(r'print\(\s*\'([^\']*?)"\s*\)', r"print('\1')", line)
    
    m = re.search(r'print\(\s*(["\'])([^"\']*?)\)', line)
    if m:
        q = m.group(1)
        text = m.group(2)
        line = line.replace(f'print({q}{text})', f'print({q}{text}{q})')
        
    m = re.match(r'^( *\t*)print\(\s*"(.*?)"\s*\)\s*$', line)
    if m:
        inner = m.group(2)
        if '"' in inner: line = f"{m.group(1)}print('{inner}')"
        
    m = re.match(r"^( *\t*)print\(\s*'(.*?)'\s*\)\s*$", line)
    if m:
        inner = m.group(2)
        if "'" in inner: line = f'{m.group(1)}print("{inner}")'
        
    line = re.sub(r'print\(\s*(["\'].*?["\'])\s+([^,)\s].*?)\)', r'print(\1, \2)', line)
    line = re.sub(r'print\(\s*(["\'].*?["\'])\s*\+\s*([0-9]+)\s*\)', r'print(\1, \2)', line)
    line = re.sub(r'print\(\s*(?<![fF])(["\'])(.*?\{[a-zA-Z_]\w*\}.*?)\1\s*\)', r'print(f\1\2\1)', line)
    
    if original.endswith('\n'):
        line += '\n'
        
    return line != original, line

def analyze_and_fix(lines):
    errors_dict = {}
    current_lines = lines.copy()
    
    for i, line in enumerate(current_lines):
        if not line.strip(): continue
        changed, new_line = fix_print_heuristics(line)
        if changed:
            errors_dict[i] = {
                "original": lines[i].rstrip('\n'),
                "fixed": new_line.rstrip('\n'),
                "auto": True
            }
            current_lines[i] = new_line

    for _ in range(30):
        source = "".join(current_lines)
        try:
            tree = ast.parse(source)
            
            defined = set(dir(builtins))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    defined.add(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    defined.add(node.name)
                    for arg in getattr(node.args, 'args', []):
                        defined.add(arg.arg)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        defined.add(alias.asname or alias.name)

            found_error = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id not in defined:
                        idx = node.lineno - 1
                        bad = node.id
                        guesses = difflib.get_close_matches(bad, defined, n=1, cutoff=0.4)
                        if guesses:
                            best = guesses[0]
                            old_line = current_lines[idx]
                            new_line = re.sub(r'\b' + re.escape(bad) + r'\b', best, old_line)
                            if new_line != old_line:
                                current_lines[idx] = new_line
                                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": new_line.rstrip('\n'), "auto": True}
                                found_error = True
                                break
                        else:
                            if idx not in errors_dict:
                                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": current_lines[idx].rstrip('\n'), "auto": False}
                            defined.add(bad)
            if not found_error:
                break
                
        except IndentationError as e:
            idx = (e.lineno or 1) - 1
            idx = min(max(idx, 0), len(current_lines) - 1)
            
            while idx > 0 and (not current_lines[idx].strip() or current_lines[idx].strip().startswith('#')):
                idx -= 1
                
            old_line = current_lines[idx]
            if "# FTP_SKIP:" in old_line:
                break 

            errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": old_line.rstrip('\n'), "auto": False}
            m = re.match(r'^(\s*)', old_line)
            sp = m.group(1) if m else ""
            current_lines[idx] = f"{sp}# FTP_SKIP: {old_line.lstrip()}"
            if not current_lines[idx].endswith('\n'): current_lines[idx] += '\n'
            
        except SyntaxError as e:
            idx = (e.lineno or 1) - 1
            idx = min(max(idx, 0), len(current_lines) - 1)
            
            while idx > 0 and (not current_lines[idx].strip() or current_lines[idx].strip().startswith('#')):
                idx -= 1
                
            old_line = current_lines[idx]
            if "# FTP_SKIP:" in old_line:
                break 
                
            fixed_line = old_line
            
            if re.match(r'^\s*(if|for|while|def|class|elif|else|try|except|with)\b.*', fixed_line) and not fixed_line.rstrip().endswith(':'):
                fixed_line = fixed_line.rstrip('\n\r') + ':\n'
                
            fixed_line = re.sub(r'([a-zA-Z_]\w*)\s*\+\+', r'\1 += 1', fixed_line)
            fixed_line = re.sub(r'([a-zA-Z_]\w*)\s*--', r'\1 -= 1', fixed_line)
                
            if fixed_line.count('"') % 2 != 0 and fixed_line.count("'") % 2 == 0:
                fixed_line = fixed_line.rstrip('\n\r') + '"\n'
            elif fixed_line.count("'") % 2 != 0 and fixed_line.count('"') % 2 == 0:
                fixed_line = fixed_line.rstrip('\n\r') + "'\n"
                
            unmatched_close = re.search(r'(?<!\()\)', fixed_line)
            if unmatched_close and '(' not in fixed_line:
                fixed_line = fixed_line.replace(')', '', 1)

            if fixed_line != old_line:
                current_lines[idx] = fixed_line
                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_line.rstrip('\n'), "auto": True}
            else:
                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": old_line.rstrip('\n'), "auto": False}
                m = re.match(r'^(\s*)', old_line)
                sp = m.group(1) if m else ""
                current_lines[idx] = f"{sp}# FTP_SKIP: {old_line.lstrip()}"
                if not current_lines[idx].endswith('\n'): current_lines[idx] += '\n'

    result = []
    for k in sorted(errors_dict.keys()):
        if lines[k].rstrip('\n') != errors_dict[k]["fixed"] or not errors_dict[k]["auto"]:
            result.append({"idx": k, "original": lines[k].rstrip('\n'), "fixed": errors_dict[k]["fixed"], "auto": errors_dict[k]["auto"]})
    return result

def cmd_check(filename):
    if not os.path.exists(filename):
        print(f"{RED}Ошибка: Файл '{filename}' не найден.{RESET}")
        return

    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print("\nПодождите, идёт выявление ошибок...")
    progress_bar(RED, GREEN, 2.0)
    
    errors = analyze_and_fix(lines)
    if not errors:
        print(f"         {GREEN}ошибок не выявлено!{RESET}\n")
        return

    print(f"         {RED}Найдено ошибок: {len(errors)}{RESET}")
    for err in errors:
        print(f"         Строка {err['idx'] + 1}: {RED}{err['original']}{RESET}")
    print("")

def cmd_fix(filename):
    if not os.path.exists(filename):
        print(f"{RED}Ошибка: Файл '{filename}' не найден.{RESET}")
        return

    while True:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        print("\nПодождите, идёт подготовка починки файла...")
        progress_bar(RED, GREEN, 1.5)

        print("\nПодождите, идёт выявление ошибок...")
        progress_bar(RED, GREEN, 2.0)
        
        errors = analyze_and_fix(lines)
        if not errors:
            print(f"         {GREEN}ошибок не выявлено!{RESET}\n")
            return

        print("         Найдено:")
        for err in errors:
            print(f"         {err['idx'] + 1}. {err['original']}")

        print("\nПодождите, идёт поиск исправлений...")
        progress_bar(GREEN, GREEN, 2.0)
        print("         Найдено:")
        for err in errors:
            if err["auto"] and err["fixed"] != err["original"]:
                print(f"         {err['original']} > {GREEN}{err['fixed']}{RESET}")
            else:
                print(f"         {err['original']} > {RED}{err['fixed']} [ОШИБКА, НАЖМИТЕ 'E']{RESET}")

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
                    color = GREEN if err["auto"] else RED
                    print(f"         {i + 1}. {color}{err['fixed']}{RESET} (Было: {err['original']})")
                
                cwd = os.getcwd()
                choice = input(f"\nFTP>{cwd}>")
                if choice.upper() == 'ESC': continue
                    
                try:
                    choice_idx = int(choice) - 1
                    if choice_idx < 0 or choice_idx >= len(errors): raise ValueError
                except ValueError:
                    print(f"{RED}Неверный номер строки.{RESET}")
                    continue

                print("\nИзменить на что? (Если вы не хотите изменить напишите ESC чтобы вернутся к прошлому выбору)")
                new_text = input(f"\nFTP>{cwd}>")
                if new_text.upper() == 'ESC': continue

                errors[choice_idx]['fixed'] = new_text
                errors[choice_idx]['auto'] = True
                
                print("")
                progress_bar(ORANGE, GREEN, 1.0)
                print("Изменения записаны...")
                print(f"         {errors[choice_idx]['original']} > {GREEN}{errors[choice_idx]['fixed']}{RESET}")

        if action_cancelled:
            return

        print("Подождите, идёт применение исправлений...")
        progress_bar(GREEN, GREEN, 1.5)
        print("         Сделано:")
        for err in errors:
            print(f"         {err['original']} > {err['fixed']}")
            lines[err['idx']] = err['fixed'] + '\n'

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"\n--- ИСПРАВЛЕНИЕ ЗАВЕРШЕНО ---")
        print(f"{RED}Было:{RESET}")
        for err in errors:
            print(f"{RED}          {err['idx'] + 1}. {err['original']}{RESET}")
            
        print(f"{GREEN}Стало:{RESET}")
        for err in errors:
            print(f"{GREEN}          {err['idx'] + 1}. {err['fixed']}{RESET}")

        print("\nПодождите, идёт выявление ошибок...")
        progress_bar(RED, GREEN, 1.5)
        
        final_errors = analyze_and_fix(lines)
        if not final_errors:
            print(f"         {GREEN}ошибок не выявлено!{RESET}\n")
            break
        else:
            print(f"         {RED}Остались ошибки ({len(final_errors)} шт.){RESET}\n")
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
    print(f"{GREEN}Программа FTP (Fix This Python) v5.0{RESET}")
    print("Команды: cd <папка>, check <файл>, fix <файл>, exit")
    
    while True:
        try:
            cwd = os.getcwd()
            cmd_input = input(f"FTP>{cwd}>").strip()
            
            if not cmd_input: continue
            if cmd_input.lower() == 'exit': break
                
            elif cmd_input.startswith("cd "):
                path = cmd_input[3:].strip()
                try: os.chdir(path)
                except Exception as e: print(f"Ошибка: {e}")
                    
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
            print(f"{RED}Критическая ошибка: {e}{RESET}")

if __name__ == "__main__":
    main()
import ast
import builtins
import difflib
import re
import keyword
from ftp_rules import fix_print_heuristics, fix_keywords_heuristics

def analyze_and_fix(lines):
    errors_dict = {}
    current_lines = lines.copy()
    
    # ПРЕДВАРИТЕЛЬНЫЙ ПРОХОД: Эвристики (очищает код до того, как он сломает парсер)
    for i, line in enumerate(current_lines):
        if not line.strip(): continue
        
        # Умный фикс сломанных декораторов (например classmethod-property без @)
        stripped = line.strip()
        if stripped and not stripped.startswith('@') and not stripped.startswith('def ') and not stripped.startswith('#'):
            # Если это похоже на одно-два слова через дефис или точку (и не является системным словом)
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.-]*$', stripped) and stripped not in keyword.kwlist:
                # Смотрим вперед: если следующая значимая строка - функция или класс
                is_decorator = False
                for j in range(i + 1, len(current_lines)):
                    next_stripped = current_lines[j].strip()
                    if not next_stripped or next_stripped.startswith('#'): continue
                    if re.search(r'\b(def|class)\b', next_stripped):
                        is_decorator = True
                    break
                    
                if is_decorator:
                    fixed_dec = line.replace('-', '.')
                    m = re.match(r'^(\s*)', fixed_dec)
                    sp = m.group(1) if m else ''
                    fixed_dec = sp + '@' + fixed_dec.lstrip()
                    
                    errors_dict[i] = {
                        "original": lines[i].rstrip('\n'),
                        "fixed": fixed_dec.rstrip('\n'),
                        "auto": True
                    }
                    current_lines[i] = fixed_dec
                    continue
        
        changed_print, line_p = fix_print_heuristics(line)
        changed_kw, line_k = fix_keywords_heuristics(line_p)
        
        if changed_print or changed_kw:
            errors_dict[i] = {
                "original": lines[i].rstrip('\n'),
                "fixed": line_k.rstrip('\n'),
                "auto": True
            }
            current_lines[i] = line_k

    # ОСНОВНОЙ ПРОХОД: AST Анализ
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
            if "# FTP_SKIP:" in old_line: break 

            if "expected an indented block" in str(e).lower():
                if current_lines[idx].strip().endswith(':'):
                    current_lines[idx] = current_lines[idx].rstrip('\n\r') + ' pass\n'
                    continue
                elif idx > 0 and current_lines[idx-1].strip().endswith(':'):
                    current_lines[idx-1] = current_lines[idx-1].rstrip('\n\r') + ' pass\n'
                    continue
                    
            m_kw = re.match(r'^\s*(else:|elif\b.*|except\b.*|finally:)', old_line)
            if m_kw:
                target_indent = None
                is_if = m_kw.group(1).startswith('el')
                search_for = r'^\s*(if|elif)\b' if is_if else r'^\s*(try|except)\b'
                for j in range(idx - 1, -1, -1):
                    if re.match(search_for, current_lines[j]):
                        target_indent = re.match(r'^(\s*)', current_lines[j]).group(1)
                        break
                if target_indent is not None:
                    fixed_line = target_indent + old_line.lstrip()
                    if fixed_line != old_line:
                        current_lines[idx] = fixed_line
                        errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_line.rstrip('\n'), "auto": True}
                        continue
                        
            if "unexpected indent" in str(e).lower() and idx > 0:
                prev_indent = re.match(r'^(\s*)', current_lines[idx-1]).group(1)
                fixed_line = prev_indent + old_line.lstrip()
                if fixed_line != old_line:
                    current_lines[idx] = fixed_line
                    errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_line.rstrip('\n'), "auto": True}
                    continue

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
            if "# FTP_SKIP:" in old_line: break 
                
            if "expected an indented block" in str(e).lower() or "unexpected eof" in str(e).lower():
                if current_lines[idx].strip().endswith(':'):
                    current_lines[idx] = current_lines[idx].rstrip('\n\r') + ' pass\n'
                    continue
                elif idx > 0 and current_lines[idx-1].strip().endswith(':'):
                    current_lines[idx-1] = current_lines[idx-1].rstrip('\n\r') + ' pass\n'
                    continue

            fixed_line = old_line
            
            # Проверка забытого двоеточия для структурных блоков
            if re.match(r'^\s*(if|for|while|def|class|elif|else|try|except|with|match|case)\b.*', fixed_line) and not fixed_line.rstrip().endswith(':'):
                fixed_line = fixed_line.rstrip('\n\r') + ':\n'
                
            fixed_line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*\+\+\s*$', r'\1\2 += 1', fixed_line)
            fixed_line = re.sub(r'([a-zA-Z_]\w*)\s*\+\+', r'\1 + 1', fixed_line)
            
            fixed_line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*--\s*$', r'\1\2 -= 1', fixed_line)
            fixed_line = re.sub(r'([a-zA-Z_]\w*)\s*--', r'\1 - 1', fixed_line)
                
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
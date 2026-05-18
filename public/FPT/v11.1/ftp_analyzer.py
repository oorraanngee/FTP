import ast
import builtins
import difflib
import re
from ftp_rules import fix_print_heuristics, fix_keywords_heuristics

def analyze_and_fix(lines):
    errors_dict = {}
    current_lines = lines.copy()
    
    # 1. ПРЕДВАРИТЕЛЬНЫЙ ПРОХОД: Жесткая очистка синтаксиса
    for i, line in enumerate(current_lines):
        if not line.strip(): continue
        
        changed_print, line_p = fix_print_heuristics(current_lines[i])
        changed_kw, line_k = fix_keywords_heuristics(line_p)
        
        if changed_print or changed_kw:
            errors_dict[i] = {"original": lines[i].rstrip('\n'), "fixed": line_k.rstrip('\n'), "auto": True}
            current_lines[i] = line_k

    # 2. КОНТЕКСТНЫЙ ПРОХОД: Умное удаление self после @staticmethod
    for i, line in enumerate(current_lines):
        if '@staticmethod' in line:
            for j in range(i + 1, min(i + 5, len(current_lines))):
                if current_lines[j].strip().startswith('def '):
                    old_def = current_lines[j]
                    new_def = re.sub(r'(def\s+[a-zA-Z_]\w*\s*\(\s*)self\s*(?:,\s*)?', r'\1', old_def)
                    if new_def != old_def:
                        errors_dict[j] = {"original": lines[j].rstrip('\n'), "fixed": new_def.rstrip('\n'), "auto": True}
                        current_lines[j] = new_def
                    break

    # 3. ОСНОВНОЙ ПРОХОД: AST Анализ
    for _ in range(30):
        source = "".join(current_lines)
        try:
            tree = ast.parse(source)
            
            defined = set(dir(builtins))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    defined.add(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    defined.add(node.name)
                    if hasattr(node, 'args') and hasattr(node.args, 'args'):
                        for arg in node.args.args:
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
            
            err_msg = str(e).lower()
            
            if "expected an indented block" in err_msg:
                if current_lines[idx].strip().endswith(':'):
                    current_lines[idx] = current_lines[idx].rstrip('\n\r') + ' pass\n'
                    errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": current_lines[idx].rstrip('\n'), "auto": True}
                    continue
                elif idx > 0 and current_lines[idx-1].strip().endswith(':'):
                    if current_lines[idx].strip():
                        prev_indent = re.match(r'^(\s*)', current_lines[idx-1]).group(1)
                        fixed_l = prev_indent + "    " + current_lines[idx].lstrip()
                        current_lines[idx] = fixed_l
                        errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_l.rstrip('\n'), "auto": True}
                        continue
                    else:
                        current_lines[idx-1] = current_lines[idx-1].rstrip('\n\r') + ' pass\n'
                        errors_dict[idx-1] = {"original": lines[idx-1].rstrip('\n'), "fixed": current_lines[idx-1].rstrip('\n'), "auto": True}
                        continue
                    
            old_line = current_lines[idx]
            m_kw = re.match(r'^\s*(else:|elif\b.*|except\b.*|finally:)', old_line)
            if m_kw:
                target_indent = None
                search_for = r'^\s*(if|elif)\b' if m_kw.group(1).startswith('el') else r'^\s*(try|except)\b'
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
                        
            if "unexpected indent" in err_msg and idx > 0:
                prev_line_stripped = current_lines[idx-1].strip()
                if re.match(r'^(def|class|if|elif|else|for|while|try|except|finally|with|match|case)\b', prev_line_stripped) and not prev_line_stripped.endswith(':'):
                    current_lines[idx-1] = current_lines[idx-1].rstrip('\n\r') + ':\n'
                    errors_dict[idx-1] = {"original": lines[idx-1].rstrip('\n'), "fixed": current_lines[idx-1].rstrip('\n'), "auto": True}
                    continue
                else:
                    for prev_idx in range(idx - 1, -1, -1):
                        if current_lines[prev_idx].strip():
                            prev_indent = re.match(r'^(\s*)', current_lines[prev_idx]).group(1)
                            if current_lines[prev_idx].strip().endswith(':'):
                                prev_indent += "    "
                            fixed_line = prev_indent + current_lines[idx].lstrip()
                            if fixed_line != current_lines[idx]:
                                current_lines[idx] = fixed_line
                                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_line.rstrip('\n'), "auto": True}
                            break
                    continue

            if not (idx in errors_dict and errors_dict[idx].get("auto")):
                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": old_line.rstrip('\n'), "auto": False}
            break
            
        except SyntaxError as e:
            idx = (e.lineno or 1) - 1
            idx = min(max(idx, 0), len(current_lines) - 1)
            
            err_msg = str(e).lower()
            
            if "unterminated string literal" in err_msg or "eol while scanning string literal" in err_msg:
                old_line = current_lines[idx]
                stripped = old_line.rstrip('\n\r')
                
                m = re.match(r'^(.*?)(\)+)$', stripped)
                if m:
                    base, tail = m.group(1), m.group(2)
                else:
                    base, tail = stripped, ""
                    
                sq = base.count("'")
                dq = base.count('"')
                
                if dq % 2 != 0:
                    fixed_line = base + '"' + tail + '\n'
                elif sq % 2 != 0:
                    fixed_line = base + "'" + tail + '\n'
                else:
                    fixed_line = base + '"' + tail + '\n'
                
                if fixed_line.count('(') > fixed_line.count(')'):
                    fixed_line = fixed_line.rstrip('\n\r') + ')\n'
                    
                current_lines[idx] = fixed_line
                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_line.rstrip('\n'), "auto": True}
                continue

            old_line = current_lines[idx]
            m_kw = re.match(r'^\s*(else:|elif\b.*|except\b.*|finally:)', old_line)
            if m_kw:
                target_indent = None
                search_for = r'^\s*(if|elif)\b' if m_kw.group(1).startswith('el') else r'^\s*(try|except)\b'
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

            if "expected an indented block" in err_msg or "unexpected eof" in err_msg:
                if current_lines[idx].strip().endswith(':'):
                    current_lines[idx] = current_lines[idx].rstrip('\n\r') + ' pass\n'
                    errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": current_lines[idx].rstrip('\n'), "auto": True}
                    continue
                elif idx > 0 and current_lines[idx-1].strip().endswith(':'):
                    if current_lines[idx].strip():
                        prev_indent = re.match(r'^(\s*)', current_lines[idx-1]).group(1)
                        current_lines[idx] = prev_indent + "    " + current_lines[idx].lstrip()
                        errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": current_lines[idx].rstrip('\n'), "auto": True}
                        continue
                    else:
                        current_lines[idx-1] = current_lines[idx-1].rstrip('\n\r') + ' pass\n'
                        errors_dict[idx-1] = {"original": lines[idx-1].rstrip('\n'), "fixed": current_lines[idx-1].rstrip('\n'), "auto": True}
                        continue

            def try_fix_syntax_line(i):
                old_l = current_lines[i]
                fixed_l = old_l
                stripped = re.sub(r'#.*$', '', fixed_l).rstrip()
                if re.match(r'^\s*(if|for|while|def|class|elif|else|try|except|with|match|case)\b', stripped):
                    if not stripped.endswith(':') and not stripped.endswith('pass'):
                        m_comment = re.search(r'(#.*)$', fixed_l)
                        if m_comment: fixed_l = fixed_l[:m_comment.start()].rstrip() + ':  ' + m_comment.group(1) + '\n'
                        else: fixed_l = fixed_l.rstrip('\n\r') + ':\n'
                
                unmatched = re.search(r'(?<!\()\)', fixed_l)
                if unmatched and '(' not in fixed_l:
                    fixed_l = fixed_l.replace(')', '', 1)
                return old_l, fixed_l

            old_line, fixed_line = try_fix_syntax_line(idx)
            if fixed_line != old_line:
                current_lines[idx] = fixed_line
                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": fixed_line.rstrip('\n'), "auto": True}
                continue
                
            if idx + 1 < len(current_lines):
                old_line_next, fixed_line_next = try_fix_syntax_line(idx + 1)
                if fixed_line_next != old_line_next:
                    current_lines[idx+1] = fixed_line_next
                    errors_dict[idx+1] = {"original": lines[idx+1].rstrip('\n'), "fixed": fixed_line_next.rstrip('\n'), "auto": True}
                    continue

            if not (idx in errors_dict and errors_dict[idx].get("auto")):
                errors_dict[idx] = {"original": lines[idx].rstrip('\n'), "fixed": current_lines[idx].rstrip('\n'), "auto": False}
            break

    result = []
    for k in sorted(errors_dict.keys()):
        if lines[k].rstrip('\n') != errors_dict[k]["fixed"] or not errors_dict[k]["auto"]:
            result.append({"idx": k, "original": lines[k].rstrip('\n'), "fixed": errors_dict[k]["fixed"], "auto": errors_dict[k]["auto"]})
    return result
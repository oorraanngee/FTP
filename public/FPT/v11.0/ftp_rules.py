import re

def fix_print_heuristics(line):
    original = line
    
    if line.lstrip().startswith('#'):
        return False, original
        
    line = line.rstrip('\n')
    line = line.replace('«', '"').replace('»', '"')

    # Убираем дикие пробелы в p r i n t
    line = re.sub(r'(?<![a-zA-Z_])p\s+r\s+i\s+n\s+t(?=\s*\()', 'print', line)
    
    typos = ["prnt", "prit", "pnt", "pprint", "printt", "pirnt", "prnit", "pirtn", "orint", "purnt", "pribt", "prinf", "orjbt", "pi", "rint", "pri", "prt", "prent", "printf"]
    typo_pattern = r'^( *\t*)(?:' + '|'.join(typos) + r')(?=[\(\'\"\sА-Яа-яЁё]|$)(.*)$'
    m = re.match(typo_pattern, line)
    if m: line = m.group(1) + "print" + m.group(2)
        
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
    line = re.sub(r'print\(\s*(["\'].*?["\'])\s+([^,)\s].*?)\)', r'print(\1, \2)', line)
    line = re.sub(r'print\(\s*(?<![fF])(["\'])(.*?\{[a-zA-Z_]\w*\}.*?)\1\s*\)', r'print(f\1\2\1)', line)

    m_unquoted = re.search(r'print\(\s*([a-zA-ZА-Яа-яЁё0-9_]+\s+[a-zA-ZА-Яа-яЁё0-9_\s]+)\s*\)', line)
    if m_unquoted:
        words = m_unquoted.group(1).split()
        if not any(kw in words for kw in ('and', 'or', 'not', 'in', 'is', 'if', 'else', 'for', 'while', 'True', 'False', 'None')):
            line = line.replace(m_unquoted.group(1), f'"{m_unquoted.group(1)}"')
    
    if original.endswith('\n'): line += '\n'
    return line != original, line

def fix_keywords_heuristics(line):
    original = line
    
    if line.lstrip().startswith('#'):
        return False, original
        
    line = re.sub(r'\)\s*\{\s*$', '):', line) 
    line = re.sub(r'(?<!\S)else\s*\{?\s*$', 'else:', line) 
    line = re.sub(r'^\s*\}\s*else\b', 'else', line) 
    line = re.sub(r'^(\s*)elsif\b', r'\1elif', line)
    line = re.sub(r'^(\s*)else if\b', r'\1elif', line)
    line = re.sub(r'^(\s*)switch\b', r'\1match', line)
    
    line = re.sub(r'^(\s*)catch\s*\(\s*([a-zA-Z_]\w*)\s+([a-zA-Z_]\w*)\s*\)\s*:?', r'\1except \2 as \3:', line)
    line = re.sub(r'^(\s*)catch\b', r'\1except', line)
    
    line = re.sub(r'^(\s*)exsept\b', r'\1except', line)
    line = re.sub(r'^(\s*)excpet\b', r'\1except', line)
    line = re.sub(r'^(\s*)whlie\b', r'\1while', line)
    
    if '"' not in line and "'" not in line:
        line = re.sub(r'(?<=\s)&&(?=\s)', 'and', line)
        line = re.sub(r'(?<=\s)\|\|(?=\s)', 'or', line)

    if line.lstrip().startswith('def '):
        line = re.sub(r'\b([a-zA-Z_]\w*)\s+(int|str|float|bool|list|dict|tuple|set|Any|Optional)\b(?=[,\)])', r'\1: \2', line)
        line = re.sub(r'(\))\s*([a-zA-Z_]\w*|None)\s*:?(\s*(?:#.*)?)$', r'\1 -> \2:\3', line)

    line = re.sub(r'^(\s*)@?\s*(static|class)[\s_-]*method\b', r'\1@\2method', line)
    line = re.sub(r'^(\s*)@?\s*prop[e_]*rty\b', r'\1@property', line)

    line = re.sub(r'\bdef\s+operator\+\s*\(', 'def __add__(', line)
    line = re.sub(r'\bdef\s+operator-\s*\(', 'def __sub__(', line)
    line = re.sub(r'\bdef\s+operator\*\s*\(', 'def __mul__(', line)
    line = re.sub(r'\bdef\s+operator/\s*\(', 'def __truediv__(', line)
    line = re.sub(r'\bdef\s+operator==\s*\(', 'def __eq__(', line)
    
    line = re.sub(r'\bdef\s+_+init_+\b', 'def __init__', line)
    line = re.sub(r'\bdef\s+init\b', 'def __init__', line)
    
    def add_self(match):
        args = match.group(2).strip()
        return match.group(1) + 'self, ' + args if args else match.group(1) + 'self'
    line = re.sub(r'(\bdef\s+__init__\s*\(\s*)(?!\bself\b)([^)]*)', add_self, line)

    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*=\s*\2\s*$', r'\1self.\2 = \2', line)

    line = re.sub(r'^(\s*)whit\b', r'\1with', line)
    line = re.sub(r'^(\s*)asinc\b', r'\1async', line)
    line = re.sub(r'\bawiat\b', 'await', line)
    line = re.sub(r'\btrue\b', 'True', line)
    line = re.sub(r'\bfalse\b', 'False', line)
    line = re.sub(r'\bnull\b', 'None', line)
    
    def fix_for_in(m):
        if re.search(r'\bin\b', m.group(1)): return m.group(0)
        return f"{m.group(1)} in {m.group(2)}"
    line = re.sub(r'^(\s*for\s+[a-zA-Z0-9_,\s]+?)\s+([a-zA-Z_]\w*\s*\()', fix_for_in, line)
    
    line = re.sub(r'(?<![a-zA-Z])(["\'])(.*?(?:\{[a-zA-Z_][^{}]*\}).*?)\1', r'f\1\2\1', line)
    line = re.sub(r'(\))\s*[а-яА-Яa-zA-Z_]{1,2}\s*$', r'\1', line)
    
    line = re.sub(r'^(\s*)\+\+([a-zA-Z_]\w*)\s*$', r'\1\2 += 1', line)
    line = re.sub(r'^(\s*)--([a-zA-Z_]\w*)\s*$', r'\1\2 -= 1', line)
    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*\+\+\s*$', r'\1\2 += 1', line)
    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*--\s*$', r'\1\2 -= 1', line)

    # --- ИСПРАВЛЕНО: Бесконечный цикл пробелов ---
    code_part = line
    comment_part = ""
    in_str = False
    q_char = None
    for idx, char in enumerate(line):
        if char in "\"'":
            if not in_str:
                in_str = True
                q_char = char
            elif char == q_char:
                in_str = False
        elif char == '#' and not in_str:
            code_part = line[:idx]
            comment_part = line[idx:]
            break
            
    stripped_code = code_part.rstrip('\n\r')
    if stripped_code:
        stripped_clean = stripped_code.rstrip() # Полностью очищаем от пробелов справа!
        if stripped_clean.count('(') > stripped_clean.count(')'):
            stripped_clean += ')'
        elif stripped_clean.count('[') > stripped_clean.count(']'):
            stripped_clean += ']'
        elif stripped_clean.count('{') > stripped_clean.count('}'):
            stripped_clean += '}'
            
        if comment_part:
            line = stripped_clean + '  ' + comment_part # Строго 2 пробела, больше не размножается
        else:
            line = stripped_clean + '\n'
            
        if not line.endswith('\n'):
            line += '\n'

    return line != original, line
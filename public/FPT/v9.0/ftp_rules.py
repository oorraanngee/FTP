import re

def fix_print_heuristics(line):
    original = line
    line = line.rstrip('\n')
    line = line.replace('«', '"').replace('»', '"')
    
    typos = ["prnt", "prit", "pnt", "pprint", "printt", "pirnt", "prnit", "pirtn", "orint", "purnt", "pribt", "prinf", "orjbt", "pi", "rint", "pri", "prt", "zkute", "зрт"]
    typo_pattern = r'^( *\t*)(?:' + '|'.join(typos) + r')(?=[\(\'\"\sА-Яа-яЁё]|$)(.*)$'
    m = re.match(typo_pattern, line)
    if m: line = m.group(1) + "print" + m.group(2)
        
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
    
    if original.endswith('\n'): line += '\n'
    return line != original, line

def fix_keywords_heuristics(line):
    original = line
    
    # Синтаксис других языков
    line = re.sub(r'\)\s*\{\s*$', '):', line) 
    line = re.sub(r'(?<!\S)else\s*\{?\s*$', 'else:', line) 
    line = re.sub(r'^\s*\}\s*else\b', 'else', line) 
    line = re.sub(r'^(\s*)elsif\b', r'\1elif', line)
    line = re.sub(r'^(\s*)else if\b', r'\1elif', line)
    line = re.sub(r'^(\s*)switch\b', r'\1match', line)
    
    # C++ ООП операторы -> Python dunder-методы
    line = re.sub(r'\bdef operator\+\s*\(', 'def __add__(', line)
    line = re.sub(r'\bdef operator-\s*\(', 'def __sub__(', line)
    line = re.sub(r'\bdef operator\*\s*\(', 'def __mul__(', line)
    line = re.sub(r'\bdef operator/\s*\(', 'def __truediv__(', line)
    line = re.sub(r'\bdef operator==\s*\(', 'def __eq__(', line)
    
    # Ошибки в dunder-методах (_init_ вместо __init__)
    line = re.sub(r'\bdef _init_\b', 'def __init__', line)
    line = re.sub(r'\bdef _str_\b', 'def __str__', line)
    
    # Забытый self при присваивании (например: speed = speed -> self.speed = speed)
    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*=\s*\2\s*$', r'\1self.\2 = \2', line)

    # Опечатки
    line = re.sub(r'^(\s*)whit\b', r'\1with', line)
    line = re.sub(r'^(\s*)asinc\b', r'\1async', line)
    line = re.sub(r'\bawiat\b', 'await', line)
    line = re.sub(r'^(\s*)improt\b', r'\1import', line)
    line = re.sub(r'^(\s*)retrun\b', r'\1return', line)
    
    # Убираем объявления JS/C#
    line = re.sub(r'^(\s*)(?:var|let|const|dynamic)\s+([a-zA-Z_]\w*\s*(?:=.*)?)$', r'\1\2', line)
    
    # Реестр и префиксы
    line = re.sub(r'\btrue\b', 'True', line)
    line = re.sub(r'\bfalse\b', 'False', line)
    line = re.sub(r'\bnull\b', 'None', line)
    line = re.sub(r'(?<![a-zA-Z])(["\'])(.*?(?:\{[a-zA-Z_][^{}]*\}).*?)\1', r'f\1\2\1', line)

    # Мусор от русской раскладки
    line = re.sub(r'(\))\s*[а-яА-Яa-zA-Z_]{1,2}\s*$', r'\1', line)
    
    # Забытый инкремент/декремент (++ / --)
    line = re.sub(r'^(\s*)\+\+([a-zA-Z_]\w*)\s*$', r'\1\2 += 1', line)
    line = re.sub(r'^(\s*)--([a-zA-Z_]\w*)\s*$', r'\1\2 -= 1', line)

    return line != original, line
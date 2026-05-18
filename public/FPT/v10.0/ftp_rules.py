import re

def fix_print_heuristics(line):
    original = line
    line = line.rstrip('\n')
    line = line.replace('«', '"').replace('»', '"')
    
    typos = ["prnt", "prit", "pnt", "pprint", "printt", "pirnt", "prnit", "pirtn", "orint", "purnt", "pribt", "prinf", "orjbt", "pi", "rint", "pri", "prt"]
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
    line = re.sub(r'print\(\s*(["\'].*?["\'])\s+([^,)\s].*?)\)', r'print(\1, \2)', line)
    line = re.sub(r'print\(\s*(?<![fF])(["\'])(.*?\{[a-zA-Z_]\w*\}.*?)\1\s*\)', r'print(f\1\2\1)', line)
    
    if original.endswith('\n'): line += '\n'
    return line != original, line

def fix_keywords_heuristics(line):
    original = line
    
    # 1. Синтаксис других языков (JS, C++, Java)
    line = re.sub(r'\)\s*\{\s*$', '):', line) 
    line = re.sub(r'(?<!\S)else\s*\{?\s*$', 'else:', line) 
    line = re.sub(r'^\s*\}\s*else\b', 'else', line) 
    line = re.sub(r'^(\s*)elsif\b', r'\1elif', line)
    line = re.sub(r'^(\s*)else if\b', r'\1elif', line)
    line = re.sub(r'^(\s*)switch\b', r'\1match', line)
    
    # Java/JS catch -> Python except
    line = re.sub(r'^(\s*)catch\s*\(\s*([a-zA-Z_]\w*)\s+([a-zA-Z_]\w*)\s*\)\s*:?', r'\1except \2 as \3:', line)
    line = re.sub(r'^(\s*)catch\b', r'\1except', line)
    
    # Операторы && и || (если они не внутри строк)
    if '"' not in line and "'" not in line:
        line = re.sub(r'(?<=\s)&&(?=\s)', 'and', line)
        line = re.sub(r'(?<=\s)\|\|(?=\s)', 'or', line)

    # 2. ООП и Декораторы
    # Ловит @static-method, static_method, @ classmethod и т.д.
    line = re.sub(r'^(\s*)@?\s*(static|class)[\s_-]*method\b', r'\1@\2method', line)
    line = re.sub(r'^(\s*)@?\s*prop[e_]*rty\b', r'\1@property', line)

    # C++ ООП операторы -> Python dunder-методы
    line = re.sub(r'\bdef\s+operator\+\s*\(', 'def __add__(', line)
    line = re.sub(r'\bdef\s+operator-\s*\(', 'def __sub__(', line)
    line = re.sub(r'\bdef\s+operator\*\s*\(', 'def __mul__(', line)
    line = re.sub(r'\bdef\s+operator/\s*\(', 'def __truediv__(', line)
    line = re.sub(r'\bdef\s+operator==\s*\(', 'def __eq__(', line)
    
    # Ошибки в dunder-методах (_init_ вместо __init__)
    line = re.sub(r'\bdef\s+_+init_+\b', 'def __init__', line)
    line = re.sub(r'\bdef\s+init\b', 'def __init__', line)
    
    # Забытый self в __init__! Ищет def __init__(args) без слова self
    def add_self(match):
        args = match.group(2).strip()
        return match.group(1) + 'self, ' + args if args else match.group(1) + 'self'
    line = re.sub(r'(\bdef\s+__init__\s*\(\s*)(?!\bself\b)([^)]*)', add_self, line)

    # Забытый self при присваивании (speed = speed -> self.speed = speed)
    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*=\s*\2\s*$', r'\1self.\2 = \2', line)

    # 3. Опечатки и реестр
    line = re.sub(r'^(\s*)whit\b', r'\1with', line)
    line = re.sub(r'^(\s*)asinc\b', r'\1async', line)
    line = re.sub(r'\bawiat\b', 'await', line)
    line = re.sub(r'\btrue\b', 'True', line)
    line = re.sub(r'\bfalse\b', 'False', line)
    line = re.sub(r'\bnull\b', 'None', line)
    
    # Забытая f перед строкой с {}
    line = re.sub(r'(?<![a-zA-Z])(["\'])(.*?(?:\{[a-zA-Z_][^{}]*\}).*?)\1', r'f\1\2\1', line)

    # Мусор от русской раскладки в конце строки (например: print(123)ы)
    line = re.sub(r'(\))\s*[а-яА-Яa-zA-Z_]{1,2}\s*$', r'\1', line)
    
    # Забытый инкремент/декремент (++ / --)
    line = re.sub(r'^(\s*)\+\+([a-zA-Z_]\w*)\s*$', r'\1\2 += 1', line)
    line = re.sub(r'^(\s*)--([a-zA-Z_]\w*)\s*$', r'\1\2 -= 1', line)
    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*\+\+\s*$', r'\1\2 += 1', line)
    line = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*--\s*$', r'\1\2 -= 1', line)

    return line != original, line
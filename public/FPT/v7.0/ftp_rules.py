import re

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

def fix_keywords_heuristics(line):
    """Исправляет частые опечатки в ключевых словах Python и операторах из других языков"""
    original = line
    
    # elsif / else if -> elif
    line = re.sub(r'^(\s*)elsif\b', r'\1elif', line)
    line = re.sub(r'^(\s*)else if\b', r'\1elif', line)
    
    # whit -> with
    line = re.sub(r'^(\s*)whit\b', r'\1with', line)
    
    # switch -> match (Python 3.10+)
    line = re.sub(r'^(\s*)switch\b', r'\1match', line)
    
    return line != original, line

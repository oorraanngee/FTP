import os
import sys
import time

# Цвета для вывода
COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "ORANGE": "\033[33m",
    "RESET": "\033[0m"
}

if os.name == 'nt':
    os.system('color')

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
        bar = f"{dash_color}{dashes}{COLORS['RESET']} {spinner_color}{spin}{COLORS['RESET']}"
        sys.stdout.write(f"\rПрогресс: {bar}")
        sys.stdout.flush()
        time.sleep(duration / steps)
    bar = f"{dash_color}{'-' * steps}{COLORS['RESET']} {spinner_color}+{COLORS['RESET']}"
    sys.stdout.write(f"\rПрогресс: {bar}\n")
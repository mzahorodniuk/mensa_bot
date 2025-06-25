# Use this script to auto-reload your Python bot on code changes (like nodemon)
# Usage: python autoreload.py
import subprocess
import sys
import time
import os

def run_bot():
    return subprocess.Popen([sys.executable, 'src/bot.py'])

def watch(paths, interval=1):
    mtimes = {}
    for path in paths:
        mtimes[path] = os.path.getmtime(path)
    while True:
        time.sleep(interval)
        for path in paths:
            new_mtime = os.path.getmtime(path)
            if new_mtime != mtimes[path]:
                return True
    return False

if __name__ == '__main__':
    paths = ['src/bot.py', 'src/menu_parser.py', 'config/config.py']
    while True:
        proc = run_bot()
        watch(paths)
        proc.terminate()
        print('Code changed. Restarting bot...')

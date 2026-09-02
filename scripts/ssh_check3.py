# -*- coding: utf-8 -*-
"""Check server status and diagnose issues"""
import paramiko
import sys

SSH_HOST = "186.244.251.12"
SSH_USER = "root"
SSH_PASS = "Aa13910828867@&"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

print("=" * 60)
print("1. Bot Service Status")
print("=" * 60)
out, err = run("systemctl status tg-search-bot --no-pager")
print(out or err)

print("\n" + "=" * 60)
print("2. Admin Service Status")
print("=" * 60)
out, err = run("systemctl status tg-search-admin --no-pager")
print(out or err)

print("\n" + "=" * 60)
print("3. Latest Bot Logs (last 30 lines)")
print("=" * 60)
out, err = run("journalctl -u tg-search-bot -n 30 --no-pager")
print(out or err)

print("\n" + "=" * 60)
print("4. Bot Log File (last 30 lines)")
print("=" * 60)
out, err = run("tail -30 /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null")
print(out or err)

print("\n" + "=" * 60)
print("5. Git Status")
print("=" * 60)
out, err = run("cd /www/wwwroot/tg-search-bot && git log --oneline -5")
print(out or err)

print("\n" + "=" * 60)
print("6. DB Config Check (CRYPTO_SECRET, ADMIN)")
print("=" * 60)
out, err = run("cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "
               "import sqlite3; "
               "conn=sqlite3.connect('./data/tg_search.db'); "
               "rows=conn.execute('SELECT setting_key, length(setting_value) as val_len, value_type, is_encrypted FROM system_settings WHERE setting_key IN (\"CRYPTO_SECRET\",\"ADMIN_USERNAME\",\"ADMIN_PASSWORD\").fetchall(); "
               "for r in rows: print(r)")
print(out or err)

print("\n" + "=" * 60)
print("7. All system_settings keys")
print("=" * 60)
out, err = run("cd /www/wwwroot/tg-search-bot && ./venv/bin/python -c "
               "import sqlite3; "
               "conn=sqlite3.connect('./data/tg_search.db'); "
               "rows=conn.execute('SELECT setting_key, value_type, is_encrypted FROM system_settings ORDER BY setting_key').fetchall(); "
               "for r in rows: print(r[0], r[1], r[2])")
print(out or err)

print("\n" + "=" * 60)
print("8. Restart count")
print("=" * 60)
out, err = run("systemctl show tg-search-bot --property=RestartCount --no-pager")
print(out or err)

print("\n" + "=" * 60)
print("9. Check bot process is alive")
print("=" * 60)
out, err = run("pgrep -f 'python -u main.py' | head -5")
print(out or err)

print("\n" + "=" * 60)
print("10. Check latest bot log for errors")
print("=" * 60)
out, err = run("grep -i 'error\\|fail\\|traceback' /www/wwwroot/tg-search-bot/logs/bot_2026-09-02.log 2>/dev/null | tail -10")
print(out or err)

ssh.close()
print("\nDone!")

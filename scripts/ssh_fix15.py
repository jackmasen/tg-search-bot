# -*- coding: utf-8 -*-
"""Fix admin credentials and test"""
import paramiko

SSH_HOST = "186.244.251.12"
SSH_USER = "root"
SSH_PASS = "Aa13910828867@&"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

# 1. Check what's in DB for ADMIN_PASSWORD
print("=" * 60)
print("1. Check ADMIN_PASSWORD in DB")
print("=" * 60)
out, err = run("cat > /tmp/check_pwd.py << 'PYEOF'\nimport sqlite3\nconn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')\nrows = conn.execute('SELECT setting_key, setting_value, is_encrypted, value_type FROM system_settings WHERE setting_key IN (\"ADMIN_USERNAME\",\"ADMIN_PASSWORD\")').fetchall()\nfor r in rows:\n    print(r[0], '| enc=' + str(r[2]) + '| type=' + r[3] + '| val=' + (r[1][:50] if r[1] else 'EMPTY'))\nconn.close()\nPYEOF\npython3 /tmp/check_pwd.py")
print(out or err)

# 2. Decrypt using the same method as the app
print("\n" + "=" * 60)
print("2. Check Decrypted Values")
print("=" * 60)
out, err = run("cat > /tmp/check_dec.py << 'PYEOF'\nimport sqlite3\nimport base64\nimport hashlib\nfrom cryptography.fernet import Fernet\nconn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')\nrows = conn.execute('SELECT setting_key, setting_value, is_encrypted, value_type FROM system_settings WHERE setting_key IN (\"ADMIN_USERNAME\",\"ADMIN_PASSWORD\",\"CRYPTO_SECRET\")').fetchall()\nfor r in rows:\n    key, val, enc, vtype = r\n    print(f'{key}: enc={enc}, type={vtype}, val_preview={val[:60] if val else \"EMPTY\"}')\n    if enc and val and val.startswith('ENC:'):\n        try:\n            # Get CRYPTO_SECRET\n            cs_row = conn.execute('SELECT setting_value FROM system_settings WHERE setting_key=\"CRYPTO_SECRET\"').fetchone()\n            cs = cs_row[0] if cs_row else 'fallback_no_secret_2024'\n            raw = hashlib.sha256(cs.encode()).digest()\n            fkey = base64.urlsafe_b64encode(raw)\n            f = Fernet(fkey)\n            decrypted = f.decrypt(val[4:].encode()).decode()\n            print(f'  -> Decrypted: {decrypted[:30]}...')\n        except Exception as e:\n            print(f'  -> Decrypt failed: {e}')\nconn.close()\nPYEOF\npython3 /tmp/check_dec.py")
print(out or err)

# 3. Fix: properly set admin credentials (plain text, not encrypted)
print("\n" + "=" * 60)
print("3. Fix Admin Credentials (Plain Text)")
print("=" * 60)
out, err = run("cat > /tmp/fix_pwd.py << 'PYEOF'\nimport sqlite3\nconn = sqlite3.connect('/www/wwwroot/tg-search-bot/data/tg_search.db')\nc = conn.cursor()\n# Delete any existing entries and reinsert as plain text\nc.execute('DELETE FROM system_settings WHERE setting_key IN (\"ADMIN_USERNAME\",\"ADMIN_PASSWORD\")')\nc.execute('INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at) VALUES (\"ADMIN_USERNAME\", \"admin\", \"str\", 0, \"后台登录账号\", CURRENT_TIMESTAMP)')\nc.execute('INSERT INTO system_settings (setting_key, setting_value, value_type, is_encrypted, description, updated_at) VALUES (\"ADMIN_PASSWORD\", \"Admin@123456\", \"str\", 0, \"后台登录密码\", CURRENT_TIMESTAMP)')\nconn.commit()\nrows = c.execute('SELECT setting_key, setting_value, is_encrypted FROM system_settings WHERE setting_key IN (\"ADMIN_USERNAME\",\"ADMIN_PASSWORD\")').fetchall()\nprint('Fixed:', rows)\nconn.close()\nprint('Done!')\nPYEOF\npython3 /tmp/fix_pwd.py")
print(out or err)

# 4. Restart admin service
print("\n" + "=" * 60)
print("4. Restart Admin Service")
print("=" * 60)
out, err = run("systemctl restart tg-search-admin && sleep 2 && systemctl status tg-search-admin --no-pager | head -6")
print(out or err)

# 5. Test login
print("\n" + "=" * 60)
print("5. Test Admin Login")
print("=" * 60)
out, err = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"')
print(out or err)

# 6. Also test with default credentials
print("\n" + "=" * 60)
print("6. Test Default Login (admin/demo123456)")
print("=" * 60)
out, err = run('curl -s -X POST http://127.0.0.1:8001/api/admin/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"demo123456\"}"')
print(out or err)

# 7. Check bot status
print("\n" + "=" * 60)
print("7. Bot Status")
print("=" * 60)
out, err = run("systemctl status tg-search-bot --no-pager | head -8")
print(out or err)

ssh.close()
print("\nDone!")

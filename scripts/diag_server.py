# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Check listening ports
_, out1, _ = client.exec_command('ss -tlnp')
print("=== Ports ===")
print(out1.read().decode('utf-8', errors='replace'))

# Check services
_, out2, _ = client.exec_command('systemctl list-units --type=service --all | grep -i tg')
print("=== Services ===")
print(out2.read().decode('utf-8', errors='replace'))

# Check running processes
_, out3, _ = client.exec_command('ps aux | grep python')
print("=== Python processes ===")
print(out3.read().decode('utf-8', errors='replace'))

# Try curl to port 8001
_, out4, err4 = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/api/admin/check_auth?session_id=test 2>&1')
print("=== Port 8001 status ===")
print(out4.read().decode('utf-8', errors='replace').strip())
print(err4.read().decode('utf-8', errors='replace').strip())

client.close()

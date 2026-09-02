# -*- coding: utf-8 -*-
import paramiko, json, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

# Test the bot_push_test API
stdin, stdout, stderr = client.exec_command(
    'curl -s -X POST http://127.0.0.1:8001/api/admin/ops/bot_push_test '
    '-H "Content-Type: application/json" -d \'{}\' 2>&1'
)
print("Response:", stdout.read().decode('utf-8', errors='replace').strip())
print("Error:", stderr.read().decode('utf-8', errors='replace').strip())

# Check if server is listening
stdin2, stdout2, stderr2 = client.exec_command('ss -tlnp | grep 8000')
print("Port 8000:", stdout2.read().decode('utf-8', errors='replace').strip())

client.close()

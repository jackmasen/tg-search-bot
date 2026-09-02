import paramiko
import base64

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

# Use base64 to avoid escaping issues
script = '''
import socksio
print("socksio version:", getattr(socksio, "__version__", "unknown"))
print("dir:", [x for x in dir(socksio) if not x.startswith("_")])
from socksio import socks5
print("socks5:", dir(socks5))
'''
encoded = base64.b64encode(script.encode()).decode()
run(f'echo {encoded} | base64 -d > /tmp/check.py')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/check.py 2>&1')
print(f"socksio check: {out}")
if err: print(f"err: {err}")

# Check telethon proxy handling
script2 = '''
import inspect
from telethon.network import MTProtoProxySampler
src = inspect.getsource(MTProtoProxySampler)
# Find proxy-related lines
for line in src.split("\\n"):
    if "socks" in line.lower() or "proxy" in line.lower():
        print(line)
'''
encoded2 = base64.b64encode(script2.encode()).decode()
run(f'echo {encoded2} | base64 -d > /tmp/check2.py')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/check2.py 2>&1')
print(f"telethon proxy: {out}")
if err: print(f"err: {err}")

# Check how telethon accepts proxy
script3 = '''
import inspect
from telethon import TelegramClient
sig = inspect.signature(TelegramClient.__init__)
for name, param in sig.parameters.items():
    if name in ("proxy",):
        print(f"{name}: {param.annotation} = {param.default}")
# Also check the source
src = inspect.getsource(TelegramClient.__init__)
for line in src.split("\\n")[:30]:
    if "proxy" in line.lower():
        print(line)
'''
encoded3 = base64.b64encode(script3.encode()).decode()
run(f'echo {encoded3} | base64 -d > /tmp/check3.py')
out, err = run('/www/wwwroot/tg-search-bot/venv/bin/python3 /tmp/check3.py 2>&1')
print(f"telegram proxy sig: {out}")
if err: print(f"err: {err}")

client.close()
print('DONE')

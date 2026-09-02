import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=10)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('=== Check crawler_accounts table ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \".schema crawler_accounts\"")
print(out)

print('=== Check account data ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT * FROM crawler_accounts;\"")
print(out)

print('=== Check account columns ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"PRAGMA table_info(crawler_accounts);\"")
print(out)

print('=== Check full account JSON ===')
out, _ = run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT id, phone, data_json FROM crawler_accounts;\"")
print(out)

client.close()
print('DONE')

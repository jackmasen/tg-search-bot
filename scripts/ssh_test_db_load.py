import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n>>> {desc or cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        for line in out.splitlines()[:30]:
            print(f"  {line}")
    if err:
        for line in err.splitlines()[:10]:
            print(f"  ERR: {line}")
    return out, err

# 查看服务器config.py的版本号和BOT_TOKEN相关代码
run("grep -n 'APP_VERSION\\|BOT_TOKEN\\|validate' /www/wwwroot/tg-search-bot/app/config.py | head -20", "服务器config.py关键行")

# 查看服务器main.py的完整内容对比
run("wc -l /www/wwwroot/tg-search-bot/main.py /www/wwwroot/tg-search-bot/server.py /www/wwwroot/tg-search-bot/app/config.py", "文件大小")

# 检查数据库中TG_BOT_TOKEN的实际值（前20字符）
run("sqlite3 /www/wwwroot/tg-search-bot/data/tg_search.db \"SELECT setting_key, substr(setting_value,1,30) as val_preview FROM system_settings WHERE setting_key='TG_BOT_TOKEN';\"", "DB中TG_BOT_TOKEN预览")

# 手动测试从DB加载配置
run("cd /www/wwwroot/tg-search-bot && source venv/bin/activate && python -c \"\nfrom app.config import Config\nfrom app.database import get_db\nfrom app.admin.system_settings_manager import load_all_settings_from_db\nimport asyncio\nasync def test():\n    async with get_db() as db:\n        vals = await load_all_settings_from_db(db)\n        print('DB values keys:', list(vals.keys())[:10])\n        print('BOT_TOKEN from DB:', vals.get('TG_BOT_TOKEN','NOT FOUND')[:20] if vals.get('TG_BOT_TOKEN') else 'NONE')\n        Config.apply_overrides(vals)\n        print('Config.BOT_TOKEN after override:', Config.BOT_TOKEN[:20] if Config.BOT_TOKEN else 'EMPTY')\nasyncio.run(test())\n\" 2>&1", "手动测试DB配置加载")

client.close()

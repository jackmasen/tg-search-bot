"""
ssh_deploy_fix.py
通过 SSH 直接部署修复后的 server.py 到远程服务器
"""
import paramiko
import time
import base64

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd, desc=""):
    print(f"\n{'='*60}")
    print(f"▶ {desc}")
    print(f"  命令: {cmd}")
    print('='*60)
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        if out:
            print(f"【输出】\n{out}")
        if err:
            print(f"【错误】\n{err}")
        return out, err
    except Exception as e:
        print(f"【异常】{e}")
        return "", str(e)

PROJECT = '/www/wwwroot/tg-search-bot'

print("\n" + "="*60)
print("🚀 直接部署 CORSMiddleware 修复到远程服务器")
print("="*60)

# 1. 先检查远程 server.py 的当前状态
run(f'cd {PROJECT} && grep -n "from fastapi" server.py | head -10', '检查远程导入语句')
run(f'cd {PROJECT} && grep -n "CORSMiddleware" server.py', '检查 CORSMiddleware 使用位置')

# 2. 用 sed 直接在远程服务器上添加导入语句
# 在 "from fastapi.staticfiles import StaticFiles" 后面添加 CORSMiddleware 导入
run(
    f'cd {PROJECT} && sed -i "/from fastapi.staticfiles import StaticFiles/a from fastapi.middleware.cors import CORSMiddleware" server.py && echo "导入已添加"',
    '在远程 server.py 添加 CORSMiddleware 导入'
)

# 3. 验证导入已添加
run(f'cd {PROJECT} && grep -n "cors" server.py', '验证导入语句')

# 4. Python 语法检查
run(f'cd {PROJECT} && venv/bin/python -m py_compile server.py && echo "语法检查通过"', 'Python 语法检查')

# 5. 清除 Python 缓存
run(f'cd {PROJECT} && find . -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; find . -name "*.pyc" -delete 2>/dev/null; echo 缓存已清除', '清除 Python 字节码缓存')

# 6. 重启服务
run('systemctl restart tg-search-admin', '重启 Admin 服务')

print("\n⏳ 等待 5 秒让服务启动...")
time.sleep(5)

# 7. 验证服务状态
run('systemctl is-active tg-search-admin && echo "Admin: OK" || echo "Admin: FAIL"', '验证 Admin 服务状态')
run('systemctl status tg-search-admin --no-pager | head -12', 'Admin 服务状态详情')

# 8. 查看最新日志
run(f'tail -20 {PROJECT}/logs/admin_stderr.log', '查看错误日志（最后20行）')
run('journalctl -u tg-search-admin --no-pager -n 15', 'systemd 日志')

# 9. 测试健康检查和 Admin 页面
run('curl -s http://127.0.0.1:8001/health', '测试健康检查')
run('curl -s -o /dev/null -w "Admin HTTP状态: %{http_code}\n" http://127.0.0.1:8001/admin', '测试 Admin 页面')

# 10. 检查端口
run('ss -tlnp | grep 8001', '检查端口 8001 监听')

# 11. 检查 git 版本（确认代码版本）
run(f'cd {PROJECT} && grep "APP_VERSION" app/config.py', '确认版本号')

client.close()

print("\n" + "="*60)
print("✅ 部署完成！")
print("="*60)

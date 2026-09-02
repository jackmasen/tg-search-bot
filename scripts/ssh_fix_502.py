import paramiko
import time

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

# ============================================================
# 第一阶段：诊断
# ============================================================
print("\n" + "="*60)
print("🔍 TG Search Bot 502错误诊断与修复")
print("="*60)

# 1. 检查两个服务状态
run('systemctl status tg-search-bot --no-pager', '检查 Bot 服务状态')
run('systemctl status tg-search-admin --no-pager', '检查 Admin 服务状态')

# 2. 检查 Nginx 状态
run('systemctl status nginx --no-pager', '检查 Nginx 状态')

# 3. 查看 Admin 服务错误日志
run('tail -100 /www/wwwroot/tg-search-bot/logs/admin_stderr.log', '查看 Admin 错误日志')
run('tail -50 /www/wwwroot/tg-search-bot/logs/admin_stdout.log', '查看 Admin 输出日志')

# 4. 查看 Nginx 错误日志
run('tail -50 /var/log/nginx/error.log', '查看 Nginx 错误日志')

# 5. 检查端口监听
run('ss -tlnp | grep -E "8001|80"', '检查端口监听')

# 6. 直接测试后端
run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health', '测试后端健康检查')
run('curl -s http://127.0.0.1:8001/health', '获取健康检查详情')

# ============================================================
# 第二阶段：修复
# ============================================================
print("\n" + "="*60)
print("🔧 开始修复")
print("="*60)

# 7. 拉取最新代码
run('cd /www/wwwroot/tg-search-bot && git pull origin main', '拉取最新代码')

# 8. 检查语法
run('cd /www/wwwroot/tg-search-bot && python -m py_compile server.py && echo "Syntax OK"', '检查 server.py 语法')

# 9. 重启服务
run('systemctl restart tg-search-admin', '重启 Admin 服务')
run('systemctl restart tg-search-bot', '重启 Bot 服务')

# 等待服务启动
print("\n⏳ 等待 5 秒让服务启动...")
time.sleep(5)

# 10. 验证服务状态
run('systemctl is-active tg-search-admin && echo "Admin: OK" || echo "Admin: FAIL"', '验证 Admin 服务')
run('systemctl is-active tg-search-bot && echo "Bot: OK" || echo "Bot: FAIL"', '验证 Bot 服务')

# 11. 查看最新日志
run('journalctl -u tg-search-admin --no-pager -n 30', '查看 Admin 最新日志')
run('journalctl -u tg-search-bot --no-pager -n 30', '查看 Bot 最新日志')

# ============================================================
# 第三阶段：验证
# ============================================================
print("\n" + "="*60)
print("✅ 验证修复结果")
print("="*60)

# 12. 测试健康检查
run('curl -s http://127.0.0.1:8001/health', '测试健康检查')

# 13. 测试 Admin 页面
run('curl -s -o /dev/null -w "Admin页面HTTP状态: %{http_code}\n" http://127.0.0.1:8001/admin', '测试Admin页面')

# 14. 测试 Nginx 反代（如果有配置）
run('curl -s -o /dev/null -w "Nginx代理HTTP状态: %{http_code}\n" http://127.0.0.1/admin 2>/dev/null || echo "Nginx测试跳过"', '测试Nginx代理')

# 15. 最终服务状态
run('systemctl status tg-search-admin --no-pager | head -15', '最终Admin状态')
run('systemctl status tg-search-bot --no-pager | head -15', '最终Bot状态')

client.close()

print("\n" + "="*60)
print("🎉 诊断与修复完成！")
print("="*60)
print("\n请检查上面的输出，确认：")
print("1. Admin 服务是否正常运行 (应显示 active (running))")
print("2. 健康检查是否返回 OK")
print("3. Admin 页面 HTTP 状态是否为 200")
print("\n如果仍有问题，请提供:")
print("- journalctl -u tg-search-admin --no-pager -n 50")
print("- tail -50 /www/wwwroot/tg-search-bot/logs/admin_stderr.log")

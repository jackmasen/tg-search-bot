import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('186.244.251.12', username='root', password='Aa13910828867@&', timeout=15)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    return stdout.read().decode(), stderr.read().decode()

# 检查 Nginx 配置
print('=== Nginx 站点配置 ===')
out, _ = run('ls /www/server/panel/vhost/nginx/*.conf 2>/dev/null | head -5')
print(out)

# 查看反代配置
print('=== 查找反代配置 ===')
out, _ = run('grep -rl "8001" /www/server/panel/vhost/nginx/ 2>/dev/null')
print(out)

# 检查端口 8001 是否监听
print('=== 端口监听 ===')
out, _ = run('ss -tlnp | grep 8001')
print(out)

# 测试后台访问
print('=== 测试后台访问 ===')
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/admin')
print(f'\n本地访问: {out}')

# 测试健康检查
print('=== 健康检查 ===')
out, _ = run('curl -s http://127.0.0.1:8001/health')
print(f'\n{out}')

# 检查 Nginx 配置测试
print('=== Nginx 配置测试 ===')
out, _ = run('nginx -t 2>&1')
print(out)

client.close()
print('\n=== 验证完成 ===')

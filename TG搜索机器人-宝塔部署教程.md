# TG搜索机器人 v1.0.4 - 宝塔面板部署教程

## 涓€銆佺幆澧冭姹?
### 1.1 鏈嶅姟鍣ㄩ厤缃?- **鎿嶄綔绯荤粺**锛欳entOS 7.9+ / Ubuntu 20.04+ / Debian 10+
- **CPU**锛?鏍稿強浠ヤ笂
- **鍐呭瓨**锛?GB鍙婁互涓?- **纭洏**锛氳嚦灏?20GB 鍙敤绌洪棿
- **甯﹀**锛?Mbps鍙婁互涓?
### 1.2 蹇呭缁勪欢
- 瀹濆闈㈡澘 v7.x / v8.x
- Python 3.10+锛堟帹鑽?3.11锛?- Nginx 1.20+
- SQLite 3锛堢郴缁熻嚜甯﹀嵆鍙級

---

## 浜屻€佸疂濉旈潰鏉垮畨瑁?
### 2.1 涓€閿畨瑁呭疂濉?
```bash
# CentOS 瀹夎鍛戒护
yum install -y wget && wget -O install.sh https://download.bt.cn/install/install_6.0.sh && sh install.sh ed8484bec

# Ubuntu 瀹夎鍛戒护
wget -O install.sh https://download.bt.cn/install/install-ubuntu_6.0.sh && sudo bash install.sh ed8484bec

# Debian 瀹夎鍛戒护
wget -O install.sh https://download.bt.cn/install/install-ubuntu_6.0.sh && bash install.sh ed8484bec
```

### 2.2 璁板綍瀹夎淇℃伅
瀹夎瀹屾垚鍚庯紝璇疯褰曚互涓嬩俊鎭細
- 瀹濆闈㈡澘鍦板潃锛堝锛歚http://鏈嶅姟鍣↖P:8888/xxxxx`锛?- 鍒濆璐﹀彿瀵嗙爜
- 瀹夊叏鍏ュ彛璺緞

### 2.3 棣栨鐧诲綍閰嶇疆
1. 娴忚鍣ㄦ墦寮€瀹濆闈㈡澘鍦板潃
2. 杈撳叆鍒濆璐﹀彿瀵嗙爜鐧诲綍
3. 缁戝畾瀹濆瀹樻柟璐﹀彿锛堝彲閫夛級
4. 璁剧疆闈㈡澘瀹夊叏鍏ュ彛璺緞
5. 缁戝畾鏈嶅姟鍣紙鍏嶈垂鐗堝彲璺宠繃锛?
---

## 涓夈€佺幆澧冮厤缃?
### 3.1 瀹夎 Python 绠＄悊鍣?
1. 鐧诲綍瀹濆闈㈡澘
2. 鐐瑰嚮宸︿晶鑿滃崟銆愯蒋浠跺晢搴椼€?3. 鎵惧埌銆怭ython椤圭洰绠＄悊銆戞垨銆怭ython绠＄悊鍣ㄣ€?4. 鐐瑰嚮銆愬畨瑁呫€?
### 3.2 瀹夎 Python 3.11

1. 鎵撳紑銆怭ython绠＄悊鍣ㄣ€?2. 鐐瑰嚮銆愮増鏈鐞嗐€戞爣绛?3. 鎵惧埌 Python 3.11锛岀偣鍑汇€愬畨瑁呫€?4. 绛夊緟瀹夎瀹屾垚

### 3.3 瀹夎 Nginx

1. 鐐瑰嚮宸︿晶鑿滃崟銆愯蒋浠跺晢搴椼€?2. 鎵惧埌銆怤ginx銆?3. 鐐瑰嚮銆愬畨瑁呫€?4. 閫夋嫨銆愭瀬閫熷畨瑁呫€?5. 绛夊緟瀹夎瀹屾垚

### 3.4 瀹夎 SQLite锛堝彲閫夛級

> 绯荤粺榛樿宸茶嚜甯?SQLite锛屾姝ュ彲璺宠繃

```bash
# CentOS
yum install -y sqlite-devel

# Ubuntu/Debian
apt-get install -y sqlite3 libsqlite3-dev
```

---

## 鍥涖€佷笂浼犻」鐩?
### 4.1 涓嬭浇鏈€鏂扮増鏈?
1. 璁块棶椤圭洰鍙戝竷椤佃幏鍙栨渶鏂扮増鏈?2. 涓嬭浇鍘嬬缉鍖?`tg-search-bot-v1.0.3-install.zip`

### 4.2 涓婁紶鍒版湇鍔″櫒

```bash
# 鏂瑰紡涓€锛氫娇鐢ㄥ疂濉旀枃浠剁鐞嗗櫒
# 1. 瀹濆闈㈡澘 鈫?鏂囦欢
# 2. 杩涘叆 /www/wwwroot/ 鐩綍
# 3. 涓婁紶鍘嬬缉鍖?
# 鏂瑰紡浜岋細浣跨敤 SCP 鍛戒护
scp tg-search-bot-v1.0.3-install.zip root@鏈嶅姟鍣↖P:/www/wwwroot/

# 鏂瑰紡涓夛細浣跨敤瀹濆杩滅▼涓嬭浇
# 1. 瀹濆闈㈡澘 鈫?鏂囦欢 鈫?杩滅▼涓嬭浇
# 2. 杈撳叆涓嬭浇閾炬帴
```

### 4.3 瑙ｅ帇椤圭洰

```bash
cd /www/wwwroot/
unzip tg-search-bot-v1.0.4-latest.zip
mv tg-search-bot-v1.0.4 tg-search-bot
cd tg-search-bot
```

### 4.4 璁剧疆鏉冮檺

```bash
chmod -R 755 /www/wwwroot/tg-search-bot
chmod +x /www/wwwroot/tg-search-bot/install.sh
```

---

## 浜斻€侀厤缃?Python 鐜

### 5.1 鍒涘缓铏氭嫙鐜

```bash
cd /www/wwwroot/tg-search-bot

# 鍒涘缓铏氭嫙鐜
python3.11 -m venv venv

# 婵€娲昏櫄鎷熺幆澧?source venv/bin/activate

# 楠岃瘉 Python 鐗堟湰
python --version
# 搴旇緭鍑? Python 3.11.x
```

### 5.2 瀹夎渚濊禆

```bash
cd /www/wwwroot/tg-search-bot

# 婵€娲昏櫄鎷熺幆澧?source venv/bin/activate

# 鍗囩骇 pip锛堝彲閫夛級
pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple

# 瀹夎椤圭洰渚濊禆
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 馃挕 **鎻愮ず**锛氫娇鐢ㄦ竻鍗庨暅鍍忔簮鍙ぇ骞呭姞閫熶緷璧栧畨瑁?
### 5.3 楠岃瘉渚濊禆瀹夎

```bash
source /www/wwwroot/tg-search-bot/venv/bin/activate

# 楠岃瘉鏍稿績渚濊禆
python -c "import fastapi; print('fastapi:', fastapi.__version__)"
python -c "import telethon; print('telethon:', telethon.__version__)"
python -c "import aiosqlite; print('aiosqlite OK')"
python -c "import hdwallet; print('hdwallet OK')"
python -c "import jieba; print('jieba OK')"
python -c "import loguru; print('loguru OK')"
```

### 5.4 閰嶇疆鐜鍙橀噺

```bash
cd /www/wwwroot/tg-search-bot

# 濡傛灉娌℃湁 .env 鏂囦欢锛屼粠妯℃澘澶嶅埗
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || touch .env
fi

# 鐢熸垚瀹夊叏瀵嗛挜
SESSION_SECRET=$(openssl rand -hex 32)
CRYPTO_SECRET=$(openssl rand -hex 32)

# 鍐欏叆瀵嗛挜閰嶇疆
cat >> .env << EOF
SESSION_SECRET=${SESSION_SECRET}
CRYPTO_SECRET=${CRYPTO_SECRET}
EOF

# 璁剧疆鏂囦欢鏉冮檺
chmod 600 .env
```

---

## 鍏€佸疂濉旂珯鐐归厤缃?
### 6.1 鍒涘缓绔欑偣

1. 瀹濆闈㈡澘 鈫?缃戠珯
2. 鐐瑰嚮銆愭坊鍔犵珯鐐广€?3. 濉啓閰嶇疆锛?   - **鍩熷悕**锛氬～鍐欎綘鐨勫煙鍚嶏紙濡?`bot.yourdomain.com`锛夋垨鐣欑┖
   - **鏍圭洰褰?*锛歚/www/wwwroot/tg-search-bot`
   - **PHP鐗堟湰**锛氶€夋嫨銆愮函闈欐€併€?   - **鏁版嵁搴?*锛氫笉鍒涘缓
4. 鐐瑰嚮銆愭彁浜ゃ€?
### 6.2 閰嶇疆鍙嶅悜浠ｇ悊

1. 鍦ㄧ珯鐐瑰垪琛ㄤ腑鐐瑰嚮鍒氬垰鍒涘缓鐨勭珯鐐?2. 鐐瑰嚮銆愯缃€戔啋銆愬弽鍚戜唬鐞嗐€?3. 鐐瑰嚮銆愭坊鍔犲弽鍚戜唬鐞嗐€?
**閰嶇疆淇℃伅锛?*
- **浠ｇ悊鍚嶇О**锛歚tg_search_bot`
- **鐩爣URL**锛歚http://127.0.0.1:8001`
- **鍙戦€佸煙鍚?*锛歚$host`

**楂樼骇閰嶇疆锛堝彲閫夛級锛?*
```nginx
proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 300s;
proxy_send_timeout 300s;
client_max_body_size 100M;
```

4. 鐐瑰嚮銆愭彁浜ゃ€戜繚瀛?
### 6.3 閰嶇疆 SSL 璇佷功锛堟帹鑽愶級

1. 绔欑偣璁剧疆 鈫?SSL
2. 閫夋嫨銆怢et's Encrypt銆戯紙鍏嶈垂锛夋垨銆愬叾浠栬瘉涔︺€?3. 鍕鹃€夊煙鍚?4. 鐐瑰嚮銆愮敵璇枫€?5. 鐢宠鎴愬姛鍚庡紑鍚€愬己鍒禜TTPS銆?
---

## 涓冦€侀厤缃湇鍔″畧鎶?
### 7.1 鍒涘缓鍚姩鑴氭湰

```bash
cat > /www/wwwroot/tg-search-bot/start.sh << 'EOF'
#!/bin/bash
cd /www/wwwroot/tg-search-bot
source venv/bin/activate
export PYTHONUNBUFFERED=1
export PATH="/www/wwwroot/tg-search-bot/venv/bin:$PATH"
exec python -u demo_server.py
EOF

chmod +x /www/wwwroot/tg-search-bot/start.sh
```

### 7.2 鏂瑰紡涓€锛氬疂濉?PM2 绠＄悊鍣紙鎺ㄨ崘锛?
1. 瀹濆闈㈡澘 鈫?杞欢鍟嗗簵 鈫?瀹夎銆怭M2绠＄悊鍣ㄣ€?2. 鎵撳紑 PM2 绠＄悊鍣?3. 鐐瑰嚮銆愭坊鍔犻」鐩€?
**閰嶇疆淇℃伅锛?*
- **椤圭洰鍚嶇О**锛歚tg-search-bot`
- **鍚姩鏂囦欢**锛歚/www/wwwroot/tg-search-bot/start.sh`
- **杩愯鐩綍**锛歚/www/wwwroot/tg-search-bot`
- **杩愯妯″紡**锛歚fork`
- **鏃ュ織璺緞**锛歚/www/wwwroot/tg-search-bot/logs/`

4. 鐐瑰嚮銆愭彁浜ゃ€?5. 鍦?PM2 鍒楄〃涓偣鍑汇€愬惎鍔ㄣ€?
### 7.3 鏂瑰紡浜岋細Systemd 鏈嶅姟锛堟洿绋冲畾锛?
```bash
# 鍒涘缓鏈嶅姟鏂囦欢
cat > /etc/systemd/system/tg-search-bot.service << 'SVC'
[Unit]
Description=TG Search Bot Service v1.0.4
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/tg-search-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/www/wwwroot/tg-search-bot/start.sh
Restart=always
RestartSec=5
StandardOutput=append:/www/wwwroot/tg-search-bot/logs/stdout.log
StandardError=append:/www/wwwroot/tg-search-bot/logs/stderr.log

[Install]
WantedBy=multi-user.target
SVC

# 鍒涘缓鏃ュ織鐩綍
mkdir -p /www/wwwroot/tg-search-bot/logs

# 閲嶆柊鍔犺浇 systemd
systemctl daemon-reload

# 璁剧疆寮€鏈鸿嚜鍚?systemctl enable tg-search-bot

# 鍚姩鏈嶅姟
systemctl start tg-search-bot

# 鏌ョ湅鏈嶅姟鐘舵€?systemctl status tg-search-bot
```

### 7.4 鏈嶅姟绠＄悊鍛戒护

```bash
# 鍚姩鏈嶅姟
systemctl start tg-search-bot

# 鍋滄鏈嶅姟
systemctl stop tg-search-bot

# 閲嶅惎鏈嶅姟
systemctl restart tg-search-bot

# 鏌ョ湅鐘舵€?systemctl status tg-search-bot

# 鏌ョ湅瀹炴椂鏃ュ織
tail -f /www/wwwroot/tg-search-bot/logs/stderr.log
tail -f /www/wwwroot/tg-search-bot/logs/stdout.log
```

---

## 鍏€佸垵濮嬪寲閰嶇疆

### 8.1 棣栨璁块棶

1. 娴忚鍣ㄨ闂細`http://浣犵殑鍩熷悕/admin`
2. 榛樿璐﹀彿锛歚admin`
3. 榛樿瀵嗙爜锛歚demo123456`

### 8.2 淇敼瀵嗙爜锛堥噸瑕侊紒锛?
1. 鐧诲綍鍚庣偣鍑婚《鏍忋€愷煍?淇敼瀵嗙爜銆?2. 濉啓鏃у瘑鐮佸拰鏂板瘑鐮?3. 鐐瑰嚮銆愮‘璁や慨鏀广€?4. 绯荤粺鑷姩閫€鍑猴紝浣跨敤鏂板瘑鐮侀噸鏂扮櫥褰?
### 8.3 绯荤粺閰嶇疆

1. 杩涘叆銆愨殭锔?绯荤粺閰嶇疆銆戣彍鍗?2. 渚濇閰嶇疆浠ヤ笅椤圭洰锛?
**蹇呭～椤癸細**
- 鏈哄櫒浜?Token锛堜粠 @BotFather 鑾峰彇锛?- API ID / API Hash锛堜粠 my.telegram.org 鑾峰彇锛?- HD 閽卞寘鍔╄璇嶏紙12涓崟璇嶏級
- 绠＄悊鍛樿仈绯绘柟寮?
**鍙€夐」锛?*
- 系统端口（默认 8001）- 日志级别（默认 INFO）- 自动备份间隔

3. 鐐瑰嚮銆愪繚瀛橀厤缃€?
### 8.4 娣诲姞閲囬泦灏忓彿

1. 杩涘叆銆愷煇?灏忓彿 / 浠ｇ悊绠＄悊銆戣彍鍗?2. 鐐瑰嚮銆愭坊鍔犲皬鍙枫€?3. 濉啓 Telegram 灏忓彿淇℃伅
4. 閰嶇疆浠ｇ悊 IP锛堟帹鑽愪娇鐢級
5. 瀹屾垚鎵嬫満鍙烽獙璇?
### 8.5 娣诲姞棰戦亾

1. 杩涘叆銆愷煋?棰戦亾绠＄悊 / 鎺ㄥ箍銆戣彍鍗?2. 鐐瑰嚮銆愭坊鍔犻閬撱€?3. 濉啓棰戦亾淇℃伅
4. 璁剧疆鎺ㄨ崘缃《锛堝彲閫夛級

---

## 涔濄€佸畨鍏ㄩ厤缃?
### 9.1 闃茬伀澧欒缃?
```bash
# CentOS
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload

# Ubuntu/Debian (ufw)
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 9.2 瀹濆瀹夊叏璁剧疆

1. 瀹濆闈㈡澘 鈫?闈㈡澘璁剧疆
2. 淇敼瀹夊叏鍏ュ彛璺緞锛堜笉瑕佺敤榛樿锛?3. 缁戝畾鍩熷悕鎴?IP锛堝鏋滃浐瀹氾級
4. 璁剧疆闈㈡澘 SSL 璇佷功

### 9.3 淇敼 SSH 绔彛锛堝彲閫夛級

```bash
# 缂栬緫 SSH 閰嶇疆
vi /etc/ssh/sshd_config

# 淇敼绔彛
Port 2222

# 閲嶅惎 SSH
systemctl restart sshd
```

### 9.4 瀹氭湡澶囦唤

```bash
# 鎵嬪姩澶囦唤
cd /www/wwwroot/tg-search-bot
tar -czf backup_$(date +%Y%m%d).tar.gz data/ .env

# 璁剧疆瀹氭椂澶囦唤锛堝湪瀹濆璁″垝浠诲姟涓坊鍔狅級
# 姣忓ぉ鍑屾櫒 3 鐐瑰浠?0 3 * * * cd /www/wwwroot/tg-search-bot && tar -czf backup_$(date +\%Y\%m\%d).tar.gz data/ .env
```

---

## 鍗併€佸父瑙侀棶棰樻帓鏌?
### 10.1 绔彛琚崰鐢?
```bash
# 鏌ョ湅绔彛鍗犵敤
netstat -tlnp | grep 8001

# 鎴栦娇鐢?lsof
lsof -i:8001

# 瑙ｅ喅锛氭潃姝诲崰鐢ㄨ繘绋?kill -9 杩涚▼PID
```

### 10.2 Python 渚濊禆鍐茬獊

```bash
# 娓呴櫎鏃т緷璧?rm -rf venv

# 閲嶆柊鍒涘缓铏氭嫙鐜
python3.11 -m venv venv
source venv/bin/activate

# 閲嶆柊瀹夎渚濊禆
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 10.3 Nginx 502 Bad Gateway

```bash
# 妫€鏌ユ湇鍔℃槸鍚﹁繍琛?systemctl status tg-search-bot

# 妫€鏌ョ鍙ｆ槸鍚︾洃鍚?curl http://127.0.0.1:8001

# 鏌ョ湅閿欒鏃ュ織
tail -100 /www/wwwroot/tg-search-bot/logs/stderr.log

# 閲嶅惎鏈嶅姟
systemctl restart tg-search-bot
```

### 10.4 鏁版嵁搴撻攣瀹?
```bash
# 妫€鏌ユ暟鎹簱鏂囦欢鏉冮檺
ls -la /www/wwwroot/tg-search-bot/data/

# 淇鏉冮檺
chmod 664 /www/wwwroot/tg-search-bot/data/*.db
```

### 10.5 Telegram 杩炴帴闂

```bash
# 妫€鏌ョ綉缁滆繛閫氭€?ping my.telegram.org

# 妫€鏌?API 鍑瘉
# 璁块棶 https://my.telegram.org/apps
# 纭 API ID 鍜?API Hash 姝ｇ‘
```

### 10.6 鏂囦欢鏉冮檺闂

```bash
# 淇鏁翠釜椤圭洰鏉冮檺
cd /www/wwwroot/tg-search-bot
chmod -R 755 .
chmod 600 .env
chmod -R 664 data/
chmod -R 775 logs/
```

---

## 鍗佷竴銆佹€ц兘浼樺寲

### 11.1 璋冩暣 Nginx 鍙傛暟

1. 瀹濆闈㈡澘 鈫?杞欢鍟嗗簵 鈫?Nginx 鈫?璁剧疆 鈫?閰嶇疆淇敼
2. 鍦?`http` 鍧椾腑娣诲姞锛?
```nginx
# Gzip 鍘嬬缉
gzip on;
gzip_min_length 1024;
gzip_comp_level 5;
gzip_types text/plain application/json application/javascript text/css;

# 缂撳啿鍖轰紭鍖?client_body_buffer_size 128k;
large_client_header_buffers 4 128k;

# 瓒呮椂璁剧疆
client_body_timeout 30s;
client_header_timeout 30s;
keepalive_timeout 65s;
send_timeout 30s;
```

### 11.2 璋冩暣 Uvicorn 鍙傛暟

缂栬緫 `start.sh` 娣诲姞 worker 鏁帮細

```bash
#!/bin/bash
cd /www/wwwroot/tg-search-bot
source venv/bin/activate
export PYTHONUNBUFFERED=1
export PATH="/www/wwwroot/tg-search-bot/venv/bin:$PATH"
exec gunicorn demo_server:app \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8001
```

> 馃挕 **鎻愮ず**锛氫娇鐢?Gunicorn + Uvicorn 娣峰悎閮ㄧ讲鍙樉钁楁彁鍗囨€ц兘

### 11.3 绯荤粺鍙傛暟浼樺寲

```bash
# 缂栬緫绯荤粺閰嶇疆
vi /etc/sysctl.conf

# 娣诲姞浠ヤ笅鍙傛暟
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
vm.swappiness = 10

# 搴旂敤閰嶇疆
sysctl -p
```

---

## 鍗佷簩銆佺増鏈洿鏂?
### 12.1 澶囦唤褰撳墠鐗堟湰

```bash
cd /www/wwwroot/
cp -r tg-search-bot tg-search-bot-backup-$(date +%Y%m%d)
```

### 12.2 涓嬭浇鏂扮増鏈?
```bash
cd /www/wwwroot/
# 涓嬭浇鏂扮増鏈寘
wget https://your-download-url/tg-search-bot-v1.0.x-install.zip
unzip tg-search-bot-v1.0.x-install.zip
```

### 12.3 鍚堝苟閰嶇疆

```bash
# 淇濈暀鏃х増鏈殑 data 鐩綍鍜?.env
cp -r tg-search-bot/data tg-search-bot-new/
cp tg-search-bot/.env tg-search-bot-new/

# 鍋滄鏈嶅姟
systemctl stop tg-search-bot

# 鏇挎崲鏃х増鏈?mv tg-search-bot tg-search-bot-old
mv tg-search-bot-new tg-search-bot

# 閲嶆柊瀹夎渚濊禆锛堝鏈夋洿鏂帮級
cd /www/wwwroot/tg-search-bot
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
deactivate

# 鍚姩鏂扮増鏈?systemctl start tg-search-bot
```

### 12.4 鍥炴粴锛堝鏂扮増鏈湁闂锛?
```bash
systemctl stop tg-search-bot
mv tg-search-bot tg-search-bot-bad
mv tg-search-bot-backup-鏃ユ湡 tg-search-bot
systemctl start tg-search-bot
```

---

## 鍗佷笁銆佺洃鎺т笌鏃ュ織

### 13.1 鏌ョ湅瀹炴椂鏃ュ織

```bash
# 搴旂敤绋嬪簭鏃ュ織
tail -f /www/wwwroot/tg-search-bot/logs/stderr.log

# Nginx 鏃ュ織
tail -f /www/wwwlogs/浣犵殑绔欑偣鍚?log
tail -f /www/wwwlogs/浣犵殑绔欑偣鍚?error.log
```

### 13.2 瀹濆鐩戞帶

1. 瀹濆闈㈡澘 鈫?鐩戞帶
2. 鏌ョ湅 CPU銆佸唴瀛樸€佺鐩樹娇鐢ㄦ儏鍐?3. 璁剧疆鍛婅闃堝€?
### 13.3 鍋ュ悍妫€鏌?
```bash
# 妫€鏌?API 鍝嶅簲
curl -s http://127.0.0.1:8001/api/admin/settings/describe | head -c 100

# 妫€鏌ユ暟鎹簱澶у皬
du -sh /www/wwwroot/tg-search-bot/data/

# 妫€鏌ョ鐩樼┖闂?df -h
```

---

## 闄勫綍锛氫竴閿儴缃插懡浠?
濡傛灉涓婅堪閰嶇疆鐪嬭捣鏉ュ鏉傦紝鍙互浣跨敤椤圭洰鑷甫鐨勪竴閿儴缃茶剼鏈細

```bash
cd /www/wwwroot/tg-search-bot
bash install.sh
```

鑴氭湰浼氳嚜鍔ㄥ畬鎴愶細
- 鉁?鐜妫€娴?- 鉁?渚濊禆瀹夎
- 鉁?铏氭嫙鐜鍒涘缓
- 鉁?Python 渚濊禆瀹夎
- 鉁?Systemd 鏈嶅姟娉ㄥ唽
- 鉁?Nginx 鍙嶄唬閰嶇疆
- 鉁?鍚姩鏈嶅姟
- 鉁?楠岃瘉 API

> 鈿狅笍 娉ㄦ剰锛氬鏋滀娇鐢ㄤ竴閿剼鏈紝璇峰厛瀹屾垚銆愬疂濉旈潰鏉垮畨瑁呫€戝拰銆怤ginx 瀹夎銆戞楠?
---

## 鎶€鏈敮鎸?
濡傞亣鍒伴棶棰橈紝璇锋鏌ワ細
1. 鏈枃妗ｇ殑銆愬父瑙侀棶棰樻帓鏌ャ€戠珷鑺?2. 椤圭洰鐨?`logs/` 鐩綍涓嬬殑閿欒鏃ュ織
3. 瀹濆闈㈡澘鐨勩€愮綉绔欒瘖鏂€戝姛鑳?
---

**鏂囨。鐗堟湰**锛歷1.0.3
**閫傜敤鐗堟湰**锛歍G鎼滅储鏈哄櫒浜?v1.0.3
**鏈€鍚庢洿鏂?*锛?026-08-27

path = r'C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot\server.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The try block starts at line 4031 (index 4030)
# We need to indent lines 4039-4530 (indices 4038-4529) by 4 more spaces
for i in range(4038, 4530):
    line = lines[i]
    stripped = line.lstrip()
    if stripped:  # non-empty line
        original_indent = len(line) - len(stripped)
        lines[i] = ' ' * (original_indent + 4) + stripped

# Insert except block before line 4532 (after the return statement)
except_block = [
    '    except Exception as e:\n',
    '        import traceback\n',
    '        logger = __import__("loguru").logger\n',
    '        logger.error(f"api_bot_command error: {e}")\n',
    '        return JSONResponse({"reply_html": "⚠️ 服务暂时不可用，请稍后重试。"}, status_code=500)\n',
]

# Insert at position 4530 (before the empty line that's before @app.post)
for j, new_line in enumerate(except_block):
    lines.insert(4530 + j, new_line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done. New line count:', len(lines))

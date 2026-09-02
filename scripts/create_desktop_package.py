"""创建桌面安装包 - 排除敏感文件和大数据文件"""
import zipfile
import os
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\ai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8713b5d7ac5d58514066c4\tg-search-bot")
DESKTOP = Path.home() / "Desktop"
OUTPUT_ZIP = DESKTOP / "tg-search-bot-v1.0.25.zip"

# 排除模式
EXCLUDE_PATTERNS = {
    # 敏感文件
    '.env', '.env.local', '.env.save', '.env.bak',
    # Python缓存
    '__pycache__', '*.pyc', '*.pyo', '*.pyd',
    # Git
    '.git', '.gitignore',
    # Node
    'node_modules', '.next',
    # 数据文件
    'data/**/*.db', 'data/**/*.sqlite', 'data/**/*.sqlite3',
    'data/backups/**', 'data/sessions/**', 'data/uploads/**',
    'data/demo_sessions/**',
    # 日志
    'logs/**', '*.log',
    # 临时文件
    'scripts/ssh_*.py',  # SSH调试脚本不需要
    '*.md',  # 文档文件
    # 虚拟环境
    'venv', '.venv',
    # 其他
    '.trae', '.idea', '.vscode',
    '**/__pycache__/**',
}

def should_exclude(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    rel_str = str(rel).replace('\\', '/')
    for pattern in EXCLUDE_PATTERNS:
        # Simple pattern matching
        if pattern.startswith('*'):
            if rel_str.endswith(pattern[1:]):
                return True
        elif pattern.endswith('/**'):
            prefix = pattern[:-3]
            if rel_str.startswith(prefix + '/') or rel_str == prefix:
                return True
        elif pattern.endswith('**'):
            prefix = pattern[:-2]
            if rel_str.startswith(prefix + '/'):
                return True
        elif '/' in pattern:
            # Directory pattern
            if rel_str.startswith(pattern + '/') or rel_str == pattern:
                return True
        else:
            # File pattern
            if rel.name == pattern or rel_str.endswith('/' + pattern):
                return True
    return False

def create_zip():
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Output: {OUTPUT_ZIP}")
    print(f"Desktop: {DESKTOP}")

    # Create desktop dir if needed
    DESKTOP.mkdir(exist_ok=True)

    # Count files
    all_files = list(PROJECT_ROOT.rglob('*'))
    all_files = [f for f in all_files if f.is_file()]
    print(f"Total files: {len(all_files)}")

    excluded_count = 0
    included_count = 0
    included_files = []

    for f in all_files:
        if should_exclude(f, PROJECT_ROOT):
            excluded_count += 1
        else:
            included_count += 1
            included_files.append(f)

    print(f"Included: {included_count}, Excluded: {excluded_count}")

    # Create zip
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in included_files:
            arcname = str(f.relative_to(PROJECT_ROOT))
            zf.write(f, arcname)

    print(f"\nZip created: {OUTPUT_ZIP}")
    print(f"Zip size: {OUTPUT_ZIP.stat().st_size / 1024:.1f} KB")

    # List top-level files in zip
    with zipfile.ZipFile(OUTPUT_ZIP, 'r') as zf:
        names = zf.namelist()
        print(f"\nTop-level entries ({len(names)} total):")
        top_level = sorted(set(n.split('/')[0] for n in names if '/' in n) | {n for n in names if '/' not in n})
        for t in top_level[:30]:
            count = sum(1 for n in names if n.startswith(t + '/') or n == t)
            print(f"  {t}/ ({count} files)")
        if len(top_level) > 30:
            print(f"  ... and {len(top_level) - 30} more directories")

if __name__ == "__main__":
    create_zip()

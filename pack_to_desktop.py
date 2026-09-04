"""
TG Search Bot - 打包脚本
将项目打包为 ZIP 并保存到桌面，自动生成版本号
"""
import os
import sys
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime

# 项目根目录（本脚本所在目录）
PROJECT_ROOT = Path(__file__).parent.absolute()

# 桌面路径
DESKTOP = Path.home() / "Desktop"

# 版本号（从交接文档读取）
VERSION = "1.0.27"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# 输出文件名
ZIP_NAME = f"tg-search-bot-v{VERSION}-{TIMESTAMP}.zip"
ZIP_PATH = DESKTOP / ZIP_NAME


def should_include(path: Path) -> bool:
    """判断文件是否应该包含在压缩包中"""
    # 排除隐藏文件和目录
    parts = path.parts
    for part in parts:
        if part.startswith("."):
            return False
    # 排除 __pycache__
    if "__pycache__" in parts:
        return False
    # 排除 .db 数据库文件（体积大且含敏感数据）
    if path.suffix == ".db":
        return False
    # 排除临时文件
    if path.name.startswith("~") or path.name.endswith(".tmp"):
        return False
    # 排除 Python 缓存
    if path.suffix == ".pyc":
        return False
    return True


def create_zip():
    """创建 ZIP 压缩包"""
    print(f"📦 开始打包项目...")
    print(f"   源目录: {PROJECT_ROOT}")
    print(f"   目标:   {ZIP_PATH}")

    file_count = 0
    total_size = 0

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(PROJECT_ROOT)

                if not should_include(file_path):
                    continue

                # 添加到 ZIP
                zf.write(file_path, rel_path)
                file_count += 1
                total_size += file_path.stat().st_size

    print(f"✅ 打包完成！")
    print(f"   文件数: {file_count}")
    print(f"   大小:   {total_size / 1024:.1f} KB")
    print(f"   路径:   {ZIP_PATH}")

    # 同时在项目根目录也生成一个不带时间戳的版本（方便更新）
    SIMPLE_ZIP = PROJECT_ROOT / f"tg-search-bot-v{VERSION}.zip"
    with zipfile.ZipFile(SIMPLE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(PROJECT_ROOT)
                if not should_include(file_path):
                    continue
                zf.write(file_path, rel_path)

    print(f"📁 同时生成: {SIMPLE_ZIP}")
    return ZIP_PATH, SIMPLE_ZIP


def main():
    try:
        zip_path, simple_zip_path = create_zip()
        print(f"\n🎉 桌面压缩包: {zip_path}")
        print(f"📂 项目压缩包: {simple_zip_path}")
        return 0
    except Exception as e:
        print(f"❌ 打包失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

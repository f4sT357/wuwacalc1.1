import re
import argparse
from logger import logger


def detect_metadata_lines(filepath, fix_file=False):
    """
    指定されたファイル内で、行頭に '数字|' のパターンを持つ行を検出します。
    fix_fileがTrueの場合、これらの行を削除してファイルを上書き保存します。
    """
    pattern = re.compile(r"^\s*\d+\|\s*.*")

    original_lines = []
    cleaned_lines = []
    found_errors = False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            original_lines = f.readlines()

        for line_num, line in enumerate(original_lines, 1):
            if pattern.match(line):
                logger.info(f"Metadata pattern found at line {line_num}: {line.strip()}")
                found_errors = True
            else:
                cleaned_lines.append(line)  # メタデータがない行は保持

        if fix_file and found_errors:
            logger.info(f"Fixing {filepath} by removing metadata lines...")
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(cleaned_lines)
            logger.info(f"Successfully cleaned {filepath}.")
        elif not found_errors:
            logger.info(f"No metadata patterns found in {filepath}.")

    except FileNotFoundError:
        logger.error(f"Error: File not found at {filepath}")
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return False

    return found_errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detects and optionally fixes lines with 'number|' pattern at the beginning."
    )
    parser.add_argument("filepath", help="Path to the file to check.")
    parser.add_argument("--fix", action="store_true", help="Automatically remove metadata lines from the file.")

    args = parser.parse_args()

    detect_metadata_lines(args.filepath, args.fix)

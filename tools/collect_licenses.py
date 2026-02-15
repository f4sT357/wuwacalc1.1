import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESS_DIR = ROOT / "tesseract"
OUT_DIR = ROOT / "licenses"
THIRD = ROOT / "THIRD_PARTY_LICENSES.md"

KEYWORDS = re.compile(r"license|copyright|notice|copying|readme", re.I)


def ensure_out():
    OUT_DIR.mkdir(exist_ok=True)


def candidate_files():
    if not TESS_DIR.exists():
        return []
    files = []
    for p in TESS_DIR.rglob("*"):
        if p.is_file():
            name = p.name
            # match filenames
            if KEYWORDS.search(name):
                files.append(p)
                continue
            # match small text files by extension
            if p.suffix.lower() in [".txt", ".md", ".rst"] and p.stat().st_size < 200 * 1024:
                # scan for license keyword
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                    if KEYWORDS.search(txt):
                        files.append(p)
                except Exception:
                    pass
    return sorted(set(files))


def copy_and_aggregate(files):
    appended = []
    for f in files:
        dest = OUT_DIR / f.name
        # if name collision, prefix with parent folder
        if dest.exists():
            dest = OUT_DIR / (f.parent.name + "_" + f.name)
        try:
            shutil.copy2(f, dest)
            appended.append(dest)
        except Exception as e:
            print(f"Failed to copy {f}: {e}")

    # Append into THIRD_PARTY_LICENSES.md
    if appended:
        with THIRD.open("a", encoding="utf-8") as md:
            md.write("\n\n---\n\n")
            md.write("# Collected license files from tesseract/\n")
            for a in appended:
                md.write(f"\n## {a.name}\n\n")
                try:
                    md.write(a.read_text(encoding="utf-8", errors="ignore"))
                    md.write("\n")
                except Exception as e:
                    md.write(f"Could not read {a}: {e}\n")
    return appended


def main():
    ensure_out()
    files = candidate_files()
    print(f"Found {len(files)} candidate license files.")
    appended = copy_and_aggregate(files)
    print(f"Copied {len(appended)} files to {OUT_DIR}. Appended to {THIRD}.")


if __name__ == "__main__":
    main()

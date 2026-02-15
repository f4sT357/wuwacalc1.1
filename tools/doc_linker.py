import os
import re

ROOT_DIR = os.getcwd()
DOC_FILE = "PROCESS_FLOW.md"


def linkify_process_flow():
    # 1. Get list of files
    files_map = {}  # filename -> relative_path
    for root, dirs, files in os.walk(ROOT_DIR):
        # Exclude common ignore dirs
        if ".git" in dirs:
            dirs.remove(".git")
        if ".venv" in dirs:
            dirs.remove(".venv")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        if ".cursor" in dirs:
            dirs.remove(".cursor")
        if "build" in dirs:
            dirs.remove("build")
        if "dist" in dirs:
            dirs.remove("dist")
        if "site-packages" in root:
            continue  # Just in case

        for f in files:
            # Filter for relevant source files
            if f.endswith((".py", ".json", ".md", ".html", ".txt")) and f != DOC_FILE:
                rel_path = os.path.relpath(os.path.join(root, f), ROOT_DIR)
                # Normalize path separators
                rel_path = rel_path.replace("\\", "/")
                files_map[f] = rel_path

    # 2. Read Doc
    if not os.path.exists(DOC_FILE):
        print(f"{DOC_FILE} not found.")
        return

    with open(DOC_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. Replace
    # Sort files by length desc to avoid partial matches
    sorted_files = sorted(files_map.keys(), key=len, reverse=True)

    for fname in sorted_files:
        fpath = files_map[fname]

        # Regex to match existing links OR the filename (with optional backticks)
        # Group 1: Existing Markdown link [text](url)
        # Group 2: The filename, optionally surrounded by backticks, allowing for surrounding whitespace/punctuation check if needed
        # We use \b for boundary check if no backticks, but filenames have dots, so \b is tricky.
        # Instead, we rely on the specific `?fname`? structure.

        # Pattern explanation:
        # (\[[^\]]*?\]\([^)]*?\))  -> Match existing links: [...](\...)
        # |                        -> OR
        # (`?                      -> Optional opening backtick
        # \b                       -> Word boundary (start) - heuristic, might fail on some special chars but good for code
        # {re.escape(fname)}       -> The filename
        # \b                       -> Word boundary (end)
        # `?)                      -> Optional closing backtick

        # Actually \b is not good for filenames starting/ending with non-word chars or dots.
        # e.g. "ui_components.py" starts with word char, ends with word char (y). \b works.
        # ".gitignore" starts with dot (non-word). \b won't match start.

        # Improved Pattern:
        # We want to match `fname` or `fname`.
        # We want to avoid matching `fname` if it is part of `my_fname_is_cool.py`.
        # So we want boundaries.

        escaped_fname = re.escape(fname)

        # Construct a boundary check that accepts whitespace, punctuation, or start/end of line
        # but NOT other alphanumeric chars or underscores.
        # (?<![a-zA-Z0-9_]) and (?![a-zA-Z0-9_])

        boundary_lookbehind = r"(?<![a-zA-Z0-9_\.\-])"  # Add . and - to avoid partial match in something-else
        boundary_lookahead = r"(?![a-zA-Z0-9_\.\-])"

        # Special handling: if fname starts with ., lookbehind might need adjustment?
        # If fname=".gitignore", lookbehind char before it shouldn't be a word char?
        # Actually, simpler:

        pattern_str = (
            r"(\[[^\]]*?\]\([^)]*?\))|("
            + boundary_lookbehind
            + r"`?"
            + escaped_fname
            + r"`?"
            + boundary_lookahead
            + r")"
        )
        pattern = re.compile(pattern_str)

        def replacer(m):
            if m.group(1):  # It's an existing link
                return m.group(1)

            match_text = m.group(2)
            # If we found it, linkify it.
            # Ensure we wrap in backticks for style, and link.
            # If it already had backticks, strip them first to avoid double backticks if we construct manually,
            # but markdown link syntax is [`text`](url).

            clean_text = match_text.replace("`", "")
            return f"[`{clean_text}`](./{fpath})"

        content = pattern.sub(replacer, content)

    # 4. Write
    with open(DOC_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated {DOC_FILE} with code reference links.")


if __name__ == "__main__":
    linkify_process_flow()

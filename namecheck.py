"""Checks file names against Windows naming rules without touching any file.

Run: python namecheck.py names LIST.txt     (one file name per line)
     python namecheck.py folder FOLDER      (looks at the names inside it)
Exit code: 0 = no problem found, 1 = problem found, 2 = could not read.
"""
import os
import sys
import stat
from pathlib import Path

BAD_CHARS = '<>:"/\\|?*'
RESERVED = {"CON", "PRN", "AUX", "NUL"}
RESERVED |= {"COM" + d for d in "123456789\u00b9\u00b2\u00b3"}
RESERVED |= {"LPT" + d for d in "123456789\u00b9\u00b2\u00b3"}
PATH_LIMIT = 260  # the older Windows limit on a whole path, in characters
SHOW = 20  # how many problems to print


def check_name(name):
    """Return a list of reasons a name breaks the rules. Empty means none found."""
    reasons = []
    found = [c for c in dict.fromkeys(name) if c in BAD_CHARS]
    if found:
        reasons.append("contains " + " ".join(found))
    if any(ord(c) < 32 for c in name):
        reasons.append("contains a control character")
    if name.split(".")[0].upper() in RESERVED:
        reasons.append("starts with a reserved device name")
    if name not in (".", "..") and name[-1:] in (" ", "."):
        reasons.append("ends with a space or a period")
    return reasons


def safe_input(value, directory=False):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise OSError('Parent-traversal paths are unsupported.')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 0x400:
            raise OSError('Links/reparse points are unsupported.')
    info = path.lstat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise OSError('Expected an ordinary directory.')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise OSError('Expected an ordinary singly linked file.')
    return path


def read_names(path):
    path = safe_input(path)
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    return [line for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line != ""]


def scan_folder(folder):
    folder = safe_input(folder, directory=True)
    problems = []
    count = 0
    stack = [folder]
    while stack:
        current = stack.pop()
        # scandir errors propagate: an unreadable tree is not a clean report.
        with os.scandir(current) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                directory = stat.S_ISDIR(info.st_mode)
                safe_input(entry.path, directory=directory)
                count += 1
                if count > 10000:
                    raise OSError('Tree exceeds 10000 entries.')
                name = entry.name
                reasons = check_name(name)
                full = os.path.abspath(entry.path)
                if len(full) >= PATH_LIMIT:
                    reasons.append(f"whole path is {len(full)} characters")
                if reasons:
                    problems.append((os.path.relpath(entry.path, folder), reasons))
                if directory:
                    stack.append(Path(entry.path))
    return count, problems


def report(count, problems):
    print("Names checked:", count)
    if not problems:
        print("No problems found against the rules this tool knows.")
        print("That does not mean every program or file system will accept them.")
        return 0
    print("Names with a problem:", len(problems))
    for name, reasons in problems[:SHOW]:
        print(f"  {ascii(name)}: " + "; ".join(reasons))
    if len(problems) > SHOW:
        print("  ... and", len(problems) - SHOW, "more. Showing the first", str(SHOW) + ".")
    print("Nothing was renamed or changed.")
    return 1


def main(argv):
    if len(argv) != 3 or argv[1] not in ("names", "folder"):
        print("Usage: python namecheck.py names LIST.txt")
        print("       python namecheck.py folder FOLDER")
        return 2
    try:
        if argv[1] == "names":
            names = read_names(argv[2])
            problems = [(n, check_name(n)) for n in names if check_name(n)]
            return report(len(names), problems)
        if not Path(argv[2]).exists():
            print("Not a folder:", argv[2])
            return 2
        count, problems = scan_folder(argv[2])
        return report(count, problems)
    except UnicodeDecodeError:
        print("The list is not valid UTF-8 text.")
        return 2
    except OSError as e:
        print("Could not read:", e)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

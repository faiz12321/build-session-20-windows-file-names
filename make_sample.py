"""Makes a made-up list of file names and a small folder to practise on.

Run: python make_sample.py
The list holds names that Windows does not allow. They are only text in a
list, so no file with those names is ever created.
"""
from pathlib import Path

NAMES = [
    "holiday photos.jpg",
    "report: final.docx",
    "notes?.txt",
    "NUL.txt",
    "budget 2026.xlsx",
    "draft.",
    "com1",
    "my<file>.txt",
    ".gitignore",
    "lpt\u00b9.log",
]


def make(folder):
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    (folder / "names.txt").write_bytes(("\n".join(NAMES) + "\n").encode("utf-8"))
    tree = folder / "tree"
    (tree / "docs").mkdir(parents=True, exist_ok=True)
    (tree / "readme.txt").write_text("hello\n", encoding="utf-8")
    (tree / "docs" / "plan (v2).txt").write_text("plan\n", encoding="utf-8")
    (tree / "docs" / ".hidden").write_text("x\n", encoding="utf-8")
    return folder


if __name__ == "__main__":
    make("sample")
    print("Made sample/names.txt and sample/tree with three small files")

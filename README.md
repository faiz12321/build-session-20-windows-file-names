# Check file names against Windows naming rules

A small read-only Python tool built step by step. Give it a list of file names (a text file, one name per line) or a folder. It checks each name against the Windows rules from Microsoft's "Naming Files, Paths, and Namespaces" page and prints the names that break them. It never renames, creates or changes any file.

## Run it

    python make_sample.py                          # makes a made-up list and a small folder in sample/
    python namecheck.py names sample/names.txt     # check a list of names
    python namecheck.py folder sample/tree         # check the names inside a folder
    python -m unittest -v                          # 44 small fixture tests

On Windows, if `python` is not found, use `py`.

## Files

- `namecheck.py` - the tool
- `make_sample.py` - makes a made-up list of ten names (some Windows does not allow, listed only as text) and a small folder of ordinary files
- `test_namecheck.py` - tests

## What it checks

- The characters < > : " / \ | ? * and control characters (code 1 to 31)
- The reserved device names CON, PRN, AUX, NUL, COM1 to COM9 and LPT1 to LPT9 (including the superscript digits), with or without an extension
- A name that ends with a space or a period
- In folder mode, a whole path of 260 characters or more, counted on the PC running the tool

## Notes

- These are the rules on one Microsoft page. A file system can have more rules, and a clean report does not mean every program will accept a name.
- Since Windows 10 version 1607 the 260 character path limit can be turned off, so a long path is a warning, not always an error.
- Only the first 20 problems are printed. The count covers all of them.
- Names are printed with accented and special characters written as escapes, so they show on any console.
- The folder scan only reads names. Tests check that nothing is created or changed. Names that Windows does not allow are never created as files, because that would fail on Windows.
- Tested only on small made-up names and folders. Python 3.10 and 3.12 on Linux, and, by GitHub Actions, Python 3.12 on Windows and Ubuntu. Not tested on a Windows 10 or 11 desktop.
- Educational example, no warranty. Use at your own risk.
- Code is MIT licensed (see LICENSE). Python and the Windows rules belong to their owners; this repository includes neither.


## Safe setup and filesystem repair

Use a new empty lesson folder. Setup exclusively creates names.txt and three
fictional files in a NEW sample folder. Existing paths, traversal spellings and
linked/reparse parents are refused. No reset/overwrite. After interrupted setup
use a different new lesson folder; do not delete old data to force retry.

List input, ancestors and tree entries refuse links/reparse points, hardlinks,
special entries and parent traversal. Enumeration errors abort, instead of the
old os.walk suppression that could make a partial tree look clean. Stop editors
and sync; no hostile-race guarantee. Folder entry cap 10000 is not a resource
sandbox; whole-list reads/traversal can still use memory/time. Reports reveal
private names/paths. No upload/network code; other software/sync uncontrolled.

The 260 character rule counts local Python string length, not UTF-16 code units
or a future destination path. Case collisions, alternate streams, all namespaces,
permissions, all filesystem and application rules are not validated.

44 small tests include original 28 rule/list/folder cases, four setup preservation
and 12 filesystem/error/traversal cases. Two traversal tests mock invalid/long names
instead of creating Windows-invalid files. Unix pipe skips on Windows; symlink
tests can skip where unavailable. Two Windows and two Ubuntu full replays pass44tests; per-platform pairs differ
only in unittest time. 16phone stages320/390/1280 and four exact clipboard values
pass with no page overflow/JavaScript errors; actual pixels inspected.

Sources:
- https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
- https://docs.python.org/3/library/os.html

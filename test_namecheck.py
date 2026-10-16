import io
import os
import stat
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import make_sample
import namecheck


def run(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = namecheck.main(["namecheck.py", *map(str, args)])
    return code, buf.getvalue()


class Rules(unittest.TestCase):
    def test_plain_name(self):
        self.assertEqual(namecheck.check_name("holiday photos.jpg"), [])

    def test_each_reserved_character(self):
        for c in '<>:"/\\|?*':
            with self.subTest(c=c):
                self.assertTrue(namecheck.check_name("a" + c + "b"))

    def test_reserved_characters_listed_once(self):
        self.assertEqual(namecheck.check_name("a??b"), ["contains ?"])

    def test_control_character(self):
        self.assertIn("contains a control character", namecheck.check_name("a\x01b"))

    def test_tab_is_a_control_character(self):
        self.assertTrue(namecheck.check_name("a\tb"))

    def test_device_names_any_case(self):
        for n in ("CON", "con", "Prn", "AUX", "nul", "COM1", "com9", "LPT3", "lpt9"):
            with self.subTest(n=n):
                self.assertIn("starts with a reserved device name", namecheck.check_name(n))

    def test_device_name_with_extension(self):
        self.assertTrue(namecheck.check_name("NUL.txt"))
        self.assertTrue(namecheck.check_name("NUL.tar.gz"))

    def test_superscript_digits(self):
        self.assertTrue(namecheck.check_name("COM\u00b9"))
        self.assertTrue(namecheck.check_name("lpt\u00b3.txt"))

    def test_device_name_only_at_the_start(self):
        self.assertEqual(namecheck.check_name("console.txt"), [])
        self.assertEqual(namecheck.check_name("my.con"), [])

    def test_com0_and_com10_not_listed(self):
        self.assertEqual(namecheck.check_name("COM0"), [])
        self.assertEqual(namecheck.check_name("COM10"), [])

    def test_trailing_period_and_space(self):
        self.assertTrue(namecheck.check_name("draft."))
        self.assertTrue(namecheck.check_name("draft "))

    def test_leading_period_is_fine(self):
        self.assertEqual(namecheck.check_name(".gitignore"), [])

    def test_dot_and_dotdot_alone(self):
        self.assertEqual(namecheck.check_name("."), [])
        self.assertEqual(namecheck.check_name(".."), [])

    def test_several_reasons_at_once(self):
        r = namecheck.check_name("NUL.?.")
        self.assertEqual(len(r), 3)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.sample = make_sample.make(self.dir / "sample")


class Names(Base):
    def test_sample_list(self):
        code, out = run("names", self.sample / "names.txt")
        self.assertEqual(code, 1)
        self.assertIn("Names checked: 10", out)
        self.assertIn("Names with a problem: 7", out)
        self.assertIn("'NUL.txt': starts with a reserved device name", out)
        self.assertIn("'lpt\\xb9.log'", out)
        self.assertNotIn("holiday photos.jpg", out)

    def test_clean_list(self):
        p = self.dir / "ok.txt"
        p.write_text("a.txt\nb.txt\n", encoding="utf-8")
        code, out = run("names", p)
        self.assertEqual(code, 0)
        self.assertIn("No problems found", out)

    def test_windows_line_endings_in_list(self):
        p = self.dir / "w.txt"
        p.write_bytes(b"a.txt\r\nNUL\r\n")
        code, out = run("names", p)
        self.assertIn("Names checked: 2", out)
        self.assertIn("Names with a problem: 1", out)

    def test_blank_lines_skipped(self):
        p = self.dir / "b.txt"
        p.write_text("a.txt\n\n\nb.txt\n", encoding="utf-8")
        self.assertIn("Names checked: 2", run("names", p)[1])

    def test_only_first_20_shown(self):
        p = self.dir / "many.txt"
        p.write_text("".join("bad%d?\n" % i for i in range(25)), encoding="utf-8")
        code, out = run("names", p)
        self.assertIn("Names with a problem: 25", out)
        self.assertIn("and 5 more", out)
        self.assertEqual(out.count("contains ?"), 20)

    def test_not_utf8(self):
        p = self.dir / "bad.txt"
        p.write_bytes(b"caf\xe9\n")
        self.assertEqual(run("names", p)[0], 2)

    def test_missing_list(self):
        self.assertEqual(run("names", self.dir / "none.txt")[0], 2)


class Folder(Base):
    def test_sample_folder_is_clean(self):
        code, out = run("folder", self.sample / "tree")
        self.assertEqual(code, 0)
        self.assertIn("Names checked: 4", out)

    def fake_scan(self, names):
        entries=[]
        for name in names:
            entry=mock.Mock()
            entry.name=name
            entry.path=str(self.dir/name)
            entry.stat.return_value=mock.Mock(st_mode=stat.S_IFREG)
            entries.append(entry)
        context=mock.MagicMock()
        context.__enter__.return_value=iter(entries)
        return context

    def test_flags_names_found_in_a_folder(self):
        # Mock only traversal, so reserved names are not created on Windows.
        with mock.patch('os.scandir',return_value=self.fake_scan(['NUL.txt','fine.txt'])), mock.patch.object(namecheck,'safe_input',side_effect=lambda p,**kw:Path(p)):
            count,problems=namecheck.scan_folder(self.dir)
        self.assertEqual(count,2)
        self.assertEqual([p[0] for p in problems],['NUL.txt'])

    def test_long_path_flagged(self):
        with mock.patch('os.scandir',return_value=self.fake_scan(['a'*250])), mock.patch.object(namecheck,'safe_input',side_effect=lambda p,**kw:Path(p)):
            count,problems=namecheck.scan_folder(self.dir)
        self.assertEqual(len(problems),1)
        self.assertIn('whole path is',problems[0][1][0])

    def test_not_a_folder(self):
        code, out = run("folder", self.sample / "names.txt")
        self.assertEqual(code, 2)

    def test_usage(self):
        self.assertEqual(run("names")[0], 2)
        self.assertEqual(run("other", "x")[0], 2)


class ReadOnly(Base):
    def test_nothing_changed_or_created(self):
        before = sorted(str(p.relative_to(self.dir)) for p in self.dir.rglob("*"))
        stamps = {p: os.stat(p).st_mtime_ns for p in self.dir.rglob("*") if p.is_file()}
        run("names", self.sample / "names.txt")
        run("folder", self.sample / "tree")
        self.assertEqual(sorted(str(p.relative_to(self.dir)) for p in self.dir.rglob("*")), before)
        for p, t in stamps.items():
            self.assertEqual(os.stat(p).st_mtime_ns, t)

    def test_no_file_with_a_bad_name_is_created(self):
        run("names", self.sample / "names.txt")
        names = {p.name for p in self.dir.rglob("*")}
        self.assertNotIn("NUL.txt", names)
        self.assertNotIn("draft.", names)


class SafeSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sample = self.root / 'sample'

    def test_existing_folder_preserves_nested_bytes_and_mtime(self):
        (self.sample / 'nested').mkdir(parents=True)
        keep = self.sample / 'nested' / 'keep'
        keep.write_bytes(b'KEEP')
        before = keep.read_bytes(), keep.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (keep.read_bytes(), keep.stat().st_mtime_ns))

    def test_existing_file_preserved(self):
        self.sample.write_bytes(b'KEEP')
        before = self.sample.read_bytes(), self.sample.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (self.sample.read_bytes(), self.sample.stat().st_mtime_ns))

    def test_repeat_preserves_every_output(self):
        make_sample.make(self.sample)
        before = {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()}
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()})

    def test_cli_repeat_preserves_every_output(self):
        import subprocess, sys
        script = self.root / 'make_sample.py'
        shutil.copyfile(Path(make_sample.__file__).resolve(), script)
        make_sample.make(self.sample)
        before = {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('sample already exists', result.stderr)
        self.assertEqual(before, {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()})




class FilesystemSafety(Base):
    def link(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError:self.skipTest('Symlink creation unavailable')

    def test_list_hardlink_refused(self):
        target=self.sample/'names.txt';before=target.read_bytes(),target.stat().st_mtime_ns
        link=self.dir/'hard.txt';os.link(target,link)
        self.assertEqual(run('names',link)[0],2)
        self.assertEqual(before,(target.read_bytes(),target.stat().st_mtime_ns))

    def test_list_symlink_existing_dangling_and_selfloop_refused(self):
        link=self.dir/'link';self.link(link,self.sample/'names.txt')
        self.assertEqual(run('names',link)[0],2);link.unlink()
        self.link(link,self.dir/'absent');self.assertEqual(run('names',link)[0],2);link.unlink()
        self.link(link,link);self.assertEqual(run('names',link)[0],2)

    def test_list_linked_parent_refused(self):
        link=self.dir/'linked';self.link(link,self.sample,True)
        self.assertEqual(run('names',link/'names.txt')[0],2)

    def test_folder_root_link_refused(self):
        link=self.dir/'linked';self.link(link,self.sample/'tree',True)
        self.assertEqual(run('folder',link)[0],2)

    def test_tree_file_link_refused(self):
        link=self.sample/'tree'/'link';self.link(link,self.sample/'names.txt')
        self.assertEqual(run('folder',self.sample/'tree')[0],2)

    def test_tree_recursive_loop_refused(self):
        tree=self.sample/'tree';self.link(tree/'loop',tree,True)
        self.assertEqual(run('folder',tree)[0],2)

    def test_tree_hardlink_refused(self):
        target=self.sample/'names.txt';os.link(target,self.sample/'tree'/'hard')
        self.assertEqual(run('folder',self.sample/'tree')[0],2)

    def test_tree_special_pipe_refused(self):
        if not hasattr(os,'mkfifo'):self.skipTest('Unix pipe unavailable')
        tree=self.sample/'tree';os.mkfifo(tree/'pipe')
        self.assertEqual(run('folder',tree)[0],2)
        self.assertEqual(run('names',tree/'pipe')[0],2)

    def test_traversal_refused(self):
        self.assertEqual(run('names',self.sample/'..'/'sample'/'names.txt')[0],2)
        self.assertEqual(run('folder',self.sample/'..'/'sample'/'tree')[0],2)

    def test_scandir_permission_error_is_not_a_clean_report(self):
        with mock.patch('os.scandir',side_effect=PermissionError('simulated denial')):
            code,out=run('folder',self.sample/'tree')
        self.assertEqual(code,2);self.assertIn('simulated denial',out)

    def test_setup_linked_parent_refused(self):
        link=self.dir/'linked';self.link(link,self.dir,True)
        with self.assertRaises(OSError):make_sample.make(link/'new')
        self.assertFalse((self.dir/'new').exists())

    def test_setup_traversal_refused(self):
        with self.assertRaises(OSError):make_sample.make(self.dir/'..'/self.dir.name/'new')
        self.assertFalse((self.dir/'new').exists())


if __name__ == "__main__":
    unittest.main()

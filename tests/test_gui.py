# My test gui module for this compiler project.
"""Exercise real Tk buttons and backend jobs. Requires a desktop display."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gui"))
from app import CompilerApp
from backend import find_gcc


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt" and not os.environ.get("DISPLAY"):
            raise unittest.SkipTest("GUI tests require a desktop or a virtual display.")
        cls.temporary = tempfile.TemporaryDirectory(prefix="MY GUI compiler test ")
        cls.project = Path(cls.temporary.name)
        shutil.copytree(ROOT / "custom-keywords", cls.project / "custom-keywords")
        (cls.project / "gui").mkdir()
        shutil.copyfile(ROOT / "gui" / "runtime_io.h", cls.project / "gui" / "runtime_io.h")
        cls.window = tk.Tk()
        cls.app = CompilerApp(cls.window, cls.project)
        cls.app.backend.gcc = find_gcc()
        cls.window.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.closing = True
        cls.app.backend.cancel()
        if cls.app.worker:
            cls.app.worker.join(5)
        cls.app.backend.cleanup()
        cls.window.destroy()
        cls.temporary.cleanup()

    def setUp(self):
        self.app.config.set((ROOT / "custom-keywords" / "keywords.cfg").read_text())
        self.app.config_dirty = False
        self.app.dirty = False
        self.app._load_example("Hello world", confirm=False)
        self.window.update()

    def wait_until(self, condition, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.window.update()
            if condition():
                return
            time.sleep(0.01)
        self.fail("GUI condition timed out. Status: " + self.app.status.cget("text"))

    def finished(self):
        self.wait_until(lambda: self.app.run_button.cget("state") == "normal")

    def test_run_button_and_generated_c(self):
        self.app.run_button.invoke()
        self.finished()
        self.assertIn("Hello from my own C-like language!",
                      self.app.console.get("1.0", "end"))
        self.assertIn("printf", self.app.generated.get())
        self.assertEqual(self.app.export_button.cget("state"), "normal")

    def test_send_button_supplies_live_input(self):
        self.app.source.set(
            '#include <stdio.h>\nint main(void){int n;output("Number: ");'
            'when(input("%d",&n)!=1)provide 1;output("answer:%d",n*2);provide 0;}')
        self.app.input_text.delete("1.0", "end")
        self.app.run_button.invoke()
        self.wait_until(lambda: self.app.running and
                        "Number:" in self.app.console.get("1.0", "end"))
        self.app.live_input.insert(0, "21")
        self.app.send_button.invoke()
        self.finished()
        self.assertIn("answer:42", self.app.console.get("1.0", "end"))

    def test_compile_errors_appear_in_build_log(self):
        self.app.source.set('int main(void){provide ; invalid syntax}')
        self.app.compile_button.invoke()
        self.finished()
        self.assertIn("error:", self.app.log.get("1.0", "end"))
        self.assertIsNone(self.app.last_build)
        self.assertIn("Build failed", self.app.status.cget("text"))

    def test_translate_and_run_with_edited_keywords(self):
        config = self.app.config.get().replace("printf = output", "printf = display")
        self.app.config.set(config)
        self.app.source.set('#include <stdio.h>\nint main(void){display("new alias");provide 0;}')
        self.app.translate_button.invoke()
        self.finished()
        self.assertIn('printf("new alias")', self.app.generated.get())
        self.assertIsNone(self.app.last_build.executable)
        self.app.run_button.invoke()
        self.finished()
        self.assertIn("new alias", self.app.console.get("1.0", "end"))

    def test_stop_button(self):
        self.app.source.set('int main(void){until(1){}provide 0;}')
        self.app.run_button.invoke()
        self.wait_until(lambda: self.app.running)
        self.app.stop_button.invoke()
        self.finished()
        self.assertIn("stopped", self.app.console.get("1.0", "end"))
        self.assertFalse(self.app.running)

    def test_strict_error_navigation_and_highlight(self):
        self.app.source.set('int main(void){\n    printf("bad");\n    provide 0;\n}\n')
        self.app.compile_button.invoke()
        self.finished()
        items = self.app.problems.get_children()
        self.assertTrue(items)
        self.assertIn("use 'output'", self.app.problems.item(items[0], "values")[-1])
        self.assertTrue(self.app.source.text.tag_ranges("error_line"))
        self.app.problems.selection_set(items[0])
        self.app.go_to_problem()
        self.assertEqual(self.app.source.text.index("insert"), "2.4")

    def test_keyword_config_error_jumps_to_keywords(self):
        self.app.config.set(self.app.config.get().replace("printf = output", "printf = printf"))
        self.app.compile_button.invoke()
        self.finished()
        item = self.app.problems.get_children()[0]
        self.assertEqual(self.app.problem_records[item]["target"], "config")
        self.app.problems.selection_set(item)
        self.app.go_to_problem()
        self.assertEqual(self.app.config.text.index("insert"), "3.0")
        self.assertEqual(self.app.editor_tabs.index(self.app.editor_tabs.select()), 2)

    def test_go_to_line_and_language_help(self):
        self.app.source.set("one\ntwo\nthree")
        with patch("app.simpledialog.askinteger", return_value=2):
            self.app.go_to_line()
        self.assertEqual(self.app.source.text.index("insert"), "2.0")
        with patch("app.messagebox.showinfo") as dialog:
            self.app.language_help()
        self.assertIn("Standard spellings are rejected", dialog.call_args.args[1])

    def test_save_and_open_roundtrip(self):
        source = '#include <stdio.h>\nint main(void){output("saved");provide 0;}'
        self.app.source.set(source)
        path = self.project / "my saved code.myc"
        with patch("app.filedialog.asksaveasfilename", return_value=str(path)):
            self.assertTrue(self.app.save_source())
        self.assertEqual(path.read_text(), source)
        self.app.source.set("temporary")
        self.app.dirty = False
        with patch("app.filedialog.askopenfilename", return_value=str(path)):
            self.app.open_source()
        self.assertEqual(self.app.source.get(), source)


if __name__ == "__main__":
    unittest.main(verbosity=2)

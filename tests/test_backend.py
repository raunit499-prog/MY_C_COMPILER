# My test backend module for this compiler project.
"""Real translate/build/run integration tests; no GUI display is required."""
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gui"))
from backend import BuildError, CompilerBackend


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="MY compiler test & spaces ")
        cls.project = Path(cls.temporary.name)
        shutil.copytree(ROOT / "custom-keywords" / "src", cls.project / "custom-keywords" / "src")
        (cls.project / "gui").mkdir()
        shutil.copyfile(ROOT / "gui" / "runtime_io.h", cls.project / "gui" / "runtime_io.h")
        cls.config = (ROOT / "custom-keywords" / "keywords.cfg").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.events = []
        self.running = threading.Event()
        self.prompt = threading.Event()
        self.backend = CompilerBackend(self.project, self.emit)
        self.assertTrue(self.backend.gcc, "GCC must be installed for integration tests.")
        self.backend.reset()

    def emit(self, kind, value):
        self.events.append((kind, value))
        if kind == "running":
            self.running.set()
        if kind == "output" and "Number:" in self.output():
            self.prompt.set()

    def output(self):
        return "".join(value for kind, value in self.events if kind == "output")

    def compile(self, source, **kwargs):
        return self.backend.build(source, self.config, **kwargs)

    def launch(self, result, **kwargs):
        outcomes = []
        def run():
            try:
                outcomes.append(self.backend.run(result, **kwargs))
            except Exception as error:
                outcomes.append(error)
        thread = threading.Thread(target=run)
        thread.start()
        self.assertTrue(self.running.wait(5), "Program never started.")
        return thread, outcomes

    def finish(self, thread, outcomes):
        thread.join(8)
        if thread.is_alive():
            self.backend.cancel()
            thread.join(5)
        self.assertFalse(thread.is_alive(), "Program did not stop.")
        self.assertTrue(outcomes)
        if isinstance(outcomes[0], Exception):
            raise outcomes[0]
        return outcomes[0]

    def test_hello_compiles_and_runs(self):
        source = (ROOT / "custom-keywords" / "examples" / "hello.myc").read_text()
        result = self.compile(source)
        outcome = self.backend.run(result)
        self.assertEqual(outcome.returncode, 0)
        self.assertIn("Hello from my own C-like language!", self.output())
        self.assertIn("printf", result.generated.read_text())

    def test_all_custom_features(self):
        source = (ROOT / "custom-keywords" / "examples" / "all_features.myc").read_text()
        outcome = self.backend.run(self.compile(source), initial_input="2")
        self.assertEqual(outcome.returncode, 0)
        for expected in ("switch: case 2", "for: 1", "for: 3",
                         "while: 0", "while: 1", "do while: 0", "if: positive"):
            self.assertIn(expected, self.output())

    def test_interactive_input_and_unterminated_prompt(self):
        source = ('#include <stdio.h>\nint main(void){int n; output("Number: ");'
                  'when(input("%d",&n)!=1)provide 1; output("Twice=%d\\n",2*n);provide 0;}')
        thread, outcomes = self.launch(self.compile(source))
        self.assertTrue(self.prompt.wait(3), "Prompt was buffered instead of being displayed.")
        self.assertTrue(self.backend.send_input("21\n"))
        outcome = self.finish(thread, outcomes)
        self.assertEqual(outcome.returncode, 0)
        self.assertIn("Twice=42", self.output())

    def test_eof_for_input_loop(self):
        source = ('#include <stdio.h>\nint main(void){int n,sum=0;'
                  'until(input("%d",&n)==1)sum+=n;output("sum:%d",sum);provide 0;}')
        thread, outcomes = self.launch(self.compile(source), initial_input="1\n2\n")
        self.backend.close_input()
        self.assertEqual(self.finish(thread, outcomes).returncode, 0)
        self.assertIn("sum:3", self.output())

    def test_c_syntax_error_is_reported(self):
        with self.assertRaises(BuildError):
            self.compile('#include <stdio.h>\nint main(void){output("x") provide 0;}')
        self.assertTrue(any(kind == "log" and "error:" in value
                            for kind, value in self.events))
        self.assertTrue(any(kind == "generated" for kind, _ in self.events))

    def test_invalid_keyword_config_is_reported(self):
        with self.assertRaises(BuildError):
            self.backend.build('int main(void){provide 0;}', "printf=x\nscanf=x\n")
        self.assertTrue(any(kind == "log" and "same custom name" in value
                            for kind, value in self.events))

    def test_stop_infinite_loop(self):
        result = self.compile('int main(void){until(1){}provide 0;}')
        thread, outcomes = self.launch(result)
        self.backend.cancel()
        self.assertEqual(self.finish(thread, outcomes).reason, "stopped")

    def test_runtime_limit(self):
        outcome = self.backend.run(self.compile('int main(void){until(1){}provide 0;}'),
                                   timeout=0.2)
        self.assertEqual(outcome.reason, "time limit")
        self.assertLess(outcome.elapsed, 4)

    def test_output_limit(self):
        source = '#include <stdio.h>\nint main(void){until(1)output("hello\\n");}'
        outcome = self.backend.run(self.compile(source))
        self.assertEqual(outcome.reason, "output limit")
        self.assertLessEqual(len(self.output().encode()), self.backend.OUTPUT_LIMIT)

    def test_local_header_and_spaces_in_paths(self):
        include_folder = self.project / "my headers & code"
        include_folder.mkdir(exist_ok=True)
        (include_folder / "helper.h").write_text("static int answer(void){return 42;}\n")
        source = '#include "helper.h"\nint main(void){provide answer();}'
        outcome = self.backend.run(self.compile(source, source_folder=include_folder))
        self.assertEqual(outcome.returncode, 42)

    def test_keyword_changes_without_rebuilding_frontend(self):
        first = self.compile('#include <stdio.h>\nint main(void){output("first");provide 0;}')
        translator = next(path for path in (self.project / "build").glob("customc*")
                          if path.is_file())
        modified = translator.stat().st_mtime_ns
        config = self.config.replace("printf = output", "printf = display")
        second = self.backend.build(
            '#include <stdio.h>\nint main(void){display("changed");provide 0;}', config)
        self.assertEqual(translator.stat().st_mtime_ns, modified)
        self.assertEqual(self.backend.run(second).returncode, 0)
        self.assertIn("changed", self.output())
        self.assertTrue(first.generated.exists())

    def test_translate_only(self):
        result = self.compile('int main(void){when(1)provide 7;given provide 0;}',
                              translate_only=True)
        self.assertIsNone(result.executable)
        self.assertIn("if(1)return 7;else return 0;", result.generated.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)

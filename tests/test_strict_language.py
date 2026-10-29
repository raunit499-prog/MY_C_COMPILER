# My test strict language module for this compiler project.
"""I check strict vocabulary, foreign syntax and original-source diagnostics."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gui"))
from backend import BuildError, CompilerBackend


class StrictLanguageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="my strict tests ")
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        shutil.copytree(ROOT / "custom-keywords", self.project / "custom-keywords")
        (self.project / "gui").mkdir()
        shutil.copy(ROOT / "gui/runtime_io.h", self.project / "gui/runtime_io.h")
        self.events = []
        self.backend = CompilerBackend(self.project, lambda k, v: self.events.append((k, v)))
        self.config = (ROOT / "custom-keywords/keywords.cfg").read_text()

    def reject(self, source, row=None, column=None, config=None):
        self.events.clear()
        with self.assertRaises(BuildError):
            self.backend.build(source, self.config if config is None else config)
        diagnostics = [v for k, v in self.events if k == "diagnostic" and "error" in v["severity"]]
        self.assertTrue(diagnostics, self.events)
        if row is not None:
            self.assertEqual(diagnostics[0]["line"], row, diagnostics)
        if column is not None:
            self.assertEqual(diagnostics[0]["column"], column, diagnostics)
        return diagnostics

    def test_all_thirteen_standard_spellings_rejected(self):
        for standard, alias in [line.split(" = ") for line in self.config.splitlines()
                                if " = " in line and not line.startswith("#")]:
            with self.subTest(standard=standard):
                d = self.reject("int main(void) {\n    " + standard + ";\n}\n", 2, 5)
                self.assertIn("use '" + alias + "'", d[0]["message"])

    def test_comments_strings_and_types_work(self):
        source = '#include <stdio.h>\nint main(void){/* printf if for */ output("printf scanf if while"); provide 0;}'
        result = self.backend.build(source, self.config)
        self.assertEqual(self.backend.run(result).returncode, 0)

    def test_original_column_after_shorter_translation(self):
        source = '#include <stdio.h>\nint main(void) {\n    when (1) { missing = 2; }\n}\n'
        self.reject(source, 3, source.splitlines()[2].index("missing") + 1)

    def test_original_column_after_longer_translation(self):
        config = self.config.replace("if = when", "if = extremely_long_condition")
        source = "int main(void){ extremely_long_condition(1) { unknown = 3; } }"
        self.reject(source, 1, source.index("unknown") + 1, config)

    def test_crlf_and_spliced_word_diagnostic(self):
        source = '#include <stdio.h>\r\nint main(void){\r\nout\\\r\nput("x"); missing = 1;\r\n}\r\n'
        self.reject(source, 4, source.splitlines()[3].index("missing") + 1)

    def test_cr_only_line_endings_keep_original_locations(self):
        source = '#include <stdio.h>\rint main(void){\r output("x"); missing=1;\r}'
        self.reject(source, 3, 15)

    def test_unicode_and_tab_location(self):
        source = '#include <stdio.h>\nint main(void){ output("π");\tmissing = 1; }\n'
        self.reject(source, 2, source.splitlines()[1].index("missing") + 1)

    def test_native_error_location_after_splicing(self):
        source = "int main(void){\r\n    out\\\r\nput(\"x\"); return 0;\r\n}"
        self.reject(source, 3, source.splitlines()[2].index("return") + 1)

    def test_foreign_language_examples_rejected(self):
        for source in ['def hello():\n    print("hello")\n', 'console.log("hello");',
                       '#include <iostream>\nint main(){std::cout << "hello";}',
                       'public class Main { public static void main(String[] args) {} }']:
            with self.subTest(source=source):
                self.reject(source)

    def test_missing_semicolon_and_unknown_function_rejected(self):
        self.reject('int main(void){ int n = 1 provide n; }')
        self.reject('int main(void){ totally_unknown(); provide 0; }')

    def test_standard_word_in_macro_rejected(self):
        self.reject('#define P printf\nint main(void){provide 0;}', 1, 11)

    def test_conditional_directive_allowed(self):
        self.backend.build('#if 1\nint main(void){provide 0;}\n#endif\n', self.config)

    def test_config_cannot_restore_standard_spelling(self):
        self.events.clear()
        with self.assertRaises(BuildError):
            self.backend.build('int main(void){provide 0;}', self.config.replace("printf = output", "printf = printf"))
        self.assertIn("requires a nonstandard", "".join(str(v) for k, v in self.events if k == "log"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

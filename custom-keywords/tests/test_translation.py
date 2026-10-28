# My test translation module for this compiler project.
"""Optional integration tests; normal project use needs only C and GCC."""
import pathlib
import subprocess
import tempfile
import unittest
import os


PROJECT = pathlib.Path(__file__).resolve().parents[1]
SUFFIX = ".exe" if os.name == "nt" else ""


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory()
        cls.compiler = pathlib.Path(cls.build.name) / ("customc" + SUFFIX)
        subprocess.run(
            ["gcc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
             *map(str, [PROJECT / "src" / name
                        for name in ("main.c", "keywords.c", "translate.c")]),
             "-o", str(cls.compiler)],
            check=True, capture_output=True, text=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.folder = pathlib.Path(self.work.name)
        self.source = self.folder / "input.myc"
        self.output = self.folder / "generated.c"

    def translate(self, source, config=None):
        self.source.write_bytes(source if isinstance(source, bytes) else source.encode())
        config_path = PROJECT / "keywords.cfg"
        if config is not None:
            config_path = self.folder / "keywords.cfg"
            defaults = dict(line.split(" = ", 1) for line in (PROJECT / "keywords.cfg").read_text().splitlines()
                            if " = " in line and not line.startswith("#"))
            overrides = dict(line.split("=", 1) for line in config.splitlines() if "=" in line)
            # Invalid/repeated fixtures must reach the actual loader unchanged.
            if all(k.strip() in defaults for k in overrides) and len(overrides) == len(config.splitlines()):
                keys = {k.strip() for k in overrides}
                config = "\n".join(k + "=" + v for k, v in defaults.items() if k not in keys) + "\n" + config
            config_path.write_bytes(config.encode())
        return subprocess.run(
            [str(self.compiler), str(config_path), str(self.source), str(self.output)],
            capture_output=True, text=True, timeout=5,
        )

    def test_all_requested_features_execute(self):
        source = (PROJECT / "examples" / "all_features.myc").read_bytes()
        result = self.translate(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        executable = self.folder / ("demo" + SUFFIX)
        subprocess.run(
            ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
             str(self.output), "-o", str(executable)],
            check=True, capture_output=True, text=True,
        )
        cases = [("1", "case 1"), ("2", "case 2"),
                 ("0", "default"), ("-3", "default"), ("abc", "Invalid input")]
        for value, expected in cases:
            with self.subTest(value=value):
                result = subprocess.run(
                    [str(executable)], input=value + "\n",
                    capture_output=True, text=True, timeout=5,
                )
                self.assertIn(expected, result.stdout)
                self.assertEqual(result.returncode, 1 if value == "abc" else 0)
                if value != "abc":
                    for text in ("for: 1", "for: 3", "while: 0", "while: 1",
                                 "do while: 0",
                                 "Strings stay unchanged: output input each until"):
                        self.assertIn(text, result.stdout)
                    self.assertNotIn("for: 2", result.stdout)
                    self.assertIn("if: positive" if int(value) > 0
                                  else "else: zero or negative", result.stdout)

    def test_complete_identifiers_and_literal_boundaries(self):
        source = (
            'output("output"); // output\n'
            '/* output */ output_count myoutput output2 output;\n'
            'input("%d", &number);'
        )
        result = self.translate(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.output.read_text(),
            'printf("output"); // output\n'
            '/* output */ output_count myoutput output2 printf;\n'
            'scanf("%d", &number);',
        )

    def test_preprocessor_directives_are_preserved(self):
        source = (
            '#include <output.h>\n#define VALUE output\n'
            '#define VALUE2 /* output\n output */ output\noutput("x");'
        )
        result = self.translate(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(), source[:-len('output("x");')] + 'printf("x");')

    def test_numeric_tokens_and_prefixed_literals_are_preserved(self):
        config = "printf=xFF\nscanf=e3\nfor=L\nif=u8\n"
        source = '0xFF 1e3 1e+3 .5 L"L" u8"u8" xFF e3 L u8'
        result = self.translate(source, config)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(),
                         '0xFF 1e3 1e+3 .5 L"L" u8"u8" printf scanf for if')

    def test_line_endings_bom_and_splicing(self):
        result = self.translate(b'\xef\xbb\xbfout\\\r\nput("x");\r\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_bytes(), b'printf("x");\n')

    def test_configuration_changes_need_no_rebuild(self):
        result = self.translate('display("Hello");', "printf=display\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(), 'printf("Hello");')

    def test_bad_config_does_not_overwrite_output(self):
        configs = [
            "printf=x\nscanf=x\n", "if=when\ncase=when\n",
            "printf=for\n", "for=while\n", "printf=main\n", "printf=int\n",
            "printf=123abc\n", "printf=two words\n", "printf=\n",
            "printf=x\nprintf=y\n", "unknown=x\n", "printf x\n",
            "printf=" + "x" * 64 + "\n", "printf=x\x00y\n", "x" * 256 + "\n",
        ]
        for config in configs:
            with self.subTest(config=config[:60]):
                self.output.write_bytes(b"KEEP")
                result = self.translate('int main(void){provide 0;}', config)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.output.read_bytes(), b"KEEP")

    def test_bad_source_does_not_overwrite_output(self):
        sources = ['output("unfinished);', "/* unfinished", "char c='x;",
                   'output("line\nbreak");', "int main(){}\x00",
                   " " * (1024 * 1024 + 1)]
        for source in sources:
            with self.subTest(source=source[:40]):
                self.output.write_bytes(b"KEEP")
                result = self.translate(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.output.read_bytes(), b"KEEP")

    def test_parenthesized_switch_labels_and_if_both_work(self):
        result = self.translate(
            'choose (value) { match (1 + 2): when (flag) output("ok"); snap; }'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.output.read_text(),
            'switch (value) { case (1 + 2): if (flag) printf("ok"); break; }',
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

# My diagnostics module for this compiler project.
"""I map translator/GCC locations back to the custom source in my editor."""
from bisect import bisect_right
import re

TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|(?:u8|[LuU])?(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|[A-Za-z_\u0080-\uffff]\w*|\s+|.', re.S)
HEADER = re.compile(r"^(.+?):(\d+):(\d+):\s*(fatal error|error|warning|note):\s*(.*)$")


def normalized_source(source):
    """I retain an original character offset for every normalized character."""
    chars, offsets = [], []
    i = 1 if source.startswith("\ufeff") else 0
    while i < len(source):
        offsets.append(i)
        if source[i] == "\r":
            chars.append("\n")
            i += 2 if source[i:i + 2] == "\r\n" else 1
        else:
            chars.append(source[i])
            i += 1
    text = "".join(chars)
    result, positions = [], []
    i = 0
    while i < len(text):
        if text[i:i + 2] == "\\\n":
            i += 2
        else:
            result.append(text[i])
            positions.append(offsets[i])
            i += 1
    positions.append(len(source))
    return "".join(result), positions


class SourceDiagnostics:
    def __init__(self, source, input_path, generated_path, emit, config_path=None, config=""):
        self.config_path = str(config_path)
        self.config = config
        self.source = source
        self.input_path = str(input_path)
        self.generated_path = str(generated_path)
        self.emit = emit
        self.original_lines = source.splitlines()
        self.starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self.normalized, self.positions = normalized_source(source)

    def mapping(self, generated):
        original_tokens = list(TOKEN.finditer(self.normalized))
        generated_tokens = list(TOKEN.finditer(generated))
        if len(original_tokens) != len(generated_tokens):
            return None
        offsets = []
        for original, translated in zip(original_tokens, generated_tokens):
            if original.group() == translated.group():
                offsets.extend(self.positions[original.start():original.end()])
            else:
                offsets.extend([self.positions[original.start()]] * len(translated.group()))
        offsets.append(len(self.source))
        return offsets

    def format(self, text):
        generated = None
        try:
            from pathlib import Path
            generated = Path(self.generated_path).read_text(encoding="utf-8")
        except OSError:
            pass
        output = []
        skipping_excerpt = False
        for line in text.splitlines():
            config_match = re.match(re.escape(self.config_path) + r":(\d+): error: (.*)$", line)
            if config_match:
                row, message = config_match.groups()
                row = int(row)
                config_lines = self.config.splitlines()
                snippet = config_lines[row - 1] if row <= len(config_lines) else ""
                output.extend([f"keywords.cfg:{row}:1: error: {message}",
                               f" {row:4} | {snippet}", "      | ^"])
                self.emit("diagnostic", {"line": row, "column": 1, "severity": "error",
                                         "message": message, "source": self.config, "target": "config"})
                continue
            match = HEADER.match(line)
            if not match:
                # I replace GCC's generated-source excerpt with my original source.
                if skipping_excerpt and (re.match(r"^\s*\d+\s*\|", line) or
                                          re.match(r"^\s*\|", line)):
                    continue
                skipping_excerpt = False
                output.append(line)
                continue
            filename, row, column, severity, message = match.groups()
            if filename not in (self.input_path, self.generated_path):
                output.append(line)  # Included headers keep their own real locations.
                skipping_excerpt = False
                continue
            body = generated if filename == self.generated_path else self.source
            positions = self.mapping(body) if filename == self.generated_path else list(range(len(self.source) + 1))
            if body is None or positions is None:
                output.append(line)
                continue
            rows = body.splitlines(keepends=True)
            row, column = int(row), int(column)
            before = sum(map(len, rows[:row - 1]))
            physical = rows[row - 1] if row <= len(rows) else ""
            # Both GCC (with my flag) and the C scanner report byte columns.
            character = len(physical.encode("utf-8")[:column - 1].decode("utf-8", "ignore"))
            offset = positions[min(before + character, len(positions) - 1)]
            original_row = bisect_right(self.starts, offset)
            original_column = offset - self.starts[original_row - 1] + 1
            original_line = self.original_lines[original_row - 1] if original_row <= len(self.original_lines) else ""
            prefix = original_line[:original_column - 1].expandtabs(8)
            output.extend([
                f"source.myc:{original_row}:{original_column}: {severity}: {message}",
                f" {original_row:4} | {original_line.expandtabs(8)}",
                "      | " + " " * len(prefix) + "^",
            ])
            self.emit("diagnostic", {
                "line": original_row, "column": original_column,
                "severity": severity, "message": message, "source": self.source,
            })
            skipping_excerpt = True
        return "\n".join(output) + ("\n" if output else "")

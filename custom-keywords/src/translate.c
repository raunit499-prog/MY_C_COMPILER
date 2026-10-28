/* My translate module for this compiler project. */
#include "translate.h"

#include <string.h>

/* I retain original byte locations while normalizing my 1 MiB source limit. */
static unsigned source_lines[1024 * 1024 + 4];
static unsigned source_columns[1024 * 1024 + 4];
static int locations_ready;

static int letter(unsigned char c) {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

static int digit(unsigned char c) {
  return c >= '0' && c <= '9';
}

static int identifier_start(unsigned char c) {
  return letter(c) || c == '_' || c >= 128;
}

static int identifier_part(unsigned char c) {
  return identifier_start(c) || digit(c);
}

void normalize_source(char *source) {
  unsigned line = 1, column = 1;
  size_t n = 0;
  for (; source[n] != '\0'; n++) {
    source_lines[n] = line;
    source_columns[n] = column;
    if (source[n] == '\r') { line++; column = 1; }
    else if (source[n] == '\n') {
      if (n == 0 || source[n - 1] != '\r') line++;
      column = 1;
    } else column++;
  }
  source_lines[n] = line;
  source_columns[n] = column;
  locations_ready = 1;
  size_t read_pos = 0, write_pos = 0;
  if ((unsigned char)source[0] == 0xef &&
      (unsigned char)source[1] == 0xbb &&
      (unsigned char)source[2] == 0xbf) read_pos = 3;
  /* First normalize CRLF / CR to LF, without changing other bytes. */
  while (source[read_pos] != '\0') {
    if (source[read_pos] == '\r') {
      source_lines[write_pos] = source_lines[read_pos];
      source_columns[write_pos] = source_columns[read_pos];
      source[write_pos++] = '\n';
      read_pos++;
      if (source[read_pos] == '\n') read_pos++;
    } else {
      source_lines[write_pos] = source_lines[read_pos];
      source_columns[write_pos] = source_columns[read_pos];
      source[write_pos++] = source[read_pos++];
    }
  }
  source_lines[write_pos] = source_lines[read_pos];
  source_columns[write_pos] = source_columns[read_pos];
  source[write_pos] = '\0';
  read_pos = write_pos = 0;
  while (source[read_pos] != '\0') {
    if (source[read_pos] == '\\' && source[read_pos + 1] == '\n') {
      read_pos += 2;
    } else {
      source_lines[write_pos] = source_lines[read_pos];
      source_columns[write_pos] = source_columns[read_pos];
      source[write_pos++] = source[read_pos++];
    }
  }
  source_lines[write_pos] = source_lines[read_pos];
  source_columns[write_pos] = source_columns[read_pos];
  source[write_pos] = '\0';
}

/* Return the offset of the quote for a regular or prefixed C literal. */
static int literal_quote_offset(const char *source) {
  if (source[0] == '"' || source[0] == '\'') return 0;
  if ((source[0] == 'L' || source[0] == 'u' || source[0] == 'U') &&
      (source[1] == '"' || source[1] == '\'')) return 1;
  if (source[0] == 'u' && source[1] == '8' &&
      (source[2] == '"' || source[2] == '\'')) return 2;
  return -1;
}

static int lexical_error(const char *filename, const char *source, size_t position,
                         const char *message) {
  size_t line = 1, column = 1;
  for (size_t i = 0; i < position; i++) {
    if (source[i] == '\n') { line++; column = 1; }
    else column++;
  }
  if (locations_ready) { line = source_lines[position]; column = source_columns[position]; }
  fprintf(stderr, "%s:%zu:%zu: error: %s\n", filename, line, column, message);
  return 0;
}

int translate_source(const char *source, const char *filename,
                     const KeywordMap *map, FILE *output, size_t *replacements) {
  size_t i = 0;
  int line_prefix = 1;
  int in_directive = 0;
  int directive_name = 0;
  *replacements = 0;
  while (source[i] != '\0') {
    size_t start = i;
    unsigned char c = (unsigned char)source[i];
    if (c == '\n' || c == ' ' || c == '\t' || c == '\v' || c == '\f') {
      if (c == '\n') { line_prefix = 1; in_directive = 0; }
      fputc(c, output);
      i++;
      continue;
    }
    if (c == '/' && source[i + 1] == '/') {
      while (source[i] != '\0' && source[i] != '\n') i++;
      fwrite(source + start, 1, i - start, output);
      continue;
    }
    if (c == '/' && source[i + 1] == '*') {
      i += 2;
      while (source[i] != '\0' && !(source[i] == '*' && source[i + 1] == '/')) i++;
      if (source[i] == '\0') {
        return lexical_error(filename, source, start, "unterminated block comment");
      }
      i += 2;
      fwrite(source + start, 1, i - start, output);
      /* A comment acts as whitespace, including inside a directive. */
      continue;
    }
    if (c == '#' && line_prefix) {
      in_directive = 1;
      directive_name = 1;
      line_prefix = 0;
      fputc(c, output);
      i++;
      continue;
    }
    int offset = literal_quote_offset(source + i);
    if (offset >= 0) {
      i += (size_t)offset;
      char quote = source[i++];
      while (source[i] != '\0' && source[i] != quote && source[i] != '\n') {
        if (source[i] == '\\') {
          i++;
          if (source[i] == '\0' || source[i] == '\n') break;
        }
        i++;
      }
      if (source[i] != quote) {
        return lexical_error(filename, source, start, "unterminated string or character literal");
      }
      i++;
      fwrite(source + start, 1, i - start, output);
      line_prefix = 0;
      continue;
    }
    /* Keep numeric preprocessing tokens together (e.g. 0xFF and 1e+3). */
    if (digit(c) || (c == '.' && digit((unsigned char)source[i + 1]))) {
      i++;
      for (;;) {
        unsigned char next = (unsigned char)source[i];
        char previous = source[i - 1];
        if (identifier_part(next) || next == '.') i++;
        else if ((next == '+' || next == '-') &&
                 (previous == 'e' || previous == 'E' ||
                  previous == 'p' || previous == 'P')) i++;
        else break;
      }
      fwrite(source + start, 1, i - start, output);
      line_prefix = 0;
      continue;
    }
    if (identifier_start(c)) {
      i++;
      while (identifier_part((unsigned char)source[i])) i++;
      size_t length = i - start;
      /* I reject the old spelling only when its configured alias differs. */
      for (size_t k = 0; !(in_directive && directive_name) && k < KEYWORD_COUNT; k++) {
        const Keyword *entry = &map->entries[k];
        if (strcmp(entry->standard_name, entry->custom_name) != 0 &&
            strlen(entry->standard_name) == length &&
            strncmp(source + start, entry->standard_name, length) == 0) {
          char message[192];
          snprintf(message, sizeof(message),
                   "standard spelling '%s' is disabled; use '%s' instead",
                   entry->standard_name, entry->custom_name);
          return lexical_error(filename, source, start, message);
        }
      }
      directive_name = 0;
      const char *replacement = in_directive ? NULL :
                                keywords_lookup(map, source + start, length);
      if (replacement != NULL) {
        fputs(replacement, output);
        if (strlen(replacement) != length ||
            strncmp(source + start, replacement, length) != 0) (*replacements)++;
      } else {
        fwrite(source + start, 1, length, output);
      }
      line_prefix = 0;
      continue;
    }
    fputc(c, output);
    i++;
    line_prefix = 0;
  }
  if (ferror(output)) {
    fputs("error: could not write translated source\n", stderr);
    return 0;
  }
  return 1;
}

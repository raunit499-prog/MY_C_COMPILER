/* My keywords module for this compiler project. */
#include "keywords.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

static const char *const standard_names[KEYWORD_COUNT] = {
  "printf", "scanf", "for", "if", "else", "while", "do",
  "switch", "case", "default", "break", "continue", "return"
};

/* A custom name must not take over another C keyword. */
static const char *const c_keywords[] = {
  "auto", "break", "case", "char", "const", "continue", "default", "do",
  "double", "else", "enum", "extern", "float", "for", "goto", "if",
  "inline", "int", "long", "register", "restrict", "return", "short",
  "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
  "unsigned", "void", "volatile", "while", "_Alignas", "_Alignof",
  "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary", "_Noreturn",
  "_Static_assert", "_Thread_local"
};

static int ascii_letter(unsigned char c) {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

static int valid_alias(const char *name) {
  size_t length = strlen(name);
  if (length == 0 || length > MAX_ALIAS_LENGTH ||
      !ascii_letter((unsigned char)name[0])) return 0;
  for (size_t i = 1; i < length; i++) {
    unsigned char c = (unsigned char)name[i];
    if (!ascii_letter(c) && !(c >= '0' && c <= '9') && c != '_') return 0;
  }
  return 1;
}

static char *trim(char *text) {
  while (isspace((unsigned char)*text)) text++;
  size_t length = strlen(text);
  while (length > 0 && isspace((unsigned char)text[length - 1])) {
    text[--length] = '\0';
  }
  return text;
}

static int config_error(const char *filename, size_t line, const char *message) {
  fprintf(stderr, "%s:%zu: error: %s\n", filename, line, message);
  return 0;
}

int keywords_load(KeywordMap *map, const char *filename) {
  for (size_t i = 0; i < KEYWORD_COUNT; i++) {
    map->entries[i].standard_name = standard_names[i];
    strcpy(map->entries[i].custom_name, standard_names[i]);
    map->entries[i].configured = 0;
    map->entries[i].config_line = 1;
  }
  FILE *file = fopen(filename, "rb");
  if (file == NULL) {
    perror(filename);
    return 0;
  }
  size_t line_number = 0;
  for (;;) {
    char line[256];
    size_t length = 0;
    int c;
    while ((c = fgetc(file)) != EOF && c != '\n') {
      if (c == 0 || length == sizeof(line) - 1) {
        fclose(file);
        return config_error(filename, line_number + 1,
                            "config line is too long or contains a NUL byte");
      }
      line[length++] = (char)c;
    }
    if (c == EOF && length == 0) break;
    line[length] = '\0';
    line_number++;
    /* Accept the UTF-8 BOM that some Windows editors add to text files. */
    char *start = line;
    if (line_number == 1 && length >= 3 &&
        (unsigned char)line[0] == 0xef &&
        (unsigned char)line[1] == 0xbb &&
        (unsigned char)line[2] == 0xbf) start += 3;
    char *comment = strchr(start, '#');
    if (comment != NULL) *comment = '\0';
    char *key = trim(start);
    if (*key == '\0') continue;
    char *equal = strchr(key, '=');
    if (equal == NULL) {
      fclose(file);
      return config_error(filename, line_number, "expected standard_name = custom_name");
    }
    *equal = '\0';
    key = trim(key);
    char *alias = trim(equal + 1);
    if (!valid_alias(alias)) {
      fclose(file);
      return config_error(filename, line_number,
                          "name must start with an ASCII letter and contain only letters, digits or underscores (maximum 63 characters)");
    }
    size_t index = 0;
    while (index < KEYWORD_COUNT && strcmp(key, standard_names[index]) != 0) index++;
    if (index == KEYWORD_COUNT || map->entries[index].configured) {
      fclose(file);
      return config_error(filename, line_number, "unknown or repeated standard name");
    }
    strcpy(map->entries[index].custom_name, alias);
    map->entries[index].configured = 1;
    map->entries[index].config_line = line_number;
  }
  int failed = ferror(file);
  fclose(file);
  if (failed) return config_error(filename, line_number, "could not read config");

  for (size_t i = 0; i < KEYWORD_COUNT; i++) {
    const char *alias = map->entries[i].custom_name;
    const char *standard = map->entries[i].standard_name;
    if (strcmp(alias, standard) == 0) {
      return config_error(filename, map->entries[i].config_line,
                          "each renamed word requires a nonstandard custom spelling");
    }
    if (strcmp(alias, "main") == 0) {
      return config_error(filename, map->entries[i].config_line, "main cannot be used as an alias");
    }
    for (size_t j = 0; j < KEYWORD_COUNT; j++) {
      if (i != j && strcmp(alias, map->entries[j].custom_name) == 0) {
        return config_error(filename, map->entries[i].config_line, "two entries cannot use the same custom name");
      }
      if (strcmp(alias, standard_names[j]) == 0 && strcmp(alias, standard) != 0) {
        return config_error(filename, map->entries[i].config_line, "alias conflicts with another standard name");
      }
    }
    for (size_t j = 0; j < sizeof(c_keywords) / sizeof(c_keywords[0]); j++) {
      if (strcmp(alias, c_keywords[j]) == 0 && strcmp(alias, standard) != 0) {
        return config_error(filename, map->entries[i].config_line, "alias conflicts with a C keyword");
      }
    }
  }
  return 1;
}

const char *keywords_lookup(const KeywordMap *map, const char *word, size_t length) {
  for (size_t i = 0; i < KEYWORD_COUNT; i++) {
    if (strlen(map->entries[i].custom_name) == length &&
        strncmp(map->entries[i].custom_name, word, length) == 0) {
      return map->entries[i].standard_name;
    }
  }
  return NULL;
}

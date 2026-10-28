/* My keywords module for this compiler project. */
#ifndef KEYWORDS_H
#define KEYWORDS_H

#include <stddef.h>

#define KEYWORD_COUNT 13
#define MAX_ALIAS_LENGTH 63

typedef struct {
  const char *standard_name;
  char custom_name[MAX_ALIAS_LENGTH + 1];
  int configured;
  size_t config_line;
} Keyword;

typedef struct {
  Keyword entries[KEYWORD_COUNT];
} KeywordMap;

int keywords_load(KeywordMap *map, const char *filename);
const char *keywords_lookup(const KeywordMap *map, const char *word, size_t length);

#endif

/* My translate module for this compiler project. */
#ifndef TRANSLATE_H
#define TRANSLATE_H

#include <stdio.h>
#include "keywords.h"

/* Normalize line endings and apply ordinary C backslash-newline splicing. */
void normalize_source(char *source);
int translate_source(const char *source, const char *filename,
                     const KeywordMap *map, FILE *output, size_t *replacements);

#endif

/* My main module for this compiler project. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "translate.h"

#define MAX_SOURCE_SIZE (1024 * 1024)

static char *read_source(const char *filename) {
  FILE *file = fopen(filename, "rb");
  if (file == NULL) { perror(filename); return NULL; }
  /* Extra zero bytes make limited lookahead safe, even for empty inputs. */
  char *source = calloc(MAX_SOURCE_SIZE + 4, 1);
  if (source == NULL) {
    fputs("error: could not allocate source buffer\n", stderr);
    fclose(file);
    return NULL;
  }
  size_t length = 0;
  int c;
  while ((c = fgetc(file)) != EOF) {
    if (c == 0 || length == MAX_SOURCE_SIZE) {
      fputs("error: source must be at most 1 MiB and contain no NUL bytes\n", stderr);
      free(source);
      fclose(file);
      return NULL;
    }
    source[length++] = (char)c;
  }
  int failed = ferror(file);
  fclose(file);
  if (failed) {
    fputs("error: could not read source file\n", stderr);
    free(source);
    return NULL;
  }
  normalize_source(source);
  return source;
}

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "Usage: %s keywords.cfg input.myc output.c\n", argv[0]);
    return EXIT_FAILURE;
  }
  size_t output_length = strlen(argv[3]);
  if (strcmp(argv[2], argv[3]) == 0 || output_length < 2 ||
      strcmp(argv[3] + output_length - 2, ".c") != 0) {
    fputs("error: choose a different output path ending in .c\n", stderr);
    return EXIT_FAILURE;
  }
  KeywordMap map;
  if (!keywords_load(&map, argv[1])) return EXIT_FAILURE;
  char *source = read_source(argv[2]);
  if (source == NULL) return EXIT_FAILURE;

  /* Validate and translate first, so lexical errors leave existing output alone. */
  FILE *temporary = tmpfile();
  if (temporary == NULL) {
    perror("temporary output");
    free(source);
    return EXIT_FAILURE;
  }
  size_t replacements = 0;
  int ok = translate_source(source, argv[2], &map, temporary, &replacements);
  free(source);
  if (!ok || fflush(temporary) != 0 || fseek(temporary, 0, SEEK_SET) != 0) {
    fputs("error: translation did not complete\n", stderr);
    fclose(temporary);
    return EXIT_FAILURE;
  }
  FILE *output = fopen(argv[3], "wb");
  if (output == NULL) {
    perror(argv[3]);
    fclose(temporary);
    return EXIT_FAILURE;
  }
  char buffer[4096];
  size_t count;
  while ((count = fread(buffer, 1, sizeof(buffer), temporary)) != 0) {
    if (fwrite(buffer, 1, count, output) != count) { ok = 0; break; }
  }
  if (ferror(temporary) || ferror(output)) ok = 0;
  fclose(temporary);
  if (fclose(output) != 0) ok = 0;
  if (!ok) {
    fputs("error: could not finish output file\n", stderr);
    return EXIT_FAILURE;
  }
  printf("Translated %s -> %s (%zu custom tokens)\n", argv[2], argv[3], replacements);
  return EXIT_SUCCESS;
}

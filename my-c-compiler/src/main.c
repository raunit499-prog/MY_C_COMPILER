/* My main module for this compiler project. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "codegen.h"

#define MAX_SOURCE_SIZE 16384

static void read_source(const char *filename, char *source) {
  FILE *input = fopen(filename, "rb");
  if (input == NULL) {
    perror(filename);
    exit(EXIT_FAILURE);
  }
  size_t length = 0;
  int c;
  while ((c = fgetc(input)) != EOF) {
    if (length == MAX_SOURCE_SIZE || c == 0) {
      fprintf(stderr, "error: source must be at most 16384 bytes with no NUL bytes\n");
      fclose(input);
      exit(EXIT_FAILURE);
    }
    source[length++] = (char)c;
  }
  if (ferror(input)) {
    fprintf(stderr, "error: could not read %s\n", filename);
    fclose(input);
    exit(EXIT_FAILURE);
  }
  fclose(input);
  source[length] = '\0';
}

int main(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "Usage: %s input.c output.s\n"
                    "   or: %s --tokens input.c\n", argv[0], argv[0]);
    return EXIT_FAILURE;
  }
  int tokens_only = strcmp(argv[1], "--tokens") == 0;
  const char *filename = tokens_only ? argv[2] : argv[1];
  char source[MAX_SOURCE_SIZE + 1];
  read_source(filename, source);

  if (tokens_only) {
    Lexer lexer;
    lexer_init(&lexer, filename, source);
    while (lexer.current.kind != TK_END) {
      Token token = lexer.current;
      printf("%zu:%zu\t%.*s\n", token.line, token.column,
             (int)token.length, token.start);
      lexer_next(&lexer);
    }
    puts("<end of file>");
    return EXIT_SUCCESS;
  }

  if (strcmp(argv[1], argv[2]) == 0) {
    fputs("error: input and output paths must be different\n", stderr);
    return EXIT_FAILURE;
  }
  Parser parser;
  parser_init(&parser, filename, source);
  Node *root = parse_program(&parser);
  FILE *output = fopen(argv[2], "w");
  if (output == NULL) {
    perror(argv[2]);
    return EXIT_FAILURE;
  }
  generate_assembly(output, root);
  int failed = ferror(output);
  if (fclose(output) != 0) failed = 1;
  if (failed) {
    fputs("error: could not write assembly output\n", stderr);
    return EXIT_FAILURE;
  }
  printf("Compiled %s -> %s\n", filename, argv[2]);
  return EXIT_SUCCESS;
}

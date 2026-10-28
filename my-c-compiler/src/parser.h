/* My parser module for this compiler project. */
#ifndef PARSER_H
#define PARSER_H

#include "lexer.h"

#define MAX_NODES 256
#define MAX_EXPRESSION_NESTING 64

typedef enum {
  NODE_NUMBER, NODE_ADD, NODE_SUBTRACT, NODE_MULTIPLY, NODE_DIVIDE, NODE_NEGATE
} NodeKind;

typedef struct Node {
  NodeKind kind;
  int value;
  struct Node *left;
  struct Node *right;
} Node;

typedef struct {
  Lexer lexer;
  Node nodes[MAX_NODES];
  size_t node_count;
  unsigned nesting;
} Parser;

void parser_init(Parser *parser, const char *filename, const char *source);
Node *parse_program(Parser *parser);

#endif

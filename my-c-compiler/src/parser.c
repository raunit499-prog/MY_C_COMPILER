/* My parser module for this compiler project. */
#include "parser.h"

#include <string.h>

static Node *parse_expression(Parser *parser);

static void expect(Parser *parser, TokenKind kind, const char *message) {
  if (parser->lexer.current.kind != kind) {
    compiler_error(&parser->lexer, &parser->lexer.current, message);
  }
  lexer_next(&parser->lexer);
}

static Node *new_node(Parser *parser, NodeKind kind, int value,
                      Node *left, Node *right) {
  if (parser->node_count == MAX_NODES) {
    compiler_error(&parser->lexer, &parser->lexer.current,
                   "expression is too large (maximum 256 tree nodes)");
  }
  Node *node = &parser->nodes[parser->node_count++];
  node->kind = kind;
  node->value = value;
  node->left = left;
  node->right = right;
  return node;
}

/* A factor is a number, a signed factor, or a parenthesized expression. */
static Node *parse_factor(Parser *parser) {
  if (++parser->nesting > MAX_EXPRESSION_NESTING) {
    compiler_error(&parser->lexer, &parser->lexer.current,
                   "expression nesting exceeds 64");
  }
  Token token = parser->lexer.current;
  Node *node;
  if (token.kind == TK_NUMBER) {
    lexer_next(&parser->lexer);
    node = new_node(parser, NODE_NUMBER, token.value, NULL, NULL);
  } else if (token.kind == TK_PLUS || token.kind == TK_MINUS) {
    lexer_next(&parser->lexer);
    node = parse_factor(parser);
    if (token.kind == TK_MINUS) {
      node = new_node(parser, NODE_NEGATE, 0, node, NULL);
    }
  } else if (token.kind == TK_LPAREN) {
    lexer_next(&parser->lexer);
    node = parse_expression(parser);
    expect(parser, TK_RPAREN, "expected ')' after expression");
  } else {
    compiler_error(&parser->lexer, &token, "expected a number, sign, or '('");
    return NULL;
  }
  parser->nesting--;
  return node;
}

/* Multiplication and division bind more tightly than addition/subtraction. */
static Node *parse_term(Parser *parser) {
  Node *left = parse_factor(parser);
  while (parser->lexer.current.kind == TK_STAR ||
         parser->lexer.current.kind == TK_SLASH) {
    TokenKind operator_kind = parser->lexer.current.kind;
    lexer_next(&parser->lexer);
    Node *right = parse_factor(parser);
    left = new_node(parser,
                    operator_kind == TK_STAR ? NODE_MULTIPLY : NODE_DIVIDE,
                    0, left, right);
  }
  return left;
}

static Node *parse_expression(Parser *parser) {
  Node *left = parse_term(parser);
  while (parser->lexer.current.kind == TK_PLUS ||
         parser->lexer.current.kind == TK_MINUS) {
    TokenKind operator_kind = parser->lexer.current.kind;
    lexer_next(&parser->lexer);
    Node *right = parse_term(parser);
    left = new_node(parser,
                    operator_kind == TK_PLUS ? NODE_ADD : NODE_SUBTRACT,
                    0, left, right);
  }
  return left;
}

void parser_init(Parser *parser, const char *filename, const char *source) {
  memset(parser, 0, sizeof(*parser));
  lexer_init(&parser->lexer, filename, source);
}

Node *parse_program(Parser *parser) {
  expect(parser, TK_INT, "expected 'int' at the start of the program");
  expect(parser, TK_MAIN, "expected 'main'");
  expect(parser, TK_LPAREN, "expected '(' after main");
  if (parser->lexer.current.kind == TK_VOID) {
    lexer_next(&parser->lexer);
  }
  expect(parser, TK_RPAREN, "expected ')' (parameters are not supported yet)");
  expect(parser, TK_LBRACE, "expected '{' to begin main");
  expect(parser, TK_RETURN, "expected a return statement");
  Node *result = parse_expression(parser);
  expect(parser, TK_SEMICOLON, "expected ';' after return expression");
  expect(parser, TK_RBRACE, "expected '}' after return statement");
  expect(parser, TK_END, "unexpected text after main");
  return result;
}

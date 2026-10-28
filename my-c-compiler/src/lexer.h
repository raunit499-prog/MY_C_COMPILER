/* My lexer module for this compiler project. */
#ifndef LEXER_H
#define LEXER_H

#include <stddef.h>

typedef enum {
  TK_END, TK_NUMBER, TK_INT, TK_MAIN, TK_VOID, TK_RETURN,
  TK_PLUS, TK_MINUS, TK_STAR, TK_SLASH,
  TK_LPAREN, TK_RPAREN, TK_LBRACE, TK_RBRACE, TK_SEMICOLON
} TokenKind;

typedef struct {
  TokenKind kind;
  const char *start;
  size_t length;
  size_t line;
  size_t column;
  int value;
} Token;

typedef struct {
  const char *filename;
  const char *source;
  size_t position;
  size_t line;
  size_t column;
  Token current;
} Lexer;

void lexer_init(Lexer *lexer, const char *filename, const char *source);
void lexer_next(Lexer *lexer);
void compiler_error(const Lexer *lexer, const Token *token, const char *message);

#endif

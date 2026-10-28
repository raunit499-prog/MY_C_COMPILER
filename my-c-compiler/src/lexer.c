/* My lexer module for this compiler project. */
#include "lexer.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* These helpers move through the source without losing its line numbers. */
static char peek(const Lexer *lexer) {
  return lexer->source[lexer->position];
}

static void advance(Lexer *lexer) {
  if (peek(lexer) == '\n') {
    lexer->line++;
    lexer->column = 1;
  } else {
    lexer->column++;
  }
  lexer->position++;
}

void compiler_error(const Lexer *lexer, const Token *token, const char *message) {
  fprintf(stderr, "%s:%zu:%zu: error: %s\n",
          lexer->filename, token->line, token->column, message);
  exit(EXIT_FAILURE);
}

static Token start_token(const Lexer *lexer) {
  Token token = {TK_END, lexer->source + lexer->position, 0,
                 lexer->line, lexer->column, 0};
  return token;
}

static int word_is(const Token *token, const char *word) {
  return token->length == strlen(word) &&
         strncmp(token->start, word, token->length) == 0;
}

static void skip_space_and_comments(Lexer *lexer) {
  for (;;) {
    while (isspace((unsigned char)peek(lexer))) {
      advance(lexer);
    }
    if (peek(lexer) != '/') {
      return;
    }
    if (lexer->source[lexer->position + 1] == '/') {
      while (peek(lexer) != '\0' && peek(lexer) != '\n') {
        advance(lexer);
      }
    } else if (lexer->source[lexer->position + 1] == '*') {
      Token beginning = start_token(lexer);
      advance(lexer);
      advance(lexer);
      while (peek(lexer) != '\0' &&
             !(peek(lexer) == '*' &&
               lexer->source[lexer->position + 1] == '/')) {
        advance(lexer);
      }
      if (peek(lexer) == '\0') {
        compiler_error(lexer, &beginning, "unterminated block comment");
      }
      advance(lexer);
      advance(lexer);
    } else {
      return;
    }
  }
}

void lexer_next(Lexer *lexer) {
  skip_space_and_comments(lexer);
  Token token = start_token(lexer);
  char c = peek(lexer);

  if (c == '\0') {
    lexer->current = token;
    return;
  }

  if (isdigit((unsigned char)c)) {
    token.kind = TK_NUMBER;
    do {
      int digit = peek(lexer) - '0';
      if (token.value > (2147483647 - digit) / 10) {
        compiler_error(lexer, &token, "integer literal exceeds 2147483647");
      }
      token.value = token.value * 10 + digit;
      advance(lexer);
    } while (isdigit((unsigned char)peek(lexer)));
    token.length = (size_t)(lexer->source + lexer->position - token.start);
    if (token.length > 1 && token.start[0] == '0') {
      compiler_error(lexer, &token,
                     "use decimal literals without leading zeros in this version");
    }
    lexer->current = token;
    return;
  }

  if (isalpha((unsigned char)c) || c == '_') {
    do {
      advance(lexer);
    } while (isalnum((unsigned char)peek(lexer)) || peek(lexer) == '_');
    token.length = (size_t)(lexer->source + lexer->position - token.start);
    if (word_is(&token, "int")) token.kind = TK_INT;
    else if (word_is(&token, "main")) token.kind = TK_MAIN;
    else if (word_is(&token, "void")) token.kind = TK_VOID;
    else if (word_is(&token, "return")) token.kind = TK_RETURN;
    else compiler_error(lexer, &token, "identifier is not supported yet");
    lexer->current = token;
    return;
  }

  /* In C, ++ and -- are single operators, not two unary signs. */
  if ((c == '+' || c == '-') && lexer->source[lexer->position + 1] == c) {
    compiler_error(lexer, &token, "++ and -- are not supported yet");
  }

  switch (c) {
    case '+': token.kind = TK_PLUS; break;
    case '-': token.kind = TK_MINUS; break;
    case '*': token.kind = TK_STAR; break;
    case '/': token.kind = TK_SLASH; break;
    case '(': token.kind = TK_LPAREN; break;
    case ')': token.kind = TK_RPAREN; break;
    case '{': token.kind = TK_LBRACE; break;
    case '}': token.kind = TK_RBRACE; break;
    case ';': token.kind = TK_SEMICOLON; break;
    default: compiler_error(lexer, &token, "character is not supported yet");
  }
  advance(lexer);
  token.length = 1;
  lexer->current = token;
}

void lexer_init(Lexer *lexer, const char *filename, const char *source) {
  memset(lexer, 0, sizeof(*lexer));
  lexer->filename = filename;
  lexer->source = source;
  lexer->line = 1;
  lexer->column = 1;
  lexer_next(lexer);
}

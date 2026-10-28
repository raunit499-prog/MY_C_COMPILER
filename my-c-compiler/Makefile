CC = gcc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic
SOURCES = src/main.c src/lexer.c src/parser.c src/codegen.c

.PHONY: all
all: minic

minic: $(SOURCES) src/lexer.h src/parser.h src/codegen.h
	$(CC) $(CFLAGS) $(SOURCES) -o minic

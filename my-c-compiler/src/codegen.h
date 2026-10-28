/* My codegen module for this compiler project. */
#ifndef CODEGEN_H
#define CODEGEN_H

#include <stdio.h>
#include "parser.h"

void generate_assembly(FILE *output, const Node *root);

#endif

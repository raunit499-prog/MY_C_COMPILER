/* My codegen module for this compiler project. */
#include "codegen.h"

#if !defined(__x86_64__) && !defined(_M_X64)
#error "This teaching compiler currently targets x86-64 only."
#endif

/* Each binary operation saves its left result while calculating its right. */
static size_t stack_slots(const Node *node) {
  if (node->kind == NODE_NUMBER) return 0;
  if (node->kind == NODE_NEGATE) return stack_slots(node->left);
  size_t left = stack_slots(node->left);
  size_t right = 1 + stack_slots(node->right);
  return left > right ? left : right;
}

/* Every expression leaves its 32-bit integer result in the EAX register. */
static void emit_expression(FILE *output, const Node *node, size_t slot) {
  if (node->kind == NODE_NUMBER) {
    fprintf(output, "    movl $%d, %%eax\n", node->value);
    return;
  }
  if (node->kind == NODE_NEGATE) {
    emit_expression(output, node->left, slot);
    fputs("    negl %eax\n", output);
    return;
  }
  emit_expression(output, node->left, slot);
  fprintf(output, "    movl %%eax, %zu(%%rsp)\n", slot * 4);
  emit_expression(output, node->right, slot + 1);
  fputs("    movl %eax, %ecx\n", output);
  fprintf(output, "    movl %zu(%%rsp), %%eax\n", slot * 4);
  switch (node->kind) {
    case NODE_ADD: fputs("    addl %ecx, %eax\n", output); break;
    case NODE_SUBTRACT: fputs("    subl %ecx, %eax\n", output); break;
    case NODE_MULTIPLY: fputs("    imull %ecx, %eax\n", output); break;
    case NODE_DIVIDE:
      fputs("    cltd\n    idivl %ecx\n", output);
      break;
    default: break; /* Number and negation were handled above. */
  }
}

void generate_assembly(FILE *output, const Node *root) {
  size_t slots = stack_slots(root);
  size_t frame = 0;
  if (slots > 0) {
    frame = 8;
    while (frame < slots * 4) frame += 16;
  }

  fputs(".text\n.globl main\n", output);
#ifdef _WIN32
  /* Windows unwind metadata describes this function's fixed stack frame. */
  fputs(".seh_proc main\n", output);
#else
  fputs(".type main, @function\n", output);
#endif
  fputs("main:\n", output);
  if (frame != 0) {
    fprintf(output, "    subq $%zu, %%rsp\n", frame);
#ifdef _WIN32
    fprintf(output, "    .seh_stackalloc %zu\n", frame);
#endif
  }
#ifdef _WIN32
  fputs("    .seh_endprologue\n", output);
#endif
  emit_expression(output, root, 0);
  if (frame != 0) fprintf(output, "    addq $%zu, %%rsp\n", frame);
  fputs("    ret\n", output);
#ifdef _WIN32
  fputs(".seh_endproc\n", output);
#else
  fputs(".size main, .-main\n.section .note.GNU-stack,\"\",@progbits\n", output);
#endif
}

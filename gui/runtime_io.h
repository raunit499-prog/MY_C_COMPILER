/* My runtime io module for this compiler project. */
#ifndef MYC_GUI_RUNTIME_IO_H
#define MYC_GUI_RUNTIME_IO_H
#include <stdio.h>

/* Make prompts visible immediately when stdout is a GUI pipe. */
__attribute__((constructor))
static void myc_gui_initialize_io(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);
}
#endif

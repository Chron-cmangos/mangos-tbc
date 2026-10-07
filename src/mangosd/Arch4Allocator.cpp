// Exactly one translation unit owns global C++ allocation overrides.
// C malloc/free (including allocations owned by external DLLs) are unchanged.
#include <mimalloc-new-delete.h>

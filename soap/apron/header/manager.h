typedef enum ap_exc_t {
  AP_EXC_NONE,
  AP_EXC_TIMEOUT,
  AP_EXC_OUT_OF_SPACE,
  AP_EXC_OVERFLOW,
  AP_EXC_INVALID_ARGUMENT,
  AP_EXC_NOT_IMPLEMENTED,
  AP_EXC_SIZE
} ap_exc_t;

typedef struct ap_funopt_t {
  int algorithm;
  size_t timeout;
  size_t max_object_size;
  bool flag_exact_wanted;
  bool flag_best_wanted;
} ap_funopt_t;

typedef struct { ...; } ap_manager_t;

void ap_manager_clear_exclog(ap_manager_t* man);
void ap_manager_free(ap_manager_t* man);
const char* ap_manager_get_library(ap_manager_t* man);
const char* ap_manager_get_version(ap_manager_t* man);

bool ap_manager_get_abort_if_exception(ap_manager_t* man, ap_exc_t exn);

void ap_funopt_init(ap_funopt_t* fopt);
void ap_manager_set_abort_if_exception(
    ap_manager_t* man, ap_exc_t exn, bool flag);

bool ap_fpu_init(void);


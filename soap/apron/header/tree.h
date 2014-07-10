typedef enum ap_texpr_op_t {
  /* Binary operators */
  AP_TEXPR_ADD,
  AP_TEXPR_SUB,
  AP_TEXPR_MUL,
  AP_TEXPR_DIV,
  AP_TEXPR_MOD,
  AP_TEXPR_POW,
  /* Unary operators */
  AP_TEXPR_NEG,
  AP_TEXPR_CAST,
  AP_TEXPR_SQRT,
} ap_texpr_op_t;

typedef enum ap_texpr_rtype_t {
  AP_RTYPE_REAL,     /* real (no rounding) */
  AP_RTYPE_INT,      /* integer */
  AP_RTYPE_SINGLE,   /* IEEE 754 32-bit single precision, e.g.: C's float */
  AP_RTYPE_DOUBLE,   /* IEEE 754 64-bit double precision, e.g.: C's double */
  /* non-standard 80-bit double extended, e.g.: Intel's long double */
  AP_RTYPE_EXTENDED,
  /* non-standard 128-bit quadruple precision, e.g.: Motorola's long double */
  AP_RTYPE_QUAD,
  AP_RTYPE_SIZE,     /* Not to be used ! */
} ap_texpr_rtype_t;

typedef enum ap_texpr_rdir_t {
  AP_RDIR_NEAREST = MPFR_RNDN, /* Nearest */
  AP_RDIR_ZERO    = MPFR_RNDZ, /* Zero (truncation for integers) */
  AP_RDIR_UP      = MPFR_RNDU, /* + Infinity */
  AP_RDIR_DOWN    = MPFR_RNDD, /* - Infinity */
  AP_RDIR_RND,    /* All possible mode, non deterministically */
  AP_RDIR_SIZE    /* Not to be used ! */
} ap_texpr_rdir_t;


typedef struct ap_texpr0_t { ...; } ap_texpr0_t;

typedef struct ap_texpr1_t {
  ap_texpr0_t* texpr0;
  ap_environment_t* env;
} ap_texpr1_t;

ap_texpr1_t* ap_texpr1_cst(ap_environment_t* env, ap_coeff_t* coeff);
ap_texpr1_t* ap_texpr1_cst_scalar(
    ap_environment_t* env, ap_scalar_t* scalar);
ap_texpr1_t* ap_texpr1_cst_scalar_mpq(
    ap_environment_t* env, mpq_t mpq);
ap_texpr1_t* ap_texpr1_cst_scalar_mpfr(
    ap_environment_t* env, mpfr_t mpfr);
ap_texpr1_t* ap_texpr1_cst_scalar_int(
    ap_environment_t* env, long int num);
ap_texpr1_t* ap_texpr1_cst_scalar_frac(
    ap_environment_t* env, long int num, unsigned long int den);
ap_texpr1_t* ap_texpr1_cst_scalar_double(
    ap_environment_t* env, double num);
ap_texpr1_t* ap_texpr1_cst_interval(
    ap_environment_t* env, ap_interval_t* itv);
ap_texpr1_t* ap_texpr1_cst_interval_scalar(
    ap_environment_t* env, ap_scalar_t* inf, ap_scalar_t* sup);
ap_texpr1_t* ap_texpr1_cst_interval_mpq(
    ap_environment_t* env, mpq_t inf, mpq_t sup);
ap_texpr1_t* ap_texpr1_cst_interval_mpfr(
    ap_environment_t* env, mpfr_t inf, mpfr_t sup);
ap_texpr1_t* ap_texpr1_cst_interval_int(
    ap_environment_t* env, long int inf, long int sup);
ap_texpr1_t* ap_texpr1_cst_interval_frac(
    ap_environment_t* env, long int numinf, unsigned long int deninf,
    long int numsup, unsigned long int densup);
ap_texpr1_t* ap_texpr1_cst_interval_double(
    ap_environment_t* env, double inf, double sup);
ap_texpr1_t* ap_texpr1_cst_interval_top(ap_environment_t* env);
ap_texpr1_t* ap_texpr1_var(ap_environment_t* env, ap_var_t var);
ap_texpr1_t* ap_texpr1_unop(
    ap_texpr_op_t op, ap_texpr1_t* opA,
    ap_texpr_rtype_t type, ap_texpr_rdir_t dir);
ap_texpr1_t* ap_texpr1_binop(
    ap_texpr_op_t op, ap_texpr1_t* opA, ap_texpr1_t* opB,
    ap_texpr_rtype_t type, ap_texpr_rdir_t dir);

ap_texpr1_t* ap_texpr1_copy(ap_texpr1_t* expr);
void ap_texpr1_free(ap_texpr1_t* expr);

// ap_texpr1_t* ap_texpr1_from_linexpr1(ap_linexpr1_t* e);

void ap_texpr1_fprint(FILE* stream, ap_texpr1_t* a);
void ap_texpr1_print(ap_texpr1_t* a);

bool ap_texpr1_has_var(ap_texpr1_t* e, ap_var_t var);
bool ap_texpr1_is_interval_cst(ap_texpr1_t* e);
bool ap_texpr1_is_interval_linear(ap_texpr1_t* e);
bool ap_texpr1_is_interval_polynomial(ap_texpr1_t* e);
bool ap_texpr1_is_interval_polyfrac(ap_texpr1_t* e);
bool ap_texpr1_is_scalar(ap_texpr1_t* e);

ap_texpr1_t* ap_texpr1_substitute(
    ap_texpr1_t* e, ap_var_t var, ap_texpr1_t *dst);
bool ap_texpr1_substitute_with(
    ap_texpr1_t* e, ap_var_t var, ap_texpr1_t *dst);

ap_texpr1_t* ap_texpr1_extend_environment(
    ap_texpr1_t* expr, ap_environment_t* nenv);
bool ap_texpr1_extend_environment_with(
    ap_texpr1_t* expr, ap_environment_t* nenv);

bool ap_texpr1_equal(ap_texpr1_t* a1, ap_texpr1_t* a2);

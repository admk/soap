typedef struct { ...; } __mpq_struct;
typedef __mpq_struct mpq_t[1];
typedef __mpq_struct *mpq_ptr;

typedef struct { ...; } __mpfr_struct;
typedef __mpfr_struct mpfr_t[1];
typedef __mpfr_struct *mpfr_ptr;

typedef enum {
  MPFR_RNDN=0,  /* round to nearest, with ties to even */
  MPFR_RNDZ,    /* round toward zero */
  MPFR_RNDU,    /* round toward +Inf */
  MPFR_RNDD,    /* round toward -Inf */
  MPFR_RNDA,    /* round away from zero */
  MPFR_RNDF,    /* faithful rounding (not implemented yet) */
  MPFR_RNDNA=-1 /* round to nearest, with ties away from zero (mpfr_round) */
} mp_rnd_t;


typedef enum ap_scalar_discr_t {
  AP_SCALAR_DOUBLE,
  AP_SCALAR_MPQ,
  AP_SCALAR_MPFR,
} ap_scalar_discr_t;

typedef struct ap_scalar_t {
  ap_scalar_discr_t discr;
  union {
    double dbl;
    mpq_ptr mpq; /* +infty coded by 1/0, -infty coded by -1/0 */
    mpfr_ptr mpfr;
  } val;
} ap_scalar_t;

ap_scalar_t* ap_scalar_alloc(void);
void ap_scalar_free(ap_scalar_t* scalar);
void ap_scalar_print(ap_scalar_t* a);
void ap_scalar_swap(ap_scalar_t* a, ap_scalar_t* b);

void ap_scalar_set(ap_scalar_t* scalar, ap_scalar_t* scalar2);
void ap_scalar_set_int(ap_scalar_t* scalar, long int i);
void ap_scalar_set_mpq(ap_scalar_t* scalar, mpq_t mpq);
void ap_scalar_set_frac(ap_scalar_t* scalar, long int i, unsigned long int j);
void ap_scalar_set_double(ap_scalar_t* scalar, double k);
void ap_scalar_set_mpfr(ap_scalar_t* scalar, mpfr_t mpfr);
void ap_scalar_set_infty(ap_scalar_t* scalar, int sgn);

ap_scalar_t* ap_scalar_alloc_set(ap_scalar_t* scalar2);
ap_scalar_t* ap_scalar_alloc_set_mpq(mpq_t mpq);
ap_scalar_t* ap_scalar_alloc_set_double(double k);
ap_scalar_t* ap_scalar_alloc_set_mpfr(mpfr_t mpfr);

int ap_mpq_set_scalar(mpq_t mpq, ap_scalar_t* scalar, mp_rnd_t round);
int ap_double_set_scalar(double* k, ap_scalar_t* scalar, mp_rnd_t round);

int ap_scalar_infty(ap_scalar_t* scalar);
int ap_scalar_cmp(ap_scalar_t* a, ap_scalar_t* b);
int ap_scalar_cmp_int(ap_scalar_t* a, int b);
bool ap_scalar_equal(ap_scalar_t* a, ap_scalar_t* b);
bool ap_scalar_equal_int(ap_scalar_t* a, int b);
int ap_scalar_sgn(ap_scalar_t* a);

void ap_scalar_neg(ap_scalar_t* a, ap_scalar_t* b);
void ap_scalar_inv(ap_scalar_t* a, ap_scalar_t* b);
long ap_scalar_hash(ap_scalar_t* a);


typedef struct ap_interval_t {
  ap_scalar_t* inf;
  ap_scalar_t* sup;
} ap_interval_t;

ap_interval_t* ap_interval_alloc(void);
void ap_interval_free(ap_interval_t* interval);
void ap_interval_print(ap_interval_t* a);
void ap_interval_swap(ap_interval_t* a, ap_interval_t* b);

void ap_interval_set(ap_interval_t* interval, ap_interval_t* interval2);
void ap_interval_set_scalar(
    ap_interval_t* interval, ap_scalar_t* inf, ap_scalar_t* sup);
void ap_interval_set_mpq(ap_interval_t* interval, mpq_t inf, mpq_t sup);
void ap_interval_set_int(ap_interval_t* interval, long int inf, long int sup);
void ap_interval_set_frac(
    ap_interval_t* interval, long int numinf, unsigned long int deninf,
    long int numsup, unsigned long int densup);
void ap_interval_set_double(ap_interval_t* interval, double inf, double sup);
void ap_interval_set_mpfr(ap_interval_t* interval, mpfr_t inf, mpfr_t sup);
void ap_interval_set_top(ap_interval_t* interval);
void ap_interval_set_bottom(ap_interval_t* interval);

ap_interval_t* ap_interval_alloc_set(ap_interval_t* interval);

bool ap_interval_is_top(ap_interval_t* interval);
bool ap_interval_is_bottom(ap_interval_t* interval);
bool ap_interval_is_leq(ap_interval_t* i1, ap_interval_t* i2);
int ap_interval_cmp(ap_interval_t* i1, ap_interval_t* i2);
bool ap_interval_equal(ap_interval_t* i1, ap_interval_t* i2);
bool ap_interval_equal_int(ap_interval_t* i, int b);

void ap_interval_neg(ap_interval_t* a, ap_interval_t* b);
long ap_interval_hash(ap_interval_t* itv);

ap_interval_t** ap_interval_array_alloc(size_t size);
void ap_interval_array_free(ap_interval_t** array, size_t size);


typedef enum ap_coeff_discr_t {
  AP_COEFF_SCALAR,
  AP_COEFF_INTERVAL
} ap_coeff_discr_t;

typedef struct ap_coeff_t {
  ap_coeff_discr_t discr; /* discriminant for coefficient */
  union {
    ap_scalar_t* scalar;       /* cst (normal linear expression) */
    ap_interval_t* interval;   /* interval (quasi-linear expression) */
  } val;
} ap_coeff_t;


ap_coeff_t* ap_coeff_alloc(ap_coeff_discr_t ap_coeff_discr);
void ap_coeff_free(ap_coeff_t* a);
void ap_coeff_print(ap_coeff_t* a);

void ap_coeff_reduce(ap_coeff_t* coeff);
void ap_coeff_swap(ap_coeff_t* a, ap_coeff_t* b);

void ap_coeff_set(ap_coeff_t* a, ap_coeff_t* b);
void ap_coeff_set_scalar(ap_coeff_t* coeff, ap_scalar_t* scalar);
void ap_coeff_set_scalar_mpq(ap_coeff_t* coeff, mpq_t mpq);
void ap_coeff_set_scalar_int(ap_coeff_t* coeff, long int num);
void ap_coeff_set_scalar_frac(
    ap_coeff_t* coeff, long int num, unsigned long int den);
void ap_coeff_set_scalar_double(ap_coeff_t* coeff, double num);
void ap_coeff_set_scalar_mpfr(ap_coeff_t* coeff, mpfr_t mpfr);
void ap_coeff_set_interval(ap_coeff_t* coeff, ap_interval_t* itv);
void ap_coeff_set_interval_scalar(ap_coeff_t* coeff, ap_scalar_t* inf, ap_scalar_t* sup);
void ap_coeff_set_interval_mpq(ap_coeff_t* coeff, mpq_t inf, mpq_t sup);
void ap_coeff_set_interval_int(ap_coeff_t* coeff, long int inf, long int sup);
void ap_coeff_set_interval_frac(
    ap_coeff_t* coeff,
    long int numinf, unsigned long int deninf,
    long int numsup, unsigned long int densup);
void ap_coeff_set_interval_double(ap_coeff_t* coeff, double inf, double sup);
void ap_coeff_set_interval_top(ap_coeff_t* coeff);
void ap_coeff_set_interval_mpfr(ap_coeff_t* coeff, mpfr_t inf, mpfr_t sup);

ap_coeff_t* ap_coeff_alloc_set(ap_coeff_t* coeff);
ap_coeff_t* ap_coeff_alloc_set_scalar(ap_scalar_t* scalar);
ap_coeff_t* ap_coeff_alloc_set_interval(ap_interval_t* interval);

int ap_coeff_cmp(ap_coeff_t* coeff1, ap_coeff_t* coeff2);
bool ap_coeff_equal(ap_coeff_t* coeff1, ap_coeff_t* coeff2);
bool ap_coeff_zero(ap_coeff_t* coeff);
bool ap_coeff_equal_int(ap_coeff_t* coeff, int i);

void ap_coeff_neg(ap_coeff_t* a, ap_coeff_t* b);
long ap_coeff_hash(ap_coeff_t* coeff);

typedef void* ap_var_t;
typedef unsigned int ap_dim_t;
typedef struct ap_dimperm_t {
  ap_dim_t* dim;    /* Array assumed to be of size size */
  size_t size;
} ap_dimperm_t;

typedef struct ap_environment_t {
  ap_var_t* var_of_dim;
  size_t intdim;
  size_t realdim;
  size_t count;
} ap_environment_t;

typedef struct ap_environment_name_of_dim_t {
  size_t size;
  char* p[];
} ap_environment_name_of_dim_t;

void ap_environment_free2(ap_environment_t* e);
void ap_environment_free(ap_environment_t* e);

ap_environment_t* ap_environment_copy(ap_environment_t* e);

void ap_environment_fdump(FILE* stream, ap_environment_t* env);

ap_environment_name_of_dim_t* ap_environment_name_of_dim_alloc(
    ap_environment_t* e);
void ap_environment_name_of_dim_free(ap_environment_name_of_dim_t*);

ap_environment_t* ap_environment_alloc_empty(void);
ap_environment_t* ap_environment_alloc(
    ap_var_t* name_of_intdim, size_t intdim,
    ap_var_t* name_of_realdim, size_t realdim);
ap_environment_t* ap_environment_add(
    ap_environment_t* env,
    ap_var_t* name_of_intdim, size_t intdim,
    ap_var_t* name_of_realdim, size_t realdim);
ap_environment_t* ap_environment_add_perm(
    ap_environment_t* env,
    ap_var_t* name_of_intdim, size_t intdim,
    ap_var_t* name_of_realdim, size_t realdim,
    ap_dimperm_t* dimpermu);
ap_environment_t* ap_environment_remove(
    ap_environment_t* env, ap_var_t* tvar, size_t size);

bool ap_environment_mem_var(ap_environment_t* env, ap_var_t name);
ap_dim_t ap_environment_dim_of_var(ap_environment_t* env, ap_var_t name);
ap_var_t ap_environment_var_of_dim(ap_environment_t* env, ap_dim_t dim);


bool ap_environment_is_eq(ap_environment_t* env1, ap_environment_t* env2);
bool ap_environment_is_leq(ap_environment_t* env1, ap_environment_t* env2);
int ap_environment_compare(ap_environment_t* env1, ap_environment_t* env2);
  /* Return
    - -2 if the environments are not compatible
      (a variable has a different type in the 2 environments)
    - -1 if env1 is a subset of env2
    - 0 if equality
    - +1 if env1 is a superset of env2
    - +2 otherwise (the lce exists and is a strict superset of both)
  */
int ap_environment_hash(ap_environment_t* env);

ap_environment_t* ap_environment_rename(
    ap_environment_t* env, ap_var_t* tvar1, ap_var_t* tvar2,
    size_t size, ap_dimperm_t* perm);

from tempfile import TemporaryFile

from soap.apron.ffi import encode_str, ffi, library


class ApronEnvironment(object):
    def __init__(self, integer_variables=None, float_variables=None):
        integer_variables = self._to_c_list(integer_variables)
        float_variables = self._to_c_list(float_variables)

        self._environment = library.ap_environment_alloc(
            integer_variables, len(integer_variables),
            float_variables, len(float_variables))

        if not self._environment:
            raise RuntimeError(
                'Environment is NULL. '
                'May be there is a variable name collision.')

    def _to_c_list(self, var_list):
        c_vars = []
        for v in var_list or []:
            c_vars.append(ffi.new('char []', encode_str(v)))
        var_list = ffi.new('ap_var_t []', c_vars)
        # Hack to prevent cffi from garbage collecting c_vars
        self._dummy = c_vars
        return var_list

    def _add_variable(self, var, is_int):
        var = self._to_c_list([var])
        if is_int:
            args = [self._environment, var, len(var), ffi.NULL, 0]
        else:
            args = [self._environment, ffi.NULL, 0, var, len(var)]
        env = library.ap_environment_add(*args)
        if not env:
            raise ValueError('Variable name already exists.')
        self._environment = env

    def add_integer_variable(self, var):
        self._add_variable(var, is_int=True)

    def add_float_variable(self, var):
        self._add_variable(var, is_int=False)

    def remove_variable(self, var):
        var = self._to_c_list([var])
        env = library.ap_environment_remove(self._environment, var, len(var))
        if not env:
            raise ValueError('Variable name does not exist.')
        self._environment = env

    def __repr__(self):
        with TemporaryFile() as out:
            library.ap_environment_fdump(out, self._environment)
            out.seek(0)
            return out.read().decode('utf-8')

    def __eq__(self, other):
        return library.ap_environment_is_eq(
            self._environment, other._environment)

    def __hash__(self):
        return library.ap_environment_hash(self._environment)

    def __del__(self):
        if not self._environment:
            raise RuntimeError('Environment is NULL. Cannot delete.')
        library.ap_environment_free(self._environment)

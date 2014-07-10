import sys

import cffi


dir_name = 'soap/apron/header/'

ffi = cffi.FFI()

decls = ['numeric.h', 'environment.h', 'manager.h', 'tree.h']
for decl in decls:
    with open(dir_name + decl) as decl_file:
        ffi.cdef(decl_file.read())
oct_h = '\nap_manager_t* oct_manager_alloc(void);\n'
ffi.cdef(oct_h)

includes = ['ap_global0.h', 'ap_global1.h', 'oct.h']
includes = '\n'.join('#include <{}>'.format(i) for i in includes)

library = ffi.verify(includes, libraries=['apron', 'octD'])
stdout = ffi.cast('FILE *', sys.stdout)


def decode_str(s):
    return ffi.string(s).decode('utf-8')


def encode_str(s):
    return s.encode('utf-8')

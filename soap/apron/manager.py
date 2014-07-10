from soap.apron.ffi import library, decode_str


class _ApronManager(object):
    def __del__(self):
        library.ap_manager_free(self._manager)


class OctagonManager(_ApronManager):
    def __init__(self):
        self._manager = library.oct_manager_alloc()

    @property
    def library(self):
        return decode_str(library.ap_manager_get_library(self._manager))

    @property
    def version(self):
        return decode_str(library.ap_manager_get_version(self._manager))

    def __repr__(self):
        return 'OctagonManager(library={!r}, version={!r})'.format(
            self.library, self.version)

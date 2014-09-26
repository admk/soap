import signal
import multiprocessing
from multiprocessing.pool import Pool

from soap import logger


class NoDaemonProcess(multiprocessing.Process):
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)


class _NoDaemonPool(Pool):
    Process = NoDaemonProcess


class _Pool(object):
    def __init__(self, cpu=None):
        super().__init__()
        self._cpu = cpu
        self._pool = None
        self.map = self._func_wrapper('imap')
        self.map_unordered = self._func_wrapper('imap_unordered')

    @property
    def pool(self):
        if not self._pool:
            cpu = self._cpu or multiprocessing.cpu_count()
            self._pool = _NoDaemonPool(cpu, initializer=self._initializer)
        return self._pool

    @staticmethod
    def _initializer():
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _func_wrapper(self, func):
        def wrapped(*args, **kwargs):
            try:
                return list(getattr(self.pool, func)(*args, **kwargs))
            except KeyboardInterrupt:
                logger.warning(
                    'KeyboardInterrupt caught, terminating workers.')
                self.pool.terminate()
                self.pool.join()
                self._pool = None
                raise KeyboardInterrupt()
        return wrapped

    def invalidate_cache(self):
        from soap.common.cache import process_invalidate_cache
        if self._pool:
            self._pool.apply(process_invalidate_cache)


pool = _Pool()

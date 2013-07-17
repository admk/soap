from multiprocessing import Process, Pipe, cpu_count


def _spawn(f):
    def decorated(pipe, *args):
        try:
            pipe.send(f(*args))
        except:
            import traceback
            traceback.print_exc()
            raise
        finally:
            pipe.close()
    return decorated


def map(func, args):
    def chunks(l, size):
        l = list(l)
        for i in range(0, len(l), size):
            yield l[i:i+size]
    for args_chunk in chunks(args, cpu_count()):
        pipes = []
        processes = []
        for a in args_chunk:
            opipe, ipipe = Pipe()
            try:
                a = list(a)
            except TypeError:
                a = [a]
            a = [ipipe] + a
            pipes.append(opipe)
            processes.append(Process(target=_spawn(func), args=a))
        for p in processes:
            p.start()
        for p in processes:
            p.join()
        for p in pipes:
            yield p.recv()

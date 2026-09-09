"""OS advisory lock, automatically released if the writer process exits."""
from contextlib import contextmanager
from .store import DATA

@contextmanager
def pipeline_lock():
    DATA.mkdir(parents=True,exist_ok=True)
    with (DATA/'pipeline.lock').open('a+b') as handle:
        handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
        try:
            import os
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError) as e:
            raise RuntimeError('Another data refresh or training process is running.') from e
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)

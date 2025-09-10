import os


def tail(filepath, lines=500):
    """Return last `lines` from a file."""
    with open(filepath, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        block_size = 1024
        data = b""
        while file_size > 0 and lines > 0:
            read_size = min(block_size, file_size)
            file_size -= read_size
            f.seek(file_size)
            data = f.read(read_size) + data
            lines -= data.count(b"\n")
        return data.decode(errors="ignore").splitlines()[-500:]

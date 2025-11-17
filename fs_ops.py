# fs_ops.py

from disk import DREAD, DWRITE, USER_DATA_SIZE, allocate_block, free_block
from fs_structs import DirBlock, DataBlock, DirEntry, OpenFile

open_stack = []

def find_dir_and_name(path):
    """
    Given a path, return the parent directory block and the name of the final component.
    For example, for path "/sub/docs/file1", return the DirBlock for "/sub/docs" and "file1".
    """
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return DREAD(0), None  # root
    current_dir = DREAD(0)
    for part in parts[:-1]:
        found = False
        for entry in current_dir.entries:
            if entry.name == part and entry.ftype == 'D':
                current_dir = DREAD(entry.start_block)
                found = True
                break
        if not found:
            print(f"Error: Directory '{part}' not found in path '{path}'.")
            return None, None
    return current_dir, parts[-1]

def create(ftype, path):
    """
    Create a file or directory at the specified path.
    ftype: 'F' for file, 'D' for directory
    """
    parent_dir, name = find_dir_and_name(path)
    if parent_dir is None or name is None:
        return
    # If exists, delete it
    for e in parent_dir.entries:
        if e.name == name:
            free_block(e.start_block)
            parent_dir.entries.remove(e)
    new_block = allocate_block()
    if new_block == -1:
        print("Error: No free blocks.")
        return
    entry = DirEntry(name, ftype, new_block, 0)
    parent_dir.entries.append(entry)
    if ftype == 'D':
        DWRITE(new_block, DirBlock())
        print(f"Directory '{path}' created.")
    else:
        DWRITE(new_block, DataBlock())
        print(f"File '{path}' created.")
    # Save root dir
    DWRITE(0, DREAD(0))

def open_file(mode, path):
    """
    Open a file at the specified path in the given mode.
    mode: 'I' for read, 'O' for write, 'U' for update
    I is input mode (read and seek only)
    O is output mode (write only, truncates file)
    U is update mode (read and write and seek)
    """
    mode = mode.strip().upper()
    if mode == "I": mode = 'r'
    elif mode == "O": mode = 'w'
    elif mode == "U": mode = 'u'
    else:
        print("Error: Invalid mode.")
        return None
    parent_dir, name = find_dir_and_name(path)
    if parent_dir is None:
        return None
    for entry in parent_dir.entries:
        if entry.name == name and entry.ftype == 'F':
            for i, f in enumerate(open_stack):
                if f is None:
                    open_stack[i] = OpenFile(path, entry, mode)
                    print(f"File '{path}' opened with FD {i} in mode '{mode}'.")
                    return i
            fd = len(open_stack)
            open_stack.append(OpenFile(path, entry, mode))
            print(f"File '{path}' opened with FD {fd} in mode '{mode}'.")
            return fd
    print(f"Error: File '{path}' not found.")
    return None

def close_file(fd):
    """
    This cmd cause the last opened or created file to be closed. No file named is given
    as argument, only the file descriptor (FD) is used.
    fd: file descriptor to close

  """
    
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD or file already closed.")
        return
    closed = open_stack[fd]
    open_stack[fd] = None
    print(f"File '{closed.path}' with FD {fd} closed.")

def delete(path):
    """"
    Delete a file or directory at the specified path.
    How it work:
    if the file or directory exists at the specified path, it is removed from its parent directory's entries,
    and its allocated blocks are freed.
    """
    parent_dir, name = find_dir_and_name(path)
    if parent_dir is None:
        return
    for i, entry in enumerate(parent_dir.entries):
        if entry.name == name:
            free_block(entry.start_block)
            del parent_dir.entries[i]
            DWRITE(0, DREAD(0))
            print(f"Deleted '{path}'.")
            return
    print(f"Error: '{path}' not found.")

def write_cmd(fd_or_size, data_str=None):
    # Case 1: called as WRITE <n> 'data' without FD
    if isinstance(fd_or_size, str) and data_str is None:
        tokens = fd_or_size.strip().split(maxsplit=1)
        if len(tokens) < 2:
            print("Error: Invalid WRITE command.")
            return
        n = int(tokens[0])
        data = tokens[1].strip("'\"")
        data_bytes = data.encode()
        if len(data_bytes) < n:
            data_bytes += b' ' * (n - len(data_bytes))

        # Auto-create default file if none is open
        if not open_stack or all(f is None for f in open_stack):
            create('F', '/auto_file')
            fd = open_file('O', '/auto_file')
        else:
            fd = next((i for i, f in enumerate(open_stack) if f is not None), None)
            if fd is None:
                fd = open_file('O', '/auto_file')

        file_object = open_stack[fd]
        data_block = DREAD(file_object.entry.start_block)
        data_block.data[:n] = data_bytes[:USER_DATA_SIZE]
        file_object.entry.size = min(n, USER_DATA_SIZE)
        DWRITE(file_object.entry.start_block, data_block)
        print(f"Wrote {file_object.entry.size} bytes to FD {fd}.")
        return

    # Case 2: normal WRITE <fd> 'data'
    fd = fd_or_size
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]
    if file_object.mode not in ('w', 'u'):
        print("Error: File not open in write mode.")
        return
    # write at current offset, respect USER_DATA_SIZE
    data_bytes = data_str.encode()
    start = file_object.offset
    # cap write to available user data area
    max_write = max(0, USER_DATA_SIZE - start)
    write_bytes = data_bytes[:max_write]

    data_block = DREAD(file_object.entry.start_block)
    data_block.data[start:start+len(write_bytes)] = write_bytes
    file_object.offset = start + len(write_bytes)
    file_object.entry.size = max(file_object.entry.size, file_object.offset)
    DWRITE(file_object.entry.start_block, data_block)
    print(f"Wrote {len(write_bytes)} bytes to FD {fd}.")

def read_cmd(fd, num_bytes):
    """
    This cmd reads data from the file associated with the given file descriptor (FD).
    This cmd only be used when the file is opened in input (I) or update (U) mode and corresponding to close cmd.
    """
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]
    if file_object.mode not in ('r', 'u'):
        print("Error: File not open in read mode.")
        return
    data_block = DREAD(file_object.entry.start_block)
    start = getattr(file_object, 'offset', 0)
    end = min(start + num_bytes, file_object.entry.size)
    if start >= end:
        data_to_read = b''
    else:
        data_to_read = data_block.data[start:end]
    try:
        decoded = data_to_read.decode()
    except Exception:
        decoded = ''
    print(f"Read {len(data_to_read)} bytes from FD {fd}: '{decoded}'")
    # advance offset
    file_object.offset = end

def seek(fd, base, offset=None):
    """
    seek(fd, offset)  -> short form (SEEK_SET)
    seek(fd, base, offset) -> long form where base is 0=SEEK_SET,1=SEEK_CUR,2=SEEK_END
    """
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]

    # short form: seek(fd, offset)
    if offset is None:
        new_offset = base
    else:
        b = base
        if b == 0:
            new_offset = offset
        elif b == 1:
            new_offset = file_object.offset + offset
        elif b == 2:
            new_offset = file_object.entry.size + offset
        else:
            print("Error: Invalid base for SEEK.")
            return

    # bounds
    if new_offset < 0 or new_offset > USER_DATA_SIZE:
        print("Error: Offset out of bounds.")
        return

    if new_offset > file_object.entry.size and file_object.mode not in ('w', 'u'):
        print("Error: Cannot seek beyond EOF in read-only mode.")
        return

    if new_offset > file_object.entry.size:
        file_object.entry.size = new_offset

    file_object.offset = new_offset
    print(f"Set offset of FD {fd} to {new_offset}.")

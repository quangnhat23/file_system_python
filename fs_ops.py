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

    Behavior and logic:
    - Locate the parent directory using `find_dir_and_name`.
    - If an entry with the requested name already exists, free its block and remove it
      (this implements a simple replace-on-create semantics).
    - Allocate a free block from the simulated disk (`allocate_block`).
    - Create a `DirEntry` for the new file/directory and append it to the parent
      directory's entries.
    - For directories, write an empty `DirBlock` into the allocated block.
    - For files, write an empty `DataBlock` into the allocated block and automatically
      open the file in Output ('w') mode.

    Notes:
    - Errors such as missing parent directories or lack of free blocks are reported
      via printed error messages and the operation is aborted.
    - When a file is created, it is automatically opened and the file descriptor
      is printed.

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
        # Automatically open file in Output mode
        fd = open_file('O', path)
        if fd is not None:
            print(f"File descriptor: {fd}")
    # Save root dir
    DWRITE(0, DREAD(0))

def open_file(mode, path):
    """
    Open a file at the specified path in the given mode.

    Behavior and logic:
    - Normalize the textual mode into an internal mode character ('I' -> 'r',
      'O' -> 'w', 'U' -> 'u').
    - Locate the file's `DirEntry` by walking the parent directory entries.
    - If found, allocate or reuse a slot in `open_stack` and create an `OpenFile`
      object that tracks the path, entry, mode and current offset.
    - Returns the file descriptor (index in `open_stack`) on success, otherwise
      prints an error and returns `None`.
    """
    mode = mode.strip().upper()
    if mode == "I": # Input mode
        mode = 'r'# read-only
    elif mode == "O":# Output mode
        mode = 'w'# write-only
    elif mode == "U":# update mode
        mode = 'u'# read-write
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

def close_file(fd=None):
        """
        Close an open file.

        If `fd` is provided, close that file descriptor. If `fd` is `None`, close
        the most recently opened (highest-numbered) open file.

        Behavior and logic:
        - If `fd` is None, scan `open_stack` from the end to find the last
            non-None entry and use that FD.
        - Validate the FD, set the slot to `None` to mark it closed, and print a
            confirmation message.
        - If no open files exist, print an error message.
        """
        # If no FD given, pick the most recently opened FD
        if fd is None:
                fd = None
                for i in range(len(open_stack) - 1, -1, -1): # scan backwards
                        if open_stack[i] is not None:
                                fd = i
                                break
                if fd is None:
                        print("Error: No open files to close.")
                        return

        if fd >= len(open_stack) or open_stack[fd] is None:
                print("Error: Invalid FD or file already closed.")
                return
        closed = open_stack[fd]
        open_stack[fd] = None
        print(f"File '{closed.path}' with FD {fd} closed.")

def delete(path):
    """
    Delete a file or directory at the specified path.

    Behavior and logic:
    - Locate the parent directory and target entry via `find_dir_and_name`.
    - If found, free the block associated with the entry (`free_block`) and remove
      the entry from the parent's entries list.
    - Update the root directory on-disk representation (in this simulation that
      means writing the in-memory root DirBlock back to block 0).
    - If the entry is not found, an error message is printed.

    Notes:
    - This simple implementation does not recursively free blocks for multi-block
      files or directories. It assumes a single-block file or directory.
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
    Read up to `num_bytes` starting at the current file offset for the FD.

    Behavior and logic:
    - Validate the FD and that the file is open for reading (`r` or `u`).
    - Compute the start position from the `OpenFile.offset` and limit the read
      to the file's logical size (`entry.size`) and requested `num_bytes`.
    - Extract the bytes from the DataBlock and attempt to decode to text for
      printing. Non-decodable bytes will fall back to an empty string for display.
    - Advance the file offset by the number of bytes actually read.

    Notes:
    - If the offset is at or beyond EOF, an empty byte string is returned and
      the offset remains unchanged (or set to EOF).
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
    Set the file offset for an open file descriptor.

    Supported call forms:
    - `seek(fd, offset)` — short form: set offset absolutely (SEEK_SET)
    - `seek(fd, base, offset)` — long form where `base` is:
      0 = SEEK_SET (set offset to `offset`)
      1 = SEEK_CUR (set offset to current + `offset`)
      2 = SEEK_END (set offset to file_size + `offset`)

    Behavior and logic:
    - Validate the FD.
    - Resolve the requested new offset based on the form and base value.
    - Enforce bounds: offset cannot be negative and cannot exceed the
      per-block user-data capacity (`USER_DATA_SIZE`).
    - Seeking beyond EOF is permitted only when the file is open for write
      (`w`) or update (`u`); in that case, the file's logical size (`entry.size`)
      is extended to the new offset.
    - For read-only mode, seeking beyond EOF is rejected.
    - Update the OpenFile.offset to the new value and print confirmation.
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

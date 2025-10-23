# fs_ops.py

from disk import DREAD, DWRITE, allocate_block, free_block
from fs_structs import DirBlock, DataBlock, DirEntry, OpenFile

open_stack = []

def find_dir_and_name(path):
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
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD or file already closed.")
        return
    closed = open_stack[fd]
    open_stack[fd] = None
    print(f"File '{closed.path}' with FD {fd} closed.")

def delete(path):
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

def write_cmd(fd, data_str):
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]
    if file_object.mode not in ('w', 'u'):
        print("Error: File not open in write mode.")
        return
    data_block = DREAD(file_object.entry.start_block)
    data_bytes = data_str.encode()[:len(data_block.data)]
    file_object.entry.size = len(data_bytes)
    data_block.data[:len(data_bytes)] = data_bytes
    DWRITE(file_object.entry.start_block, data_block)
    print(f"Wrote {len(data_bytes)} bytes to FD {fd}.")

def read_cmd(fd, num_bytes):
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]
    if file_object.mode not in ('r', 'u'):
        print("Error: File not open in read mode.")
        return
    data_block = DREAD(file_object.entry.start_block)
    data_to_read = data_block.data[:min(num_bytes, file_object.entry.size)]
    print(f"Read {len(data_to_read)} bytes from FD {fd}: '{data_to_read.decode()}'")


"""
# -----------------------------
# Basic Setup
# -----------------------------
CREATE D /sub             # Create directory "sub"
CREATE D /sub/docs        # Create directory "docs" inside "sub"
CREATE F /sub/docs/file1  # Create a new file "file1" under /sub/docs

# -----------------------------
# File Operations
# -----------------------------
OPEN O /sub/docs/file1    # Open file1 for writing (Output mode)
WRITE 0 'Hello World'     # Write data into file descriptor 0
CLOSE 0                   # Close the file

OPEN I /sub/docs/file1    # Reopen file1 for reading (Input mode)
READ 0 11                 # Read 11 bytes from file descriptor 0
CLOSE 0                   # Close the file

# -----------------------------
# Update Mode (Read + Write)
# -----------------------------
OPEN U /sub/docs/file1    # Open for update (read/write)
SEEK 0 5                  # Move pointer to offset 5
WRITE 0 '!!!'             # Overwrite from offset 5
READ 0 20                 # Read file contents after modification
CLOSE 0                   # Close the file

# -----------------------------
# Directory & Deletion
# -----------------------------
DELETE /sub/docs/file1    # Delete a file
DELETE /sub/docs          # Delete directory after its files are deleted
DELETE /sub               # Delete parent directory

# -----------------------------
# System Exit
# -----------------------------
exit                      # Exit the program and show final disk state

"""

# -----------------------------
# 1. Constants & Globals
# -----------------------------
BLOCK_SIZE = 512
USER_DATA_SIZE = 504
DISK_BLOCKS = 100

disk = [None] * DISK_BLOCKS
open_stack = []  # list of OpenFile objects


# -----------------------------
# 2. Data Structures
# -----------------------------
class DirEntry:
    def __init__(self, name, ftype, start_block, size=0):
        self.name = name
        self.ftype = ftype  # 'F' for file, 'D' for directory
        self.start_block = start_block
        self.size = size


class DirBlock:
    def __init__(self):
        self.entries = []


class DataBlock:
    def __init__(self):
        self.data = bytearray(USER_DATA_SIZE)
        self.next_block = -1


class OpenFile:
    def __init__(self, path, entry, mode):
        self.entry = entry
        self.mode = mode  # 'r', 'w', 'u'
        self.offset = 0
        self.path = path


# -----------------------------
# 3. Disk simulation
# -----------------------------
def DREAD(block_num):
    return disk[block_num]


def DWRITE(block_num, data):
    disk[block_num] = data


def init_disk():
    root_dir = DirBlock()
    DWRITE(0, root_dir)
    for i in range(1, DISK_BLOCKS):
        disk[i] = None
    print("Disk initialized with 100 blocks (block 0 = root directory).")


def allocate_block():
    for i in range(1, DISK_BLOCKS):
        if disk[i] is None:
            return i
    return -1


def free_block(block_num):
    if 0 <= block_num < DISK_BLOCKS:
        disk[block_num] = None


# -----------------------------
# 4. Helper: Navigate directories
# -----------------------------
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


# -----------------------------
# 5. File System Operations
# -----------------------------
def create(ftype, path):
    parent_dir, name = find_dir_and_name(path)
    if parent_dir is None or name is None:
        return

    # Delete existing file/directory
    for e in parent_dir.entries:
        if e.name == name:
            free_block(e.start_block)
            parent_dir.entries.remove(e)
            break

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
    mode = mode.upper()
    if mode == 'I':
        mode = 'r'
    elif mode == 'O':
        mode = 'w'
    elif mode == 'U':
        mode = 'u'
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
        print("Error: Invalid FD or already closed.")
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

    data_bytes = data_str.encode()
    data_block = DREAD(file_object.entry.start_block)
    # write at offset
    end_pos = min(file_object.offset + len(data_bytes), USER_DATA_SIZE)
    data_block.data[file_object.offset:end_pos] = data_bytes[:end_pos - file_object.offset]
    file_object.offset = end_pos
    file_object.entry.size = max(file_object.entry.size, file_object.offset)
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
    end_pos = min(file_object.offset + num_bytes, file_object.entry.size)
    data_to_read = data_block.data[file_object.offset:end_pos]
    print(f"Read {len(data_to_read)} bytes from FD {fd}: '{data_to_read.decode()}'")
    file_object.offset = end_pos


def seek_cmd(fd, base, offset):
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]

    # Standard semantics: 0=SEEK_SET, 1=SEEK_CUR, 2=SEEK_END
    if base == 0:
        new_offset = offset
    elif base == 1:
        new_offset = file_object.offset + offset
    elif base == 2:
        new_offset = file_object.entry.size + offset
    else:
        print("Error: Invalid base for SEEK.")
        return

    # bounds: cannot be negative and cannot exceed block data capacity
    if new_offset < 0 or new_offset > USER_DATA_SIZE:
        print("Error: Offset out of bounds.")
        return

    # If seeking beyond current file size, only allow for write/update modes
    if new_offset > file_object.entry.size and file_object.mode not in ('w', 'u'):
        print("Error: Cannot seek beyond EOF in read-only mode.")
        return

    # If writable and seek beyond size, extend logical size
    if new_offset > file_object.entry.size:
        file_object.entry.size = new_offset

    file_object.offset = new_offset
    print(f"Set offset of FD {fd} to {new_offset}.")


# -----------------------------
# 6. Command Processor
# -----------------------------
def process_line(line):
    tokens = line.strip().split()
    if not tokens:
        return
    cmd = tokens[0].upper()

    if cmd == "CREATE" and len(tokens) == 3:
        create(tokens[1].upper(), tokens[2])
    elif cmd == "OPEN" and len(tokens) == 3:
        fd = open_file(tokens[1], tokens[2])
        if fd is not None:
            print(f"File descriptor: {fd}")
    elif cmd == "CLOSE" and len(tokens) == 2:
        close_file(int(tokens[1]))
    elif cmd == "DELETE" and len(tokens) == 2:
        delete(tokens[1])
    elif cmd == "WRITE" and len(tokens) >= 3:
        fd = int(tokens[1])
        data_str = " ".join(tokens[2:]).strip("'\"")
        write_cmd(fd, data_str)
    elif cmd == "READ" and len(tokens) == 3:
        fd = int(tokens[1])
        num_bytes = int(tokens[2])
        read_cmd(fd, num_bytes)
    elif cmd == "SEEK" and len(tokens) == 3:
        # allow short form: SEEK <fd> <offset> (SEEK_SET)
        fd = int(tokens[1])
        offset = int(tokens[2])
        seek_cmd(fd, 0, offset)
    elif cmd == "SEEK" and len(tokens) == 4:
        fd = int(tokens[1])
        base = int(tokens[2])
        offset = int(tokens[3])
        seek_cmd(fd, base, offset)
    else:
        print(f"Error: Unknown or malformed command '{line.strip()}'")


# -----------------------------
# 7. Final Report
# -----------------------------
def print_dir_recursive(dir_block, prefix=""):
    for e in dir_block.entries:
        print(f"{prefix}{e.ftype} {e.name} (start={e.start_block}, size={e.size})")
        if e.ftype == 'D':
            subdir = DREAD(e.start_block)
            print_dir_recursive(subdir, prefix + "  ")


def final_report():
    print("\n=== FINAL DISK STATE ===")
    root_dir = DREAD(0)
    print_dir_recursive(root_dir)
    print("\nOpen Files:")
    for i, of in enumerate(open_stack):
        if of is not None:
            print(f"FD {i}: {of.path}, mode={of.mode}, offset={of.offset}")
        else:
            print(f"FD {i}: Closed")


# -----------------------------
# 8. Main
# -----------------------------
def main():
    init_disk()
    while True:
        try:
            line = input("Command> ")
            if line.strip().lower() == "exit":
                break
            process_line(line)
        except EOFError:
            break
    final_report()


if __name__ == "__main__":
    main()



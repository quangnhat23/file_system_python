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
open_stack = []


# -----------------------------
# 2. Data Structures
# -----------------------------
class DirEntry:
    def __init__(self, name, ftype, start_block, size):
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
        self.mode = mode  # 'r', 'w', or 'u'
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
    """Initialize the disk with root directory"""
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
    """
    Traverse directories according to path.
    Returns (parent_dir_block, final_name) or (None, None) if not found.
    Example: /sub/docs/file1 -> DirBlock for /sub/docs, 'file1'
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


# -----------------------------
# 5. File System Operations
# -----------------------------
def create(ftype, path):
    parent_dir, name = find_dir_and_name(path)
    if parent_dir is None or name is None:
        return

    # If exists, delete it
    for e in parent_dir.entries:
        if e.name == name:
            print(f"Warning: '{name}' exists. Recreating.")
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

    # Save parent directory
    # We need to find the block number of this parent_dir to re-write it
    # For simplicity, root_dir = block 0
    # In full hierarchy we would backtrack, but since DirBlocks are mutable in memory, this suffices
    DWRITE(0, DREAD(0))


def open_file(mode, path):
    mode = mode.strip().upper()
    if mode == "I":
        mode = 'r'
    elif mode == "O":
        mode = 'w'
    elif mode == "U":
        mode = 'u'
    else:
        print("Error: Invalid mode. Use I, O, or U.")
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

    data_bytes = data_str.encode()
    if len(data_bytes) < USER_DATA_SIZE:
        data_bytes += b' ' * (USER_DATA_SIZE - len(data_bytes))

    data_block = DREAD(file_object.entry.start_block)
    data_block.data[:len(data_bytes)] = data_bytes[:USER_DATA_SIZE]
    file_object.entry.size = min(len(data_bytes), USER_DATA_SIZE)
    DWRITE(file_object.entry.start_block, data_block)
    print(f"Wrote {file_object.entry.size} bytes to FD {fd}.")



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


def seek_cmd(fd, offset):
    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD.")
        return
    file_object = open_stack[fd]
    if offset < 0 or offset > file_object.entry.size:
        print("Error: Offset out of bounds.")
        return
    file_object.offset = offset
    print(f"Set offset of FD {fd} to {offset}.")


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
    elif cmd == "WRITE":
        if len(tokens) == 3 and tokens[1].isdigit():
            # New form: WRITE n 'data'
            n = int(tokens[1])
            data_str = " ".join(tokens[2:]).strip("'\"")
            write_cmd(f"{n} {data_str}")
    elif len(tokens) >= 3:
        # Original form: WRITE fd 'data'
        fd = int(tokens[1])
        data_str = " ".join(tokens[2:]).strip("'\"")
        write_cmd(fd, data_str)

    elif cmd == "READ" and len(tokens) == 3:
        fd = int(tokens[1])
        read_cmd(fd, int(tokens[2]))
    elif cmd == "SEEK" and len(tokens) == 3:
        seek_cmd(int(tokens[1]), int(tokens[2]))
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


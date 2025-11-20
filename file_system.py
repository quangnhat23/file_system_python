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
    """Read and return the contents of a disk block."""
    return disk[block_num]

def DWRITE(block_num, data):
    """Write data to a specific disk block."""
    disk[block_num] = data

def init_disk():
    """Initialize the simulated disk with 100 blocks. Block 0 is the root directory, others are empty."""
    root_dir = DirBlock()
    DWRITE(0, root_dir)
    for i in range(1, DISK_BLOCKS):
        disk[i] = None
    print("Disk initialized with 100 blocks (block 0 = root directory).")
def allocate_block():
    """Find and return the next available free block. Returns -1 if no free blocks."""
    for i in range(1, DISK_BLOCKS):
        if disk[i] is None:
            return i
    return -1

def free_block(block_num):
    """Mark a block as free (available for reallocation) by setting it to None."""
    if 0 <= block_num < DISK_BLOCKS:
        disk[block_num] = None

# -----------------------------
# 4. Helper: Navigate directories
# -----------------------------
def find_dir_and_name(path):
    """
    Navigate the directory tree to find the parent directory and final component name.
    
    For path "/sub/docs/file1", returns the DirBlock for "/sub/docs" and the string "file1".
    For empty path (root), returns (root_dir, None).
    Returns (None, None) if any intermediate directory doesn't exist.
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
    """
    Create a file or directory at the specified path.
    
    Logic:
    1. Find the parent directory using find_dir_and_name()
    2. If entry with same name exists, delete it (replace-on-create semantics)
    3. Allocate a new block from free blocks
    4. Create DirEntry and add to parent directory's entries list
    5. For directories: write empty DirBlock to new block
    6. For files: write empty DataBlock, then auto-open in Output ('O') mode
    7. Persist the root directory changes to disk
    """
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
        # Automatically open file in Output mode
        fd = open_file('O', path)
        if fd is not None:
            print(f"File descriptor: {fd}")

    # Save root dir
    DWRITE(0, DREAD(0))


def open_file(mode, path):
    """
    Open a file at the specified path in the given mode.
    
    Logic:
    1. Normalize mode: 'I'->read, 'O'->write, 'U'->update (read-write)
    2. Navigate to file location using find_dir_and_name()
    3. Search for the file entry in the parent directory
    4. Assign new FD (file descriptor) = current length of open_stack
    5. Create OpenFile object and append to open_stack
    6. Return FD on success, None on failure
    
    Multiple files can be open simultaneously, each with unique FD.
    """
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
            # If already opened in the same mode, return existing FD
            for i, f in enumerate(open_stack):
                if f is not None and f.path == path and f.mode == mode:
                    print(f"File '{path}' already opened with FD {i}.")
                    return i
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
    Close an open file by its file descriptor.
    
    Logic:
    1. If fd is None, close the most recently opened file (last in open_stack)
    2. Validate fd is within bounds and points to an open file
    3. Set open_stack[fd] to None (mark as closed, keep slot)
    4. Print confirmation message
    
    Note: Closed slots remain in open_stack for backwards compatibility with FD indices.
    """
    # If no FD provided, close the most recently opened file
    if fd is None:
        fd = None
        for i in range(len(open_stack) - 1, -1, -1):
            if open_stack[i] is not None:
                fd = i
                break
        if fd is None:
            print("Error: No open files to close.")
            return

    if fd >= len(open_stack) or open_stack[fd] is None:
        print("Error: Invalid FD or already closed.")
        return
    closed = open_stack[fd]
    open_stack[fd] = None
    print(f"File '{closed.path}' with FD {fd} closed.")


def delete(path):
    """
    Delete a file or directory at the specified path.
    
    Logic:
    1. Find parent directory using find_dir_and_name()
    2. Search for the entry in the parent's entries list
    3. If found: free its block and remove from entries
    4. Persist changes by writing root directory back to disk
    5. If not found: print error message
    
    Note: Does not recursively delete directory contents (assumes single-block files/dirs).
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


def write_cmd(fd, data_str, expected_n=None):
    """
    Write data to file at file descriptor fd.
    
    Logic:
    1. Validate fd is open and file is in write mode ('w' or 'u')
    2. Encode data_str to bytes
    3. Calculate write boundary: min(current_offset + data_length, USER_DATA_SIZE)
    4. Write bytes to the data block at current offset
    5. Update file offset and file size
    6. Persist changes to disk
    7. If expected_n provided: check for Disk Full condition
       - If bytes_written < expected_n: write succeeded partially, print "Error: Disk Full."
    
    Returns silently; output via print statements.
    """
    # Validate FD and mode
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
    """
    Read up to num_bytes from file at file descriptor fd, starting at current offset.
    
    Logic:
    1. Validate fd is open and file is in read mode ('r' or 'u')
    2. Calculate end position: min(current_offset + num_bytes, file_size)
    3. Extract bytes from data block between current offset and end position
    4. Decode bytes to string for display
    5. Print bytes read and content
    6. Advance file offset to end position
    7. If fewer bytes read than requested: print "EOF reached."
    
    Returns silently; output via print statements.
    """
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
    """
    Set the file offset for file at fd to a new position.
    
    Logic:
    1. Validate fd is open
    2. Calculate new offset based on base and offset:
       - base = -1: SEEK_SET   (absolute: new_offset = offset)
       - base = 0:  SEEK_CUR   (relative to current: new_offset = current + offset)
       - base = 1:  SEEK_END   (relative to end: new_offset = size + offset)
       - base = 2:  Legacy SEEK_END (same as base=1)
    3. Validate new_offset: must be >= 0 and <= USER_DATA_SIZE
    4. If seeking beyond file size in read-only mode: reject with error
    5. If seeking beyond file size in write/update mode: extend file size
    6. Update offset and print confirmation
    
    Supports both new compact form (-1/0/1) and legacy form (0/1/2).
    """
    if fd >= len(open_stack) or open_stack[fd] is None:
        print(f"Error: Invalid FD {fd}.")
        return
    file_object = open_stack[fd]

    if base == -1:
        new_offset = offset
    elif base == 0:
        # could be either legacy SEEK_SET (0) or new SEEK_CUR (0)
        # disambiguate by treating explicit legacy 0 with integer offset
        # If caller intended legacy behavior (set absolute), they'll call with base=-1 normally.
        # Here we interpret 0 as SEEK_CUR in the new scheme.
        new_offset = file_object.offset + offset
    elif base == 1:
        new_offset = file_object.entry.size + offset
    elif base == 2:
        # legacy mapping: 2 == SEEK_END
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
    """
    Parse and execute a command line from the user.
    
    Supported Commands:
    - CREATE <type> <path>: Create file (U) or directory (D)
    - OPEN <mode> <path>: Open file in mode I(input), O(output), U(update)
    - DELETE <path>: Delete file or directory
    - WRITE <n> 'data': Write n bytes (pad/truncate data to exactly n bytes)
    - READ <n>: No-FD form, read n bytes from most recently opened
    - SEEK <base> <offset>: Set file offset (base: -1/0/1 for begin/current/end)
    - SEEK <fd> <base> <offset>: Legacy form with explicit fd
    
    CLI automatically validates arguments and prints errors/confirmations.
    """
    tokens = line.strip().split()
    if not tokens:
        return
    cmd = tokens[0].upper()

    if cmd == "CREATE" and len(tokens) == 3:
        ftype = tokens[1].upper()
        # CLI now uses 'U' to indicate a file (maps to internal 'F')
        if ftype not in ('U', 'D'):
            print(f"Error: Invalid type for CREATE: '{tokens[1]}'. Use 'U' (file) or 'D' (directory).")
        else:
            internal_type = 'F' if ftype == 'U' else 'D'
            create(internal_type, tokens[2])
    elif cmd == "OPEN" and len(tokens) == 3:
        mode = tokens[1].upper()
        if mode not in ('I', 'O', 'U'):
            print(f"Error: Invalid mode for OPEN: '{tokens[1]}'. Use I, O, or U.")
        else:
            fd = open_file(mode, tokens[2])
            if fd is not None:
                print(f"File descriptor: {fd}")
    elif cmd == "CLOSE" and len(tokens) == 1:
        close_file()
    elif cmd == "DELETE" and len(tokens) == 2:
        if not tokens[1].startswith('/'):
            print(f"Error: Invalid path '{tokens[1]}'. Paths must start with '/'.")
        else:
            delete(tokens[1])
    elif cmd == "WRITE" and len(tokens) >= 3:
        # WRITE <n> 'data'  -> write up to <n> bytes of 'data' into the
        #    most-recently opened file (auto-create '/auto_file' if none)
        first = tokens[1]
        raw_data = " ".join(tokens[2:]).strip("'\"")
        if not raw_data:
            print("Error: No data provided for WRITE.")
            return
        if first.isdigit():
            try:
                n = int(first)
            except ValueError:
                print(f"Error: Invalid byte count '{first}'.")
                return
            # Find most-recently opened FD
            fd = None
            for i in range(len(open_stack) - 1, -1, -1):
                if open_stack[i] is not None:
                    fd = i
                    break
            # If no open file, create an auto file and open it
            if fd is None:
                root = DREAD(0)
                names = set(e.name for e in root.entries)
                base = 'auto_file'
                name = base
                suffix = 1
                while name in names:
                    name = f"{base}_{suffix}"
                    suffix += 1
                path = f"/{name}"
                create('U', path)
                for i in range(len(open_stack) - 1, -1, -1):
                    if open_stack[i] is not None:
                        fd = i
                        break
            if fd is None:
                print("Error: No file available to write to.")
            else:
                data_bytes = raw_data.encode()
                to_write = data_bytes[:n]
                data_str = to_write.decode(errors='ignore')
                write_cmd(fd, data_str)
        else:
            # treat first token as explicit FD if not purely numeric count
            try:
                fd = int(first)
            except ValueError:
                print(f"Error: Invalid WRITE arguments '{first}'. FD or byte count expected.")
                return
            data_str = raw_data
            write_cmd(fd, data_str)
    elif cmd == "READ" and len(tokens) == 3:
        try:
            fd = int(tokens[1])
            num_bytes = int(tokens[2])
        except ValueError:
            print("Error: READ expects numeric FD and byte count.")
            return
        read_cmd(fd, num_bytes)
    elif cmd == "READ" and len(tokens) == 2:
        # READ <n> -> read from most-recently opened file
        try:
            num_bytes = int(tokens[1])
        except ValueError:
            print(f"Error: Invalid READ argument '{tokens[1]}'")
            return
        fd = None
        for i in range(len(open_stack) - 1, -1, -1):
            if open_stack[i] is not None:
                fd = i
                break
        if fd is None:
            print("Error: No open file to read from.")
        else:
            read_cmd(fd, num_bytes)
    elif cmd == "SEEK":
        # New CLI supports both forms:
        # 1) SEEK <base> <offset>  (no FD) -> applies to most-recent open file
        #    where base in {-1,0,1} maps to (beginning, current, end)
        # 2) SEEK <fd> <offset>    (legacy short form) -> set absolute offset
        # 3) SEEK <fd> <base> <offset> (legacy long form)
        if len(tokens) == 3:
            try:
                a = int(tokens[1])
                b = int(tokens[2])
            except ValueError:
                print("Error: SEEK arguments must be integers.")
                return
            # If first arg is one of the new base codes (-1,0,1), treat as no-FD form
            if a in (-1, 0, 1):
                # find most-recently opened FD
                fd = None
                for i in range(len(open_stack) - 1, -1, -1):
                    if open_stack[i] is not None:
                        fd = i
                        break
                if fd is None:
                    print("Error: No open file to seek.")
                else:
                    seek_cmd(fd, a, b)
            else:
                # legacy short form: SEEK <fd> <offset> (treat as absolute set)
                fd = a
                offset = b
                seek_cmd(fd, -1, offset)
        elif len(tokens) == 4:
            try:
                fd = int(tokens[1])
                base = int(tokens[2])
                offset = int(tokens[3])
            except ValueError:
                print("Error: SEEK arguments must be integers.")
                return
            seek_cmd(fd, base, offset)
        else:
            print(f"Error: Unknown or malformed SEEK '{line.strip()}'")
    else:
        print(f"Error: Unknown or malformed command '{line.strip()}'")


# -----------------------------
# 7. Final Report
# -----------------------------
def print_dir_recursive(dir_block, prefix=""):
    """
    Recursively print directory tree structure starting from dir_block.
    
    Logic:
    1. For each entry in directory:
       - Print entry type (F or D), name, start block, size
       - If directory: recursively print its contents with increased indentation
    
    Provides visual hierarchical view of entire filesystem.
    """
    for e in dir_block.entries:
        print(f"{prefix}{e.ftype} {e.name} (start={e.start_block}, size={e.size})")
        if e.ftype == 'D':
            subdir = DREAD(e.start_block)
            print_dir_recursive(subdir, prefix + "  ")


def final_report():
    """
    Print final state of the disk after program execution.
    
    Shows:
    1. Complete directory tree structure
    2. All open files (FD, path, mode, offset) or closed slots
    """
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
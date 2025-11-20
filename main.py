# main.py
"""
# -----------------------------
# Basic Setup
# -----------------------------
CREATE D /sub             # Create directory "sub"
CREATE D /sub/docs        # Create directory "docs" inside "sub"
CREATE U /sub/docs/file1  # Create a new file "file1" under /sub/docs

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
from disk import init_disk
from fs_ops import create, open_file, close_file, delete, write_cmd, read_cmd, open_stack, seek


def process_line(line):
    tokens = line.strip().split()
    if not tokens:
        return
    cmd = tokens[0].upper()

    if cmd == "CREATE" and len(tokens) == 3:
        ftype = tokens[1].upper()
        # CLI uses 'U' for file (maps to internal 'F')
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
        # Close the most recently opened file (no FD argument required)
        close_file()
    elif cmd == "DELETE" and len(tokens) == 2:
        if not tokens[1].startswith('/'):
            print(f"Error: Invalid path '{tokens[1]}'. Paths must start with '/'.")
        else:
            delete(tokens[1])
    elif cmd == "WRITE":
        # Two forms supported:
        # 1) WRITE <n> 'data'  (creates/writes a default file)
        # 2) WRITE <fd> 'data'  (write to an open FD at current offset)
        if len(tokens) >= 3:
            data_str = " ".join(tokens[2:]).strip("'\"")
            if not data_str:
                print("Error: No data provided for WRITE.")
                return
            if tokens[1].isdigit():
                fd_or_n = tokens[1]
                # detect short CREATE-like form when only two tokens and numeric n
                if len(tokens) == 3 and not (len(open_stack) and any(f is not None for f in open_stack)):
                    write_cmd(f"{fd_or_n} {data_str}")
                else:
                    try:
                        fd = int(fd_or_n)
                    except ValueError:
                        print(f"Error: Invalid FD '{fd_or_n}'.")
                        return
                    write_cmd(fd, data_str)
            else:
                try:
                    fd = int(tokens[1])
                except ValueError:
                    print(f"Error: Invalid WRITE arguments '{tokens[1]}'. FD expected.")
                    return
                write_cmd(fd, data_str)
    elif cmd == "READ" and len(tokens) == 3:
        try:
            fd = int(tokens[1])
            n = int(tokens[2])
        except ValueError:
            print("Error: READ expects numeric FD and byte count.")
            return
        read_cmd(fd, n)
    elif cmd == "READ" and len(tokens) == 2:
        # READ <n> -> read from most-recently opened file (no FD)
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
        # support short and long forms
        if len(tokens) == 3:
            try:
                fd = int(tokens[1])
                offset = int(tokens[2])
            except ValueError:
                print("Error: SEEK expects integer FD and offset.")
                return
            seek(fd, offset)
        elif len(tokens) == 4:
            try:
                fd = int(tokens[1])
                base = int(tokens[2])
                offset = int(tokens[3])
            except ValueError:
                print("Error: SEEK expects integer FD, base, and offset.")
                return
            seek(fd, base, offset)
        else:
            print(f"Error: Unknown or malformed command '{line.strip()}'")
    else:
        print(f"Error: Unknown or malformed command '{line.strip()}'")

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
    print("\nOpen files:")
    for i, of in enumerate(open_stack):
        if of:
            print(f"FD {i}: {of.path}, mode={of.mode}")
        else:
            print(f"FD {i}: Closed")

if __name__ == "__main__":
    main()


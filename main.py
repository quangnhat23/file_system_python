# main.py
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
from disk import init_disk
from fs_ops import create, open_file, close_file, delete, write_cmd, read_cmd, open_stack, seek


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
    elif cmd == "READ" and len(tokens) == 3:
        fd = int(tokens[1])
        read_cmd(fd, int(tokens[2]))
    elif cmd == "SEEK" and len(tokens) == 3:
        seek(int(tokens[1]), int(tokens[2]))
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


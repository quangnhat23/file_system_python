# main.py
"""
File system simulator (Python) — Hierarchical version
Implements:
  - Disk of 100 blocks x 512 bytes
  - Hierarchical directories (block 0 is root)
  - Data blocks (504 bytes user data + BACK/FRWD)
  - Commands: CREATE, OPEN, CLOSE, DELETE, READ, WRITE, SEEK
Usage:
  - CREATE D /sub
  - CREATE D /sub/docs
  - CREATE F /sub/docs/file1
  - OPEN O /sub/docs/file1
  - WRITE 0 'Hello World'
  - CLOSE 0
  - OPEN I /sub/docs/file1
  - READ 0 11
  - CLOSE 0
  - exit
"""
from disk import init_disk
from fs_ops import create, open_file, close_file, delete, write_cmd, read_cmd, open_stack

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
        read_cmd(fd, int(tokens[2]))
    else:
        print(f"Unknown command '{line.strip()}'")

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


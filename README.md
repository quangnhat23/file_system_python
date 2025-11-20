# 🗂️ File System Simulation in Python

## 📘 Overview
This project implements a **simple hierarchical file system** in Python, simulating basic disk operations similar to UNIX.  
It supports files, directories, and fundamental commands such as `CREATE`, `OPEN`, `READ`, `WRITE`, `SEEK`, `CLOSE`, and `DELETE`.

The disk is simulated with:
- **100 blocks (0–99)**, each of size **512 bytes**
- **Root directory stored in block 0**
- **504 bytes** available for user data per block

---

## ⚙️ Features
✅ Hierarchical directories (`/sub/docs/file1`)  
✅ Create, open, read, write, seek, and delete files  
✅ **Auto-open files in Output mode when created**  
✅ Simulated disk read/write using in-memory structures  
✅ File descriptors and offset tracking  
✅ Update mode for combined read/write access  
✅ SEEK with Unix-standard semantics (SET/CUR/END)  
✅ Comprehensive unit tests (10 passing tests)  
✅ Support for nested directory deletion  
❗ Multi-block files not implemented (single-block files only)
✅ Automatic cleanup and final disk state report  

---

## 📂 Project Structure

```
file_system_python/
├── disk.py                    # Disk simulation and block I/O
├── fs_structs.py              # Data structures (DirEntry, DirBlock, DataBlock, OpenFile)
├── fs_ops.py                  # Modular file system operations
├── file_system.py             # Monolithic file system implementation
├── main.py                    # CLI wrapper around fs_ops
├── test_seek_read.py          # Manual test for SEEK/READ functionality
├── tests/
│   ├── test_fs_ops_unittest.py # Comprehensive unit test suite (10 tests)
│   └── test_fs_ops.py         # Additional test file
└── README.md                  # This file
```

### Key Components

| Component | Description |
|------------|--------------|
| `DirEntry` | Directory entry storing name, type, start block, and size |
| `DirBlock` | Directory block containing entries (like folders) |
| `DataBlock` | User data block (504 bytes + next block pointer) |
| `OpenFile` | Tracks open files, mode, and offset |
| `disk` | Simulated disk as a list of blocks |
| `open_stack` | Active file descriptors list |

---

## 🚀 Quick Start

### Running the CLI
```bash
# Using fs_ops module with main.py
python main.py

# Or using the monolithic file_system.py
python file_system.py
```

### Running Tests
```bash
# Run all unit tests
python -m unittest tests.test_fs_ops_unittest -v

# Run specific test
python -m unittest tests.test_fs_ops_unittest.TestFsOps.test_delete_recursion -v

# Run with coverage
python -m unittest tests.test_fs_ops_unittest -v --coverage
```

---

## 🧠 Command Reference

### **File & Directory Creation**
```bash
CREATE D /sub              # Create directory
CREATE F /sub/docs/file1   # Create file (auto-opens in Output mode)
```
When a file is created, it automatically opens in **Output ('w') mode** and returns a file descriptor.

### **File Operations**
```bash
OPEN I /sub/docs/file1     # Open for reading (Input mode)
OPEN O /sub/docs/file1     # Open for writing (Output mode)
OPEN U /sub/docs/file1     # Open for read/write (Update mode)

WRITE 0 'Hello World'      # Write to FD 0 at current offset
READ 0 11                  # Read 11 bytes from FD 0 at current offset

CLOSE                      # Close most recently opened file
CLOSE 0                    # Close specific FD (deprecated, use CLOSE)
```

### **File Pointer Operations (SEEK)**
SEEK supports multiple forms. The CLI also supports a compact form that applies
to the most-recently opened file (no FD required).

CLI compact form (no FD):
```bash
SEEK <base> <offset>   # applies to most-recent open file
```
Where `base` is one of:
- `-1` = beginning of file (set absolute offset)
- `0`  = current position (SEEK_CUR)
- `1`  = end of file (SEEK_END)

Examples:
- `SEEK -1 0`  -> move to beginning of file
- `SEEK 1 0`   -> move to end of file
- `SEEK 0 -5`  -> move backwards 5 bytes from current

Legacy / explicit FD forms are also supported:

Short form (explicit FD, absolute set):
```bash
SEEK <fd> <offset>        # set absolute offset for FD
```

Long form (explicit FD with base):
```bash
SEEK <fd> <base> <offset> # where base follows the legacy codes 0=SET,1=CUR,2=END
```

Note: the CLI compact form uses `-1/0/1` for begin/current/end. The explicit FD
long form accepts the legacy `0/1/2` base codes.

### **Deletion**
```bash
DELETE /sub/docs/file1     # Delete file
DELETE /sub/docs           # Delete directory (must be empty)
DELETE /sub                # Delete directory tree
```

### **Exit Program**
```bash
exit                       # Stop the program
```

---

## 📋 SEEK & READ Semantics

### SEEK Behavior
- **Bounds**: Offsets must be in range [0, USER_DATA_SIZE (504 bytes)]
- **Beyond EOF in read mode**: Rejected with error message
- **Beyond EOF in write/update modes**: Allowed; extends file size
- **Negative offsets**: Rejected with error message

### READ Behavior
- `READ <fd> <n>` reads up to `<n>` bytes from current file offset
- Automatically advances file offset by number of bytes read
- Returns 0 bytes if offset is at or past EOF
- Returns available bytes if fewer than `<n>` remain

### Example Session
```bash
Command> CREATE D /docs
Directory '/docs' created.

Command> CREATE F /docs/hello.txt
File '/docs/hello.txt' created.
File descriptor: 0

Command> WRITE 11 'Hello World!'
Wrote 11 bytes to FD 0.

Command> SEEK 0 0
Set offset of FD 0 to 0.

Command> READ 0 5
Read 5 bytes from FD 0: 'Hello'

Command> SEEK 0 1 6
Set offset of FD 0 to 11.

Command> READ 0 1
Read 1 bytes from FD 0: '!'

Command> CLOSE
File '/docs/hello.txt' with FD 0 closed.

Command> exit
```

---

## 🧪 Test Suite

### Unit Tests (10 tests, all passing)
Located in `tests/test_fs_ops_unittest.py`:

1. **test_create_open_write_read** - Basic file operations flow
2. **test_seek_and_write_extend** - SEEK_SET in update mode extends file
3. **test_seek_beyond_eof_read_only** - SEEK beyond EOF rejected in read-only
4. **test_close_most_recent** - CLOSE command closes most recent file
5. **test_delete** - File deletion and verification
6. **test_seek_cur_and_end** - SEEK_CUR and SEEK_END behavior
7. **test_write_capped_and_auto_file** - Write size capping at 504 bytes
8. **test_delete_recursion** - Nested directory and file deletion
9. **test_multiblock_file_write_and_read** - Sequential writes and read with offset tracking
10. **test_seek_write_sparse_file** - Sparse file behavior with seek and write

Run tests:
```bash
python -m unittest tests.test_fs_ops_unittest -v
```

Expected output: **Ran 10 tests in ~0.01s ... OK**

---

## 📝 Implementation Details

### File Modes
- **'r' (Input/Read)**: Read-only mode. Cannot seek beyond EOF.
- **'w' (Output/Write)**: Write-only mode. Offset starts at 0. Can seek and write anywhere up to 504 bytes.
- **'u' (Update)**: Read/write mode. Can both read and write. Can seek beyond EOF to extend file.

### File Offset Tracking
- Each `OpenFile` maintains an offset value
- READ/WRITE operations advance offset by bytes transferred
- SEEK operations set offset based on base parameter (0/1/2)

### Block Allocation
- Free blocks tracked in a simple free list
- Allocation on file/directory creation
- Deallocation on deletion

### Directory Structure
- Directories stored as `DirBlock` with list of `DirEntry` objects
- Path traversal walks from root through directory hierarchy
- Parent directory required to exist when creating files/subdirectories

---

## 🔧 Module Architecture

### `disk.py`
- Core disk simulation: `disk[]` array of 100 blocks
- `DREAD(block_num)`, `DWRITE(block_num, data)` - block I/O
- `allocate_block()`, `free_block(block_num)` - block management
- `init_disk()` - initialize with root directory

### `fs_structs.py`
- `DirEntry` - directory entries with name, type, start_block, size
- `DirBlock` - directory blocks with entries list
- `DataBlock` - file data blocks with 504-byte data and next_block pointer
- `OpenFile` - open file tracking with path, entry, mode, offset

### `fs_ops.py`
- Modular file system operations functions
- `create()`, `open_file()`, `close_file()`, `delete()`
- `read_cmd()`, `write_cmd()`, `seek()`
- Well-documented with detailed docstrings
- `open_stack` - global list of open files

### `file_system.py`
- Monolithic implementation with all operations in one file
- Mirrors fs_ops functionality
- Alternative CLI entry point
- Useful for comparison and learning

### `main.py`
- CLI wrapper around `fs_ops` module
- Command parser with support for all file system operations
- Recommended entry point for interactive use

---

## 📌 Notes

- **Single-block files**: Current implementation stores each file in a single 504-byte block
- **Auto-open on CREATE**: Files automatically open in Output mode, directory entries don't auto-open
- **CLOSE behavior**: `CLOSE` without arguments closes the most recently opened file
- **Replace-on-create**: Creating a file/directory with existing name replaces it
- **Automatic cleanup**: Final disk state and open files shown when program exits

---

## 🐛 Known Limitations

- Multi-block files not yet implemented (files limited to 504 bytes)
- No file permissions or ownership tracking
- No symlinks or hard links
- Disk size fixed at 100 blocks
- No persistence (all data lost on program exit)

---

## 📖 Examples

### Example 1: Basic Write & Read
```bash
CREATE D /data
CREATE F /data/test.txt
WRITE 0 'Python File System'
SEEK 0 0
READ 0 6
CLOSE
DELETE /data/test.txt
DELETE /data
```

### Example 2: Multiple Files
```bash
CREATE D /home
CREATE F /home/file1
WRITE 0 'File 1'
CLOSE

CREATE F /home/file2
WRITE 1 'File 2'
CLOSE

OPEN I /home/file1
READ 0 6
CLOSE

DELETE /home/file1
DELETE /home/file2
DELETE /home
```

### Example 3: Update Mode (Read & Write)
```bash
CREATE F /data.txt
WRITE 0 'Hello World'
CLOSE

OPEN U /data.txt
SEEK 0 5
WRITE 0 '***'
SEEK 0 0
READ 0 20
CLOSE
```

---

## 👨‍💻 Author & License

Created as an educational file system simulation project.

---

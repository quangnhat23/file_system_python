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
✅ Simulated disk read/write using in-memory structures  
✅ File descriptors and offset tracking  
✅ Update mode for combined read/write access  
✅ Automatic cleanup and final disk state report  

---

## 📂 Structure

````markdown
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
✅ Simulated disk read/write using in-memory structures  
✅ File descriptors and offset tracking  
✅ Update mode for combined read/write access  
✅ Automatic cleanup and final disk state report  

---

## 📂 Structure

| Component | Description |
|------------|--------------|
| `DirEntry` | Directory entry storing name, type, start block, and size |
| `DirBlock` | Directory block containing entries (like folders) |
| `DataBlock` | User data block (504 bytes + next block pointer) |
| `OpenFile` | Tracks open files, mode, and offset |
| `disk` | Simulated disk as a list of blocks |
| `open_stack` | Active file descriptors list |

---

## 🧠 Commands & Usage

### **Create Directories and Files**
```bash
CREATE D /sub
CREATE D /sub/docs
CREATE F /sub/docs/file1

### WRITE AND READ DATA
OPEN O /sub/docs/file1
WRITE 0 'Hello World'
CLOSE 0

OPEN I /sub/docs/file1
READ 0 11
CLOSE 0

### UPDATE MODE (read + write)
OPEN U /sub/docs/file1
SEEK 0 5
WRITE 0 '!!!'
READ 0 20
CLOSE 0

### DELETE FILE AND DIRECTORY
DELETE /sub/docs/file1
DELETE /sub/docs
DELETE /sub

## exit
exit


### SEEK and READ (details)

- SEEK supports two forms:
	- Short form (common): `SEEK <fd> <offset>` — sets the file offset to `<offset>` (equivalent to SEEK_SET).
	- Long form: `SEEK <fd> <base> <offset>` — where `base` is:
		- `0` = SEEK_SET (set offset to `<offset>`)
		- `1` = SEEK_CUR (set offset to current_offset + `<offset>`)
		- `2` = SEEK_END (set offset to file_size + `<offset>`)

- Bounds & behavior:
	- Offsets cannot be negative and cannot exceed the block user-data capacity (504 bytes by default).
	- Seeking beyond EOF is allowed only when the file is open in write (`O`) or update (`U`) modes; doing so will extend the file's logical size to the new offset.
	- Seeking beyond EOF in read-only mode (`I`) is rejected.

- READ usage:
	- `READ <fd> <n>` reads up to `<n>` bytes from the current file offset and advances the offset by the number of bytes actually read.
	- If the offset is at or past EOF, `READ` returns 0 bytes.

Examples:
```
OPEN U /sub/docs/file1    # open for update
SEEK 0 5                 # set offset to 5 (SEEK_SET)
WRITE 0 'ABC'            # write at offset 5
SEEK 0 0                 # rewind to start
READ 0 20                # read up to 20 bytes from FD 0
```

These behaviors are implemented and verified by `test_seek_read.py`.

````



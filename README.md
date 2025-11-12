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


 
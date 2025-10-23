# fs_structs.py

from disk import USER_DATA_SIZE

class DirEntry:
    def __init__(self, name, ftype, start_block, size):
        self.name = name
        self.ftype = ftype  # 'F', 'D', 'U'
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


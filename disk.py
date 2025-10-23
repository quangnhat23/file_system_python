# disk.py
BLOCK_SIZE = 512
USER_DATA_SIZE = 504
DISK_BLOCKS = 100

disk = [None] * DISK_BLOCKS

def DREAD(block_num):
    return disk[block_num]

def DWRITE(block_num, data):
    disk[block_num] = data

def init_disk():
    """Initialize the disk with root directory"""
    from fs_structs import DirBlock
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


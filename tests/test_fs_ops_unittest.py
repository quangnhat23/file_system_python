import os
import sys
import unittest

# make sure top-level package modules are importable when tests are run from any cwd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fs_ops import (
    create, open_file, close_file, delete, write_cmd, read_cmd, seek, open_stack
)
from disk import init_disk, DREAD, USER_DATA_SIZE


class TestFsOps(unittest.TestCase):
    def setUp(self):
        init_disk()
        open_stack.clear()

    def test_create_open_write_read(self):
        create('D', '/sub')
        create('D', '/sub/docs')
        create('F', '/sub/docs/file1')

        fd = open_file('O', '/sub/docs/file1')
        self.assertEqual(fd, 0)

        write_cmd(fd, 'Hello')
        entry = open_stack[fd].entry
        data_block = DREAD(entry.start_block)
        self.assertTrue(data_block.data[:5].decode().startswith('Hello'))

        close_file()

        fd = open_file('I', '/sub/docs/file1')
        self.assertEqual(fd, 0)
        read_cmd(fd, 5)
        self.assertEqual(open_stack[fd].offset, 5)
        close_file()

    def test_seek_and_write_extend(self):
        create('D', '/sub')
        create('D', '/sub/docs')
        create('F', '/sub/docs/file2')
        fd = open_file('U', '/sub/docs/file2')

        seek(fd, 0, 10)
        self.assertEqual(open_stack[fd].offset, 10)
        self.assertEqual(open_stack[fd].entry.size, 10)

        write_cmd(fd, 'A')
        entry = open_stack[fd].entry
        data_block = DREAD(entry.start_block)
        self.assertEqual(data_block.data[10:11].decode(), 'A')
        self.assertEqual(entry.size, 11)
        close_file()

    def test_seek_beyond_eof_read_only(self):
        create('D', '/a')
        create('D', '/a/b')
        create('F', '/a/b/file3')
        fd = open_file('I', '/a/b/file3')

        seek(fd, 0, 1)
        self.assertEqual(open_stack[fd].offset, 0)
        close_file()

    def test_close_most_recent(self):
        create('F', '/x')
        create('F', '/y')
        fd1 = open_file('O', '/x')
        fd2 = open_file('O', '/y')
        self.assertGreater(fd2, fd1)

        close_file()
        self.assertIsNone(open_stack[fd2])
        close_file()
        self.assertTrue(all(f is None for f in open_stack))

    def test_delete(self):
        create('D', '/tmp')
        create('F', '/tmp/f1')
        fd = open_file('I', '/tmp/f1')
        self.assertEqual(fd, 0)
        close_file()
        delete('/tmp/f1')
        fd2 = open_file('I', '/tmp/f1')
        self.assertIsNone(fd2)

    def test_seek_cur_and_end(self):
        # SEEK_CUR and SEEK_END behavior
        create('F', '/f')
        fd = open_file('O', '/f')
        write_cmd(fd, 'ABCDEFGHIJ')
        close_file()
        fd = open_file('U', '/f')
        # move to offset 5
        seek(fd, 0, 5)
        self.assertEqual(open_stack[fd].offset, 5)
        # move forward 2 bytes from current
        seek(fd, 1, 2)
        self.assertEqual(open_stack[fd].offset, 7)
        # move to 3 bytes before end
        seek(fd, 2, -3)
        self.assertEqual(open_stack[fd].offset, 7)
        close_file()

    def test_write_capped_and_auto_file(self):
        # Write larger than USER_DATA_SIZE should cap
        create('F', '/big')
        fd = open_file('O', '/big')
        large = 'X' * (USER_DATA_SIZE + 10)
        write_cmd(fd, large)
        entry = open_stack[fd].entry
        self.assertEqual(entry.size, USER_DATA_SIZE)
        close_file()

        # auto-create write: pass a string as first arg
        # no open files -> create '/auto_file'
        # call write_cmd with the special <n> data form
        # first ensure no open files
        open_stack.clear()
        write_cmd('3 Z')
        # auto_file should exist in root
        rt = DREAD(0)
        names = [e.name for e in rt.entries]
        self.assertIn('auto_file', names)

    def test_delete_recursion(self):
        # Create nested directories with files
        create('D', '/root_dir')
        create('D', '/root_dir/sub_dir')
        create('F', '/root_dir/file1.txt')
        create('F', '/root_dir/sub_dir/file2.txt')

        # Verify structure
        root_block = DREAD(0)
        self.assertEqual(len(root_block.entries), 1)  # root_dir
        root_dir_entry = root_block.entries[0]
        self.assertEqual(root_dir_entry.name, 'root_dir')
        root_dir_block = DREAD(root_dir_entry.start_block)
        self.assertEqual(len(root_dir_block.entries), 2)  # file1 and sub_dir

        # Find sub_dir entry
        sub_dir_entry = None
        for e in root_dir_block.entries:
            if e.name == 'sub_dir':
                sub_dir_entry = e
                break
        self.assertIsNotNone(sub_dir_entry)
        
        # Delete file in subdirectory
        delete('/root_dir/sub_dir/file2.txt')
        sub_dir_block = DREAD(sub_dir_entry.start_block)
        self.assertEqual(len(sub_dir_block.entries), 0)

        # Delete empty subdirectory
        delete('/root_dir/sub_dir')
        root_dir_block = DREAD(root_dir_entry.start_block)  # refresh
        self.assertEqual(len(root_dir_block.entries), 1)  # only file1 left

        # Delete file in root_dir
        delete('/root_dir/file1.txt')
        root_dir_block = DREAD(root_dir_entry.start_block)  # refresh
        self.assertEqual(len(root_dir_block.entries), 0)

        # Delete empty root_dir
        delete('/root_dir')
        root_block = DREAD(0)  # refresh
        self.assertEqual(len(root_block.entries), 0)

    def test_multiblock_file_write_and_read(self):
        # Test writing and reading multi-offset data in a single block
        # Note: current implementation uses single block per file, so we test
        # sequential writes and offset tracking
        create('D', '/mb')
        create('F', '/mb/multiblock')
        fd = open_file('O', '/mb/multiblock')

        # Write to fill most of the block
        data1 = 'A' * 400
        write_cmd(fd, data1)
        self.assertEqual(open_stack[fd].offset, 400)
        self.assertEqual(open_stack[fd].entry.size, 400)

        # Continue writing in same file (append)
        data2 = 'B' * 100
        write_cmd(fd, data2)
        self.assertEqual(open_stack[fd].offset, 500)
        self.assertEqual(open_stack[fd].entry.size, 500)

        close_file()

        # Reopen and verify contents
        fd = open_file('I', '/mb/multiblock')
        read_cmd(fd, 400)
        # offset should now be 400
        self.assertEqual(open_stack[fd].offset, 400)

        # Read remaining
        read_cmd(fd, 100)
        self.assertEqual(open_stack[fd].offset, 500)
        close_file()

    def test_seek_write_sparse_file(self):
        # Test seeking far into a file and writing (sparse-like behavior)
        create('F', '/sparse')
        fd = open_file('U', '/sparse')

        # Seek to offset 100
        seek(fd, 0, 100)
        self.assertEqual(open_stack[fd].offset, 100)

        # Write at offset 100
        write_cmd(fd, 'SPARSE')
        entry = open_stack[fd].entry
        self.assertEqual(entry.size, 106)  # offset 100 + 6 bytes written

        # Seek back to 0 and read should give empty/null bytes
        seek(fd, 0, 0)
        read_cmd(fd, 10)
        # should read 10 bytes at offset [0:10]
        self.assertEqual(open_stack[fd].offset, 10)

        # Seek to where we wrote and verify
        seek(fd, 0, 100)
        read_cmd(fd, 6)
        self.assertEqual(open_stack[fd].offset, 106)
        close_file()


if __name__ == '__main__':
    unittest.main()

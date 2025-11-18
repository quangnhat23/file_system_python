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


if __name__ == '__main__':
    unittest.main()

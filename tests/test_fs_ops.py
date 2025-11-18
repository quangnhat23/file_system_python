import pytest
from fs_ops import (
    create, open_file, close_file, delete, write_cmd, read_cmd, seek, open_stack
)
from disk import init_disk, DREAD


@pytest.fixture(autouse=True)
def reset_disk_and_fds():
    # runs before each test
    init_disk()
    # reset fs_ops open_stack
    open_stack.clear()


def test_create_open_write_read():
    create('D', '/sub')
    create('D', '/sub/docs')
    create('F', '/sub/docs/file1')

    fd = open_file('O', '/sub/docs/file1')
    assert fd == 0

    write_cmd(fd, 'Hello')
    # verify by reading the data block bytes
    entry = open_stack[fd].entry
    data_block = DREAD(entry.start_block)
    assert data_block.data[:5].decode().startswith('Hello')

    close_file()

    # reopen for reading
    fd = open_file('I', '/sub/docs/file1')
    assert fd == 0

    read_cmd(fd, 5)  # consumes 'Hello'
    # offset advanced
    assert open_stack[fd].offset == 5
    close_file()


def test_seek_and_write_extend():
    create('D', '/sub')
    create('D', '/sub/docs')
    create('F', '/sub/docs/file2')
    fd = open_file('U', '/sub/docs/file2')

    # seek beyond EOF in update mode should be allowed and extend file
    seek(fd, 0, 10)
    assert open_stack[fd].offset == 10
    assert open_stack[fd].entry.size == 10

    write_cmd(fd, 'A')
    entry = open_stack[fd].entry
    data_block = DREAD(entry.start_block)
    assert data_block.data[10:11].decode() == 'A'
    assert entry.size == 11
    close_file()


def test_seek_beyond_eof_read_only():
    create('D', '/a')
    create('D', '/a/b')
    create('F', '/a/b/file3')
    fd = open_file('I', '/a/b/file3')

    # seek beyond EOF should be rejected in read-only mode
    seek(fd, 0, 1)
    assert open_stack[fd].offset == 0
    close_file()


def test_close_most_recent():
    create('F', '/x')
    create('F', '/y')
    fd1 = open_file('O', '/x')
    fd2 = open_file('O', '/y')
    assert fd2 > fd1

    close_file()  # should close file y
    assert open_stack[fd2] is None
    # close the remaining
    close_file()
    assert all(f is None for f in open_stack)


def test_delete():
    create('D', '/tmp')
    create('F', '/tmp/f1')

    # ensure file exists
    fd = open_file('I', '/tmp/f1')
    assert fd == 0

    close_file()
    delete('/tmp/f1')

    # trying to open should fail
    fd2 = open_file('I', '/tmp/f1')
    assert fd2 is None

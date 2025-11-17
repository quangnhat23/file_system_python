from file_system import (
    init_disk, create, open_file, write_cmd, close_file,
    read_cmd, seek_cmd, final_report
)

init_disk()
create('D', '/sub')
create('D', '/sub/docs')
create('F', '/sub/docs/file1')
# open for writing
fd = open_file('O', '/sub/docs/file1')
write_cmd(fd, 'Hello World')
close_file(fd)
# open for reading
fd = open_file('I', '/sub/docs/file1')
read_cmd(fd, 11)
close_file(fd)
# open for update
fd = open_file('U', '/sub/docs/file1')
# short SEEK form (SEEK_SET)
seek_cmd(fd, 0, 5)
write_cmd(fd, '!!!')
# read whole
seek_cmd(fd, 0, 0)
read_cmd(fd, 20)
close_file(fd)

final_report()

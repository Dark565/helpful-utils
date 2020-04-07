#!/usr/bin/env python3

# This script does kexec on specified kernel and initrd files

# Copyright (C) 2020  Grzegorz Kociołek (Dark565)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.



import sys, os, time, ctypes, getpass, re

i32 = ctypes.c_int
i64 = ctypes.c_long
void_p = ctypes.c_void_p
char_p = ctypes.c_char_p
size_t = i64

# kexec_file_load system call number
SYS_KEXEC_FILE_LOAD = 320
KEXEC_ARCH_DEFAULT = 0 << 16
#----
# reboot system call number
SYS_REBOOT = 169
LINUX_REBOOT_MAGIC1 = 0xfee1dead
LINUX_REBOOT_MAGIC2 = 672274793
LINUX_REBOOT_CMD_KEXEC = 0x45584543
#----
# sync system call number
SYS_SYNC = 162
#----
# write system call number
SYS_WRITE = 1
#----
# exit system call number
SYS_EXIT = 60
#----

# ERRORS
ESUCCESS    = 0
EBADF       = 9949
EBUSY       = 9952
EINVAL      = 9943
ENOEXEC     = 9954
ENOMEM      = 9971
EPERM       = 9972
#----


libc = ctypes.CDLL(None)
syscall = libc.syscall
syscall.restype = i64

def sys_exit(ret_value):
    syscall.argtypes = i64, i64
    syscall(SYS_EXIT,ret_value)

def sys_write(fileno, buff, buff_size):
    syscall.argtypes = i64, i32, char_p, i64
    return syscall(SYS_WRITE,fileno,buff,buff_size)

# This system call saves all the data on disks. If it wasn't called, all cached data would be lost in the reboot
def sys_sync():
    syscall.argtypes = [i64]
    syscall(SYS_SYNC)

# This system call loads new kernel and initrd
def sys_kexec_file_load(kernel_fd, initrd_fd, cmdline_len, cmdline, flags):
    syscall.argtypes = i64, i32, i32, size_t, char_p, i64
    return syscall(SYS_KEXEC_FILE_LOAD, kernel_fd, initrd_fd, cmdline_len, cmdline, flags)

# This system call reboots system
def sys_reboot(magic1, magic2, cmd, arg):
    syscall.argtypes = i64, i32, i32, i32, void_p 
    return syscall(SYS_REBOOT, magic1, magic2, cmd, arg)

# This procedure shuts down the current kernel and loads a new one loaded by kexec
def linux_reboot_kexec():
    return sys_reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2, LINUX_REBOOT_CMD_KEXEC, None)

def print_to_file(fileno, val):
    if type(val) != str:
        val=str(val)
    val=val.encode('utf-8')
    val_len=len(val)
    sys_write(fileno,val,val_len)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def usage():
    eprint("Usage: {} <kernel image> <initrd file>".format(sys.argv[0]))
    exit(1)


if sys.platform != 'linux':
    eprint("Nah, {} doesn't have the same syscalls as Linux", sys.platform.capitalize())
    exit(1)

euid = os.geteuid()
if euid != 0:
    eprint("Only root has the permission to do it, not you ( {}: {} )".format(euid, getpass.getuser()))
    exit(1)

args_count = len(sys.argv)

if len(sys.argv) < 3: usage()

kernel_file = sys.argv[1]
initrd_file = sys.argv[2]

for i in sys.argv[1:3]:
    if not os.path.isfile(i):
        eprint("'{}' file doesn't exist".format(i))
        exit(1)

cmd_fd = open("/proc/cmdline", "r")
cmd_text = cmd_fd.read()
cmd_fd.close()

cmd_fixed = re.sub("^BOOT_IMAGE=[^ ]* ", "BOOT_IMAGE={} ".format(kernel_file), cmd_text)

cmd_fixed_b = cmd_fixed.encode('utf-8')
cmd_fixed_b_c = ctypes.c_char_p(cmd_fixed_b)

kernel_fd = open(kernel_file, "r")
initrd_fd = open(initrd_file, "r")

# Load kernel and initrd images
if sys_kexec_file_load(kernel_fd.fileno(), initrd_fd.fileno(), len(cmd_fixed_b)+1, cmd_fixed_b_c, KEXEC_ARCH_DEFAULT):
    eprint("Error in kexec_file_load(2) has occured")
    exit(1)

# Wait 5 seconds
print("System will reboot in 5 seconds..")
time.sleep(5)

# Write all cached data onto disks
sys_sync()
# Load new kernel
linux_reboot_kexec()

#print(ctypes.cast(cmd_c_ptr,ctypes.c_wchar_p).value)

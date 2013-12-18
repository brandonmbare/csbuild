# Copyright (C) 2013 Jaedyn K. Draper
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os

def get_warnings(warnFlags, noWarnings):
    """Returns a string containing all of the passed warning flags, formatted to be passed to gcc/g++."""
    if noWarnings:
        return "-w "
    ret = ""
    for flag in warnFlags:
        ret += "-W{0} ".format(flag)
    return ret


def get_defines(defines, undefines):
    """Returns a string containing all of the passed defines and undefines, formatted to be passed to gcc/g++."""
    ret = ""
    for define in defines:
        ret += "-D{0} ".format(define)
    for undefine in undefines:
        ret += "-U{0} ".format(undefine)
    return ret


def get_include_dirs(includeDirs):
    """Returns a string containing all of the passed include directories, formatted to be passed to gcc/g++."""
    ret = ""
    for inc in includeDirs:
        ret += "-I{0} ".format(os.path.abspath(inc))
    ret += "-I/usr/include -I/usr/local/include "
    return ret


def get_libraries(libraries):
    """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
    ret = ""
    for lib in libraries:
        ret += "-l{0} ".format(lib)
    return ret


def get_static_libraries(libraries):
    """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
    ret = ""
    for lib in libraries:
        ret += "-static -l{0} ".format(lib)
    return ret


def get_library_dirs(libDirs, forLinker):
    """Returns a string containing all of the passed library dirs, formatted to be passed to gcc/g++."""
    ret = ""
    for lib in libDirs:
        ret += "-L{0} ".format(lib)
    ret += "-L/usr/lib -L/usr/local/lib "
    if forLinker:
        for lib in libDirs:
            ret += "-Wl,-R{0} ".format(os.path.abspath(lib))
        ret += "-Wl,-R/usr/lib -Wl,-R/usr/local/lib "
    return ret


def get_flags(flags):
    """Returns a string containing all of the passed flags, formatted to be passed to gcc/g++."""
    ret = ""
    for flag in flags:
        ret += "-f{0} ".format(flag)
    return ret

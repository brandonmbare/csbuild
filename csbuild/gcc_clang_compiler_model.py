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
import shlex
import subprocess
import re
import sys
from csbuild import _shared_globals


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


def get_dynamic_link_command(compiler, profileEnabled, outputFile, objList, libraries, staticLibraries, libraryDirs,
        debug_level, opt_level, isShared, linkerFlags):
    return "{0} {1} -o{2} {3} {4}{5}{6}-g{7} -O{8} {9} {10}".format(compiler, "-pg" if profileEnabled else "",
        outputFile, " ".join(objList),
        get_libraries(libraries), get_static_libraries(staticLibraries), get_library_dirs(libraryDirs, True),
        debug_level, opt_level, "-shared" if isShared else "", linkerFlags)


def get_static_link_command(outputFile, objList):
    return "ar rcs {0} {1}".format(outputFile, " ".join(objList))


def find_library(library, library_dirs):
    success = True
    out = ""
    try:
        if _shared_globals.show_commands:
            print("ld -o /dev/null --verbose {0} -l{1}".format(
                get_library_dirs(library_dirs, False),
                library))
        cmd = ["ld", "-o", "/dev/null", "--verbose", "-l{0}".format(library)]
        cmd += shlex.split(get_library_dirs(library_dirs, False))
        out = subprocess.check_output(cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        out = e.output
        success = False
    finally:
        if sys.version_info >= (3,0):
            RMatch = re.search("attempt to open (.*) succeeded".format(re.escape(library)).encode('utf-8'), out)
        else:
            RMatch = re.search("attempt to open (.*) succeeded".format(re.escape(library)), out)
        #Some libraries (such as -liberty) will return successful but don't have a file (internal to ld maybe?)
        #In those cases we can probably assume they haven't been modified.
        #Set the mtime to 0 and return success as long as ld didn't return an error code.
        if RMatch is not None:
            lib = RMatch.group(1)
            return lib
        elif not success:
            return None


def get_base_command(compiler, defines, undefines, debug_level, opt_level, isShared, enableProfile, standard, flags,
        extraFlags):
    exitcodes = ""
    if "clang" not in compiler:
        exitcodes = "-pass-exit-codes"
    return "{0} {1} -Winvalid-pch -c {2}-g{3} -O{4} {5}{6}{7} {8}{9}".format(compiler, exitcodes,
        get_defines(defines, undefines), debug_level, opt_level, "-fPIC " if isShared else "",
        "-pg " if enableProfile else "", "--std={0}".format(standard) if standard != "" else "",
        get_flags(flags), extraFlags)


def get_extended_command(baseCmd, warnFlags, disableWarnings, includeDirs, forceIncludeFile, outObj, inFile):
    inc = ""
    if forceIncludeFile:
        inc = "-include {0}".format(forceIncludeFile.rsplit(".", 1)[0])
    return "{0} {1}{2}{3} -o\"{4}\" \"{5}\"".format(baseCmd,
        get_warnings(warnFlags, disableWarnings),
        get_include_dirs(includeDirs), inc, outObj,
        inFile)

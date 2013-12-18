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
        ret += "-W{} ".format(flag)
    return ret


def get_defines(defines, undefines):
    """Returns a string containing all of the passed defines and undefines, formatted to be passed to gcc/g++."""
    ret = ""
    for define in defines:
        ret += "-D{} ".format(define)
    for undefine in undefines:
        ret += "-U{} ".format(undefine)
    return ret


def get_include_dirs(includeDirs):
    """Returns a string containing all of the passed include directories, formatted to be passed to gcc/g++."""
    ret = ""
    for inc in includeDirs:
        ret += "-I{} ".format(os.path.abspath(inc))
    ret += "-I/usr/include -I/usr/local/include "
    return ret


def get_libraries(libraries):
    """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
    ret = ""
    for lib in libraries:
        ret += "-l{} ".format(lib)
    return ret


def get_static_libraries(libraries):
    """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
    ret = ""
    for lib in libraries:
        ret += "-static -l{} ".format(lib)
    return ret


def get_library_dirs(libDirs, forLinker):
    """Returns a string containing all of the passed library dirs, formatted to be passed to gcc/g++."""
    ret = ""
    for lib in libDirs:
        ret += "-L{} ".format(lib)
    ret += "-L/usr/lib -L/usr/local/lib "
    if forLinker:
        for lib in libDirs:
            ret += "-Wl,-R{} ".format(os.path.abspath(lib))
        ret += "-Wl,-R/usr/lib -Wl,-R/usr/local/lib "
    return ret


def get_flags(flags):
    """Returns a string containing all of the passed flags, formatted to be passed to gcc/g++."""
    ret = ""
    for flag in flags:
        ret += "-f{} ".format(flag)
    return ret

def get_link_command(project, outputFile, objList):
    if project.globalDict.static:
        return "ar rcs {} {}".format(outputFile, " ".join(objList))
    else:
        if project.globalDict.hasCppFiles:
            cmd = project.globalDict.cxx
        else:
            cmd = project.globalDict.cc

        return "{} {}{}-o{} {} {}{}{}{}-g{} -O{} {} {}".format(
            cmd,
            "-m32 " if project.globalDict.force_32_bit else "-m64 " if project.globalDict.force_64_bit else "",
            "-pg " if project.globalDict.profile else "",
            outputFile,
            " ".join(objList),
            "-static-libgcc -static-libstdc++ " if project.globalDict.static_runtime else "",
            get_libraries(project.globalDict.libraries),
            get_static_libraries(project.globalDict.static_libraries),
            get_library_dirs(project.globalDict.library_dirs, True),
            project.globalDict.debug_level,
            project.globalDict.opt_level,
            "-shared" if project.globalDict.shared else "",
            project.globalDict.linker_flags
        )

def find_library(library, library_dirs):
    success = True
    out = ""
    try:
        if _shared_globals.show_commands:
            print("ld -o /dev/null --verbose {} -l{}".format(
                get_library_dirs(library_dirs, False),
                library))
        cmd = ["ld", "-o", "/dev/null", "--verbose", "-l{}".format(library)]
        cmd += shlex.split(get_library_dirs(library_dirs, False))
        out = subprocess.check_output(cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        out = e.output
        success = False
    finally:
        if sys.version_info >= (3, 0):
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


def get_base_command(compiler, project, isCpp):
    exitcodes = ""
    if "clang" not in compiler:
        exitcodes = "-pass-exit-codes"

    if isCpp:
        standard = project.globalDict.cppstandard
    else:
        standard = project.globalDict.cstandard
    return "{} {}{} -Winvalid-pch -c {}-g{} -O{} {}{}{} {}{}".format(
        compiler,
        "-m32 " if project.globalDict.force_32_bit else "-m64 " if project.globalDict.force_64_bit else "",
        exitcodes,
        get_defines(project.globalDict.defines, project.globalDict.undefines),
        project.globalDict.debug_level,
        project.globalDict.opt_level,
        "-fPIC " if project.globalDict.shared else "",
        "-pg " if project.globalDict.profile else "",
        "--std={0}".format(standard) if standard != "" else "",
        get_flags(project.globalDict.flags),
        project.globalDict.extra_flags
    )


def get_base_cxx_command(project):
    return get_base_command(project.globalDict.cxx, project, True)


def get_base_cc_command(project):
    return get_base_command(project.globalDict.cc, project, False)


def get_extended_command(baseCmd, project, forceIncludeFile, outObj, inFile):
    inc = ""
    if forceIncludeFile:
        inc = "-include {0}".format(forceIncludeFile.rsplit(".", 1)[0])
    return "{} {}{}{} -o\"{}\" \"{}\"".format(baseCmd,
        get_warnings(project.globalDict.warn_flags, project.globalDict.no_warnings),
        get_include_dirs(project.globalDict.include_dirs), inc, outObj,
        inFile)


interrupt_exit_code = 2

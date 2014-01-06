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
from csbuild import toolchain
import csbuild


class toolchain_gcc(toolchain.toolchainBase):
    def __init__(self):
        toolchain.toolchainBase.__init__(self)

        self.settingsOverrides["warn_flags"] = []
        self.settingsOverrides["cppstandard"] = ""
        self.settingsOverrides["cstandard"] = ""

    def get_warnings(self, warnFlags, noWarnings):
        """Returns a string containing all of the passed warning flags, formatted to be passed to gcc/g++."""
        if noWarnings:
            return "-w "
        ret = ""
        for flag in warnFlags:
            ret += "-W{} ".format(flag)
        return ret


    def get_defines(self, defines, undefines):
        """Returns a string containing all of the passed defines and undefines, formatted to be passed to gcc/g++."""
        ret = ""
        for define in defines:
            ret += "-D{} ".format(define)
        for undefine in undefines:
            ret += "-U{} ".format(undefine)
        return ret


    def get_include_dirs(self, includeDirs):
        """Returns a string containing all of the passed include directories, formatted to be passed to gcc/g++."""
        ret = ""
        for inc in includeDirs:
            ret += "-I{} ".format(os.path.abspath(inc))
        ret += "-I/usr/include -I/usr/local/include "
        return ret


    def get_libraries(self, libraries):
        """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
        ret = ""
        for lib in libraries:
            ret += "-l{} ".format(lib)
        return ret


    def get_static_libraries(self, libraries):
        """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
        ret = ""
        for lib in libraries:
            ret += "-static -l{} ".format(lib)
        return ret


    def get_shared_libraries(self, libraries):
        """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
        ret = ""
        for lib in libraries:
            ret += "-shared -l{} ".format(lib)
        return ret


    def get_library_dirs(self, libDirs, forLinker):
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

    def get_link_command(self, project, outputFile, objList):
        if project.settings.type == csbuild.ProjectType.StaticLibrary:
            return "ar rcs {} {}".format(outputFile, " ".join(objList))
        else:
            if project.settings.hasCppFiles:
                cmd = project.settings.cxx
            else:
                cmd = project.settings.cc

            return "{} {}{}-o{} {} {}{}{}{}{}-g{} -O{} {} {}".format(
                cmd,
                "-m32 " if project.settings.force_32_bit else "-m64 " if project.settings.force_64_bit else "",
                "-pg " if project.settings.profile else "",
                outputFile,
                " ".join(objList),
                "-static-libgcc -static-libstdc++ " if project.settings.static_runtime else "",
                self.get_libraries(project.settings.libraries),
                self.get_static_libraries(project.settings.static_libraries),
                self.get_shared_libraries(project.settings.shared_libraries),
                self.get_library_dirs(project.settings.library_dirs, True),
                project.settings.debug_level,
                project.settings.opt_level,
                "-shared" if project.settings.type == csbuild.ProjectType.SharedLibrary else "",
                " ".join(project.settings.linker_flags)
            )

    def find_library(self, library, library_dirs, force_static, force_shared):
        success = True
        out = ""
        try:
            if _shared_globals.show_commands:
                print("ld -o /dev/null --verbose {} {} -l{}".format(
                    self.get_library_dirs(library_dirs, False),
                    "-static" if force_static else "-shared" if force_shared else "",
                    library))
            cmd = ["ld", "-o", "/dev/null", "--verbose", "-static" if force_static else "-shared" if force_shared else "", "-l{}".format(library)]
            cmd += shlex.split(self.get_library_dirs(library_dirs, False))
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


    def get_base_command(self, compiler, project, isCpp):
        exitcodes = ""
        if "clang" not in compiler:
            exitcodes = "-pass-exit-codes"

        if isCpp:
            standard = self.settingsOverrides["cppstandard"]
        else:
            standard = self.settingsOverrides["cstandard"]
        return "{} {}{} -Winvalid-pch -c {}-g{} -O{} {}{}{} {}".format(
            compiler,
            "-m32 " if project.settings.force_32_bit else "-m64 " if project.settings.force_64_bit else "",
            exitcodes,
            self.get_defines(project.settings.defines, project.settings.undefines),
            project.settings.debug_level,
            project.settings.opt_level,
            "-fPIC " if project.settings.type == csbuild.ProjectType.SharedLibrary else "",
            "-pg " if project.settings.profile else "",
            "--std={0}".format(standard) if standard != "" else "",
            " ".join(project.settings.compiler_flags)
        )


    def get_base_cxx_command(self, project):
        return self.get_base_command(project.settings.cxx, project, True)


    def get_base_cc_command(self, project):
        return self.get_base_command(project.settings.cc, project, False)


    def get_extended_command(self, baseCmd, project, forceIncludeFile, outObj, inFile):
        inc = ""
        if forceIncludeFile:
            inc = "-include {0}".format(forceIncludeFile.rsplit(".", 1)[0])
        return "{} {}{}{} -o\"{}\" \"{}\"".format(baseCmd,
            self.get_warnings(self.settingsOverrides["warn_flags"], project.settings.no_warnings),
            self.get_include_dirs(project.settings.include_dirs), inc, outObj,
            inFile)


    def get_default_extension(self, projectType):
        if projectType == csbuild.ProjectType.Application:
            return ""
        elif projectType == csbuild.ProjectType.StaticLibrary:
            return ".a"
        elif projectType == csbuild.ProjectType.SharedLibrary:
            return ".so"

    def interrupt_exit_code(self):
        return 2


    def WarnFlags(self, *args):
        """Sets warn flags for the project. Multiple arguments. gcc/g++ -W"""
        self.settingsOverrides["warn_flags"] += list(args)


    def ClearWarnFlags(self):
        """Clears the list of warning flags"""
        self.settingsOverrides["warn_flags"] = []


    def CppStandard(self, s):
        """The C/C++ standard to be used when compiling. gcc/g++ --std"""
        self.settingsOverrides["cppstandard"] = s


    def CStandard(self, s):
        """The C/C++ standard to be used when compiling. gcc/g++ --std"""
        self.settingsOverrides["cstandard"] = s

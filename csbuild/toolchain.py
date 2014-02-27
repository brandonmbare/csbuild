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

from abc import abstractmethod
import os
from csbuild import log
import csbuild


class combined_toolchains(object):
    def __init__(self, toolchains):
        self.toolchains = toolchains

    def __getattr__(self, name):
        funcs = []
        for toolchain in self.toolchains:
            funcs.append(getattr(toolchain, name))

        def combined_func(*args, **kwargs):
            for func in funcs:
                func(*args, **kwargs)

        return combined_func


class toolchainBase(object):
    def __init__(self):
        self.settingsOverrides = {}

    @staticmethod
    def additional_args(parser):
        pass

    @abstractmethod
    def get_link_command(self, project, outputFile, objList):
        pass

    @abstractmethod
    def find_library(self, project, library, library_dirs, force_static, force_shared):
        pass

    @abstractmethod
    def get_base_cxx_command(self, project):
        pass

    @abstractmethod
    def get_base_cc_command(self, project):
        pass

    @abstractmethod
    def get_extended_command(self, baseCmd, project, forceIncludeFile, outObj, inFile):
        pass

    @abstractmethod
    def get_base_cxx_precompile_command(self, project):
        pass

    @abstractmethod
    def get_base_cc_precompile_command(self, project):
        pass

    @abstractmethod
    def get_extended_precompile_command(self, baseCmd, project, forceIncludeFile, outObj, inFile):
        pass

    @abstractmethod
    def get_default_extension(self, projectType):
        pass

    @abstractmethod
    def interrupt_exit_code(self):
        pass

    @abstractmethod
    def get_pch_file(self, fileName):
        pass

    def copy(self):
        ret = self.__class__()
        for kvp in self.settingsOverrides.items():
            if isinstance(kvp[1], list):
                ret.settingsOverrides[kvp[0]] = list(kvp[1])
            elif isinstance(kvp[1], dict):
                ret.settingsOverrides[kvp[0]] = dict(kvp[1])
            else:
                ret.settingsOverrides[kvp[0]] = kvp[1]

        return ret

    def InstallOutput(self, s="lib"):
        """Enables installation of the compiled output file. Default target is /usr/local/lib."""
        self.settingsOverrides["output_install_dir"] = s


    def InstallHeaders(self, s="include"):
        """Enables installation of the project's headers. Default target is /usr/local/include."""
        self.settingsOverrides["header_install_dir"] = s


    def InstallSubdir(self, s):
        self.settingsOverrides["header_subdir"] = s


    def ExcludeDirs(self, *args):
        """Excludes the given subdirectories from the build. Accepts multiple string arguments."""
        if "exclude_dirs" not in self.settingsOverrides:
            self.settingsOverrides["exclude_dirs"] = []
        args = list(args)
        newargs = []
        for arg in args:
            if arg[0] != '/' and not arg.startswith("./"):
                arg = "./" + arg
            newargs.append(os.path.abspath(arg))
        self.settingsOverrides["exclude_dirs"] += newargs


    def ExcludeFiles(self, *args):
        """Excludes the given files from the build. Accepts multiple string arguments."""
        if "exclude_files" not in self.settingsOverrides:
            self.settingsOverrides["exclude_files"] = []

        args = list(args)
        newargs = []
        for arg in args:
            if arg[0] != '/' and not arg.startswith("./"):
                arg = "./" + arg
            newargs.append(os.path.abspath(arg))
        self.settingsOverrides["exclude_files"] += newargs


    def Libraries(self, *args):
        """List of libraries to link against. Multiple string arguments. gcc/g++ -l."""
        if "libraries" not in self.settingsOverrides:
            self.settingsOverrides["libraries"] = []

        self.settingsOverrides["libraries"] += list(args)


    def StaticLibraries(self, *args):
        """List of libraries to link statically against. Multiple string arguments. gcc/g++ -l."""
        if "static_libraries" not in self.settingsOverrides:
            self.settingsOverrides["static_libraries"] = []

        self.settingsOverrides["static_libraries"] += list(args)


    def SharedLibraries(self, *args):
        """List of libraries to link statically against. Multiple string arguments. gcc/g++ -l."""
        if "shared_libraries" not in self.settingsOverrides:
            self.settingsOverrides["shared_libraries"] = []

        self.settingsOverrides["shared_libraries"] += list(args)
    def IncludeDirs(self, *args):
        """List of directories to search for included headers. Multiple string arguments. gcc/g++ -I
        By default, this list contains /usr/include and /usr/local/include.
        Using this function will add to the existing list, not replace it.
        """
        if "include_dirs" not in self.settingsOverrides:
            self.settingsOverrides["include_dirs"] = []

        for arg in args:
            arg = os.path.abspath(arg)
            if not os.path.exists(arg):
                log.LOG_WARN("Include path {0} does not exist!".format(arg))
            self.settingsOverrides["include_dirs"].append(arg)


    def LibDirs(self, *args):
        """List of directories to search for libraries. Multiple string arguments. gcc/g++ -L
        By default, this list contains /usr/lib and /usr/local/lib
        Using this function will add to the existing list, not replace it"""
        if "library_dirs" not in self.settingsOverrides:
            self.settingsOverrides["library_dirs"] = []

        for arg in args:
            arg = os.path.abspath(arg)
            if not os.path.exists(arg):
                log.LOG_WARN("Library path {0} does not exist!".format(arg))
            self.settingsOverrides["library_dirs"].append(arg)


    def ClearLibraries(self):
        """Clears the list of libraries"""
        self.settingsOverrides["libraries"] = []


    def ClearStaticLibraries(self):
        """Clears the list of libraries"""
        self.settingsOverrides["static_libraries"] = []


    def ClearSharedLibraries(self):
        """Clears the list of libraries"""
        self.settingsOverrides["shared_libraries"] = []
    def ClearIncludeDirs(self):
        """Clears the include directories, including the defaults."""
        self.settingsOverrides["include_dirs"] = []


    def ClearLibDirs(self):
        """Clears the library directories, including the defaults"""
        self.settingsOverrides["library_dirs"] = []


    def Opt(self, i):
        """Sets the optimization level. gcc/g++ -O"""
        self.settingsOverrides["opt_level"] = i
        self.settingsOverrides["opt_set"] = True


    def Debug(self, i):
        """Sets the debug level. gcc/g++ -g"""
        self.settingsOverrides["debug_level"] = i
        self.settingsOverrides["debug_set"] = True


    def Define(self, *args):
        """Sets defines for the project. Accepts multiple arguments. gcc/g++ -D"""
        if "defines" not in self.settingsOverrides:
            self.settingsOverrides["defines"] = []

        self.settingsOverrides["defines"] += list(args)


    def ClearDefines(self):
        """clears the list of defines"""
        self.settingsOverrides["defines"] = []


    def Undefine(self, *args):
        """Sets undefines for the project. Multiple arguments. gcc/g++ -U"""
        if "undefines" not in self.settingsOverrides:
            self.settingsOverrides["undefines"] = []

        self.settingsOverrides["undefines"] += list(args)


    def ClearUndefines(self):
        """clears the list of undefines"""
        self.settingsOverrides["undefines"] = []


    def CppCompiler(self, s):
        """Sets the compiler to use for the project. Default is g++"""
        self.settingsOverrides["cxx"] = s


    def CCompiler(self, s):
        """Sets the compiler to use for the project. Default is gcc"""
        self.settingsOverrides["cc"] = s


    def Output(self, name, projectType = csbuild.ProjectType.Application):
        """Sets the output file for the project. If unset, the project will be compiled as "a.out" """
        self.settingsOverrides["output_name"] = name
        self.settingsOverrides["type"] = projectType


    def Extension(self, name):
        self.settingsOverrides["ext"] = name


    def OutDir(self, s):
        """Sets the directory to place the compiled result"""
        self.settingsOverrides["output_dir"] = os.path.abspath(s)
        self.settingsOverrides["output_dir_set"] = True


    def ObjDir(self, s):
        """Sets the directory to place pre-link objects"""
        self.settingsOverrides["obj_dir"] = os.path.abspath(s)
        self.settingsOverrides["obj_dir_set"] = True


    def ClearFlags(self):
        """Clears the list of misc flags"""
        self.settingsOverrides["flags"] = []


    def EnableProfile(self):
        """Enables profiling optimizations. gcc/g++ -pg"""
        self.settingsOverrides["profile"] = True


    def DisableProfile(self):
        """Turns profiling back off."""
        self.settingsOverrides["profile"] = False


    def CppCompilerFlags(self, *args):
        """Literal string of extra flags to be passed directly to the compiler"""
        if "cpp_compiler_flags" not in self.settingsOverrides:
            self.settingsOverrides["cpp_compiler_flags"] = []

        self.settingsOverrides["cpp_compiler_flags"] += list(args)

    def ClearCppCompilerFlags(self):
        """Clears the extra flags string"""
        self.settingsOverrides["cpp_compiler_flags"] = []


    def CCompilerFlags(self, *args):
        """Literal string of extra flags to be passed directly to the compiler"""
        if "c_compiler_flags" not in self.settingsOverrides:
            self.settingsOverrides["c_compiler_flags"] = []

        self.settingsOverrides["c_compiler_flags"] += list(args)

    def ClearCCompilerFlags(self):
        """Clears the extra flags string"""
        self.settingsOverrides["c_compiler_flags"] = []

    def CompilerFlags(self, *args):
        """Literal string of extra flags to be passed directly to the compiler"""
        self.CCompilerFlags(*args)
        self.CppCompilerFlags(*args)


    def ClearCompilerFlags(self):
        """Clears the extra flags string"""
        self.ClearCCompilerFlags()
        self.ClearCppCompilerFlags()


    def LinkerFlags(self, *args):
        """Literal string of extra flags to be passed directly to the linker"""
        if "linker_flags" not in self.settingsOverrides:
            self.settingsOverrides["linker_flags"] = []

        self.settingsOverrides["linker_flags"] += list(args)


    def ClearLinkerFlags(self):
        """Clears the linker flags string"""
        self.settingsOverrides["linker_flags"] = []


    def DisableChunkedBuild(self):
        """Turn off the chunked/unity build system and build using individual files."""
        self.settingsOverrides["use_chunks"] = False


    def EnableChunkedBuild(self):
        """Turn chunked/unity build on and build using larger compilation units. This is the default."""
        self.settingsOverrides["use_chunks"] = True


    def ChunkNumFiles(self, i):
        """Set the size of the chunks used in the chunked build. This indicates the number of files per compilation
        unit.
        The default is 10.
        This value is ignored if SetChunks is called.
        Mutually exclusive with ChunkFilesize().
        """
        self.settingsOverrides["chunk_size"] = i
        self.settingsOverrides["chunk_filesize"] = 0


    def ChunkFilesize(self, i):
        """Sets the maximum filesize for a chunk. The default is 500000. This value is ignored if SetChunks is called.
        Mutually exclusive with ChunkNumFiles()
        """
        self.settingsOverrides["chunk_filesize"] = i
        self.settingsOverrides["chunk_size"] = i


    def ChunkTolerance(self, i):
        """Set the number of files above which the files will be built as a chunk.
        For example, if you set this to 3 (the default), then a chunk will be built as a chunk
        if more than three of its files need to be built; if three or less need to be built, they will
        be built individually to save build time.
        """
        if "chunk_filesize" in self.settingsOverrides and self.settingsOverrides["chunk_filesize"] > 0:
            self.settingsOverrides["chunk_size_tolerance"] = i
        elif "chunk_size" in self.settingsOverrides and self.settingsOverrides["chunk_size"] > 0:
            self.settingsOverrides["chunk_tolerance"] = i
        else:
            log.LOG_WARN("Chunk size and chunk filesize are both zero or negative, cannot set a tolerance.")


    def SetChunks(self, *chunks):
        """Explicitly set the chunks used as compilation units.
        This accepts multiple arguments, each of which should be a list of files.
        Each list is one chunk.
        NOTE that setting this will disable the automatic file gathering, so any files you have
        """
        chunks = list(chunks)
        self.settingsOverrides["chunks"] = chunks


    def ClearChunks(self):
        """Clears the explicitly set list of chunks and returns the behavior to the default."""
        self.settingsOverrides["chunks"] = []


    def HeaderRecursionLevel(self, i):
        """Sets the depth to search for header files. If set to 0, it will search with unlimited recursion to find
        included
        headers. Otherwise, it will travel to a depth of i to check headers. If set to 1, this will only check
        first-level
        headers and not check headers included in other headers; if set to 2, this will check headers included in
        headers,
        but not headers included by *those* headers; etc.
    
        This is very useful if you're using a large library (such as boost) or a very large project and are experiencing
        long waits prior to compilation.
        """
        self.settingsOverrides["header_recursion"] = i


    def IgnoreExternalHeaders(self):
        """If this option is set, external headers will not be checked or followed when building. Only headers within
         the
        base project's directory and its subdirectories will be checked. This will speed up header checking, but if you
        modify any external headers, you will need to manually --clean the project.
        """
        self.settingsOverrides["ignore_external_headers"] = True


    def DisableWarnings(self):
        """Disables ALL warnings, including gcc/g++'s built-in warnings."""
        self.settingsOverrides["no_warnings"] = True


    def DefaultTarget(self, s):
        """Sets the default target if none is specified. The default value for this is release."""
        self.settingsOverrides["default_target"] = s.lower()


    def Precompile(self, *args):
        """Explicit list of header files to precompile. Disables chunk precompile when called."""
        self.settingsOverrides["precompile"] = []
        for arg in list(args):
            self.settingsOverrides["precompile"].append(os.path.abspath(arg))
        self.settingsOverrides["chunk_precompile"] = False


    def PrecompileAsC(self, *args):
        self.settingsOverrides["cheaders"] = []
        for arg in list(args):
            self.settingsOverrides["cheaders"].append(os.path.abspath(arg))


    def ChunkPrecompile(self):
        """When this is enabled, all header files will be precompiled into a single "superheader" and included in all
        files."""
        self.settingsOverrides["chunk_precompile"] = True


    def NoPrecompile(self, *args):
        """Disables precompilation and handles headers as usual."""
        if "precompile_exclude" not in self.settingsOverrides:
            self.settingsOverrides["precompile_exclude"] = []

        args = list(args)
        if args:
            newargs = []
            for arg in args:
                if arg[0] != '/' and not arg.startswith("./"):
                    arg = "./" + arg
                newargs.append(os.path.abspath(arg))
                self.settingsOverrides["precompile_exclude"] += newargs
        else:
            self.settingsOverrides["chunk_precompile"] = False


    def EnableUnity(self):
        """Turns on true unity builds, combining all files into only one compilation unit."""
        self.settingsOverrides["unity"] = True


    def StaticRuntime(self):
        self.settingsOverrides["static_runtime"] = True


    def SharedRuntime(self):
        self.settingsOverrides["static_runtime"] = False


    def DebugRuntime(self):
        self.settingsOverrides["debug_runtime"] = True


    def ReleaseRuntime(self):
        self.settingsOverrides["debug_runtime"] = False


    def Force32Bit(self):
        self.settingsOverrides["force_32_bit"] = True
        self.settingsOverrides["force_64_bit"] = False


    def Force64Bit(self):
        self.settingsOverrides["force_64_bit"] = True
        self.settingsOverrides["force_32_bit"] = False

    def OutputArchitecture(self, arch):
        self.settingsOverrides["outputArchitecture"] = arch

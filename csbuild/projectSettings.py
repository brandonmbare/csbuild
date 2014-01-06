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
import csbuild

class projectSettings(object):
    def __init__(self, setupDict=True):
        if not setupDict:
            return

        self.libraries = []
        self.static_libraries = []
        self.shared_libraries = []
        self.include_dirs = []
        self.library_dirs = []

        self.opt_level = 0
        self.debug_level = 0
        self.defines = []
        self.undefines = []
        self.cxx = "g++"
        self.cc = "gcc"
        self.hasCppFiles = False

        self.obj_dir = "."
        self.output_dir = "."
        self.csbuild_dir = "./.csbuild"
        self.output_name = ""
        self.output_install_dir = ""
        self.header_install_dir = ""
        self.header_subdir = ""
        self.automake = True

        self.c_files = []
        self.headers = []

        self.sources = []
        self.allsources = []

        self.type = csbuild.ProjectType.Application
        self.ext = None
        self.profile = False

        self.compiler_flags = []
        self.linker_flags = []

        self.exclude_dirs = []
        self.exclude_files = []

        self.output_dir_set = False
        self.obj_dir_set = False
        self.debug_set = False
        self.opt_set = False

        self.allpaths = []
        self.chunks = []

        self.use_chunks = True
        self.chunk_tolerance = 3
        self.chunk_size = 0
        self.chunk_filesize = 500000
        self.chunk_size_tolerance = 150000

        self.header_recursion = 0
        self.ignore_external_headers = False

        self.default_target = "release"

        self.chunk_precompile = True
        self.precompile = []
        self.precompile_exclude = []
        self.cppheaderfile = ""
        self.cheaderfile = ""
        self.needs_cpp_precompile = False
        self.needs_c_precompile = False

        self.unity = False

        self.precompile_done = False

        self.no_warnings = False

        self.toolchains = {}

        self.cxxcmd = ""  # return value of get_base_cxx_command
        self.cccmd = ""  # return value of get_base_cc_command

        self.recompile_all = False

        self.targets = {}

        self.targetName = ""

        self.final_chunk_set = []

        self.compiles_completed = 0

        self.compile_failed = False

        self.static_runtime = False
        self.debug_runtime = False

        self.force_64_bit = False
        self.force_32_bit = False

        self.cheaders = []

        self.activeToolchainName = None
        self.activeToolchain = None

        self.warnings_as_errors = False


    def __getattribute__(self, name):
        activeToolchain = object.__getattribute__(self, "activeToolchain")
        if activeToolchain and name in activeToolchain.settingsOverrides:
            ret = activeToolchain.settingsOverrides[name]

            if ret:
                if isinstance(ret, dict):
                    ret2 = object.__getattribute__(self, name)
                    ret2.update(ret)
                    return ret2
                elif isinstance(ret, list):
                    return ret + object.__getattribute__(self, name)

            return ret
        return object.__getattribute__(self, name)


    def __setattr__(self, name, value):
        if hasattr(self, "activeToolchain"):
            activeToolchain = object.__getattribute__(self, "activeToolchain")
            if activeToolchain and name in activeToolchain.settingsOverrides:
                activeToolchain.settingsOverrides[name] = value
                return
        object.__setattr__(self, name, value)
    def copy(self):
        ret = projectSettings()
        toolchains = {}
        for kvp in self.toolchains.items():
            toolchains[kvp[0]] = kvp[1].copy()

        ret.__dict__ = {
            "libraries": list(self.libraries),
            "static_libraries": list(self.static_libraries),
            "shared_libraries": list(self.shared_libraries),
            "include_dirs": list(self.include_dirs),
            "library_dirs": list(self.library_dirs),
            "opt_level": self.opt_level,
            "debug_level": self.debug_level,
            "defines": list(self.defines),
            "undefines": list(self.undefines),
            "cxx": self.cxx,
            "cc": self.cc,
            "hasCppFiles": self.hasCppFiles,
            "obj_dir": self.obj_dir,
            "output_dir": self.output_dir,
            "csbuild_dir": self.csbuild_dir,
            "output_name": self.output_name,
            "output_install_dir": self.output_install_dir,
            "header_install_dir": self.header_install_dir,
            "header_subdir": self.header_subdir,
            "automake": self.automake,
            "c_files": list(self.c_files),
            "headers": list(self.headers),
            "sources": list(self.sources),
            "allsources": list(self.allsources),
            "type": self.type,
            "ext": self.ext,
            "profile": self.profile,
            "compiler_flags": list(self.compiler_flags),
            "linker_flags": list(self.linker_flags),
            "exclude_dirs": list(self.exclude_dirs),
            "exclude_files": list(self.exclude_files),
            "output_dir_set": self.output_dir_set,
            "obj_dir_set": self.obj_dir_set,
            "debug_set": self.debug_set,
            "opt_set": self.opt_set,
            "allpaths": list(self.allpaths),
            "chunks": list(self.chunks),
            "use_chunks": self.use_chunks,
            "chunk_tolerance": self.chunk_tolerance,
            "chunk_size": self.chunk_size,
            "chunk_filesize": self.chunk_filesize,
            "chunk_size_tolerance": self.chunk_size_tolerance,
            "header_recursion": self.header_recursion,
            "ignore_external_headers": self.ignore_external_headers,
            "default_target": self.default_target,
            "chunk_precompile": self.chunk_precompile,
            "precompile": list(self.precompile),
            "precompile_exclude": list(self.precompile_exclude),
            "cppheaderfile": self.cppheaderfile,
            "cheaderfile": self.cheaderfile,
            "unity": self.unity,
            "precompile_done": self.precompile_done,
            "no_warnings": self.no_warnings,
            "toolchains": toolchains,
            "cxxcmd": self.cxxcmd,
            "cccmd": self.cccmd,
            "recompile_all": self.recompile_all,
            "targets": dict(self.targets),
            "targetName": self.targetName,
            "final_chunk_set": list(self.final_chunk_set),
            "needs_c_precompile": self.needs_c_precompile,
            "needs_cpp_precompile": self.needs_cpp_precompile,
            "compiles_completed": self.compiles_completed,
            "compile_failed": self.compile_failed,
            "static_runtime": self.static_runtime,
            "debug_runtime": self.debug_runtime,
            "force_64_bit": self.force_64_bit,
            "force_32_bit": self.force_32_bit,
            "cheaders": list(self.cheaders),
            "activeToolchainName": self.activeToolchainName,
            "activeToolchain": None,
            "warnings_as_errors": self.warnings_as_errors
        }

        return ret


currentProject = projectSettings()

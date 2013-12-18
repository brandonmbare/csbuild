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

from csbuild import gcc_clang_compiler_model

libraries = []
static_libraries = []
include_dirs = []
library_dirs = []

opt_level = 0
debug_level = 0
warn_flags = []
flags = []
defines = []
undefines = []
compiler = "g++"
obj_dir = "."
output_dir = "."
csbuild_dir = "./.csbuild"
output_name = "a.out"
output_install_dir = ""
header_install_dir = ""
header_subdir = ""
automake = True
standard = ""

c_files = []
headers = []

sources = []
allsources = []

shared = False
static = False
profile = False

extra_flags = ""
linker_flags = ""

exclude_dirs = []
exclude_files = []

output_dir_set = False
obj_dir_set = False
debug_set = False
opt_set = False

errors = []
warnings = []

allpaths = []
chunks = []

use_chunks = True
chunk_tolerance = 3
chunk_size = 0
chunk_filesize = 500000
chunk_size_tolerance = 150000

header_recursion = 0
ignore_external_headers = False

default_target = "release"

chunk_precompile = True
precompile = []
precompile_exclude = []
headerfile = ""
needs_precompile = True

unity = False

precompile_done = False

no_warnings = False

compiler_model = gcc_clang_compiler_model

cmd = ""

recompile_all = False

targets = {}

targetName = ""

final_chunk_set = []

compiles_completed = 0

compile_failed = False


def copy():
    ret = {"libraries": list(libraries), "static_libraries": list(static_libraries), "include_dirs": list(include_dirs),
           "library_dirs": list(library_dirs),
           "opt_level": opt_level, "debug_level": debug_level, "warn_flags": list(warn_flags), "flags": list(flags),
           "defines": list(defines), "undefines": list(undefines), "compiler": compiler, "obj_dir": obj_dir,
           "output_dir": output_dir, "csbuild_dir": csbuild_dir, "output_name": output_name,
           "output_install_dir": output_install_dir, "header_install_dir": header_install_dir,
           "header_subdir": header_subdir, "automake": automake, "standard": standard, "c_files": list(c_files),
           "headers": list(headers), "sources": list(sources), "allsources": list(allsources), "shared": shared,
           "static": static, "profile": profile, "extra_flags": extra_flags, "linker_flags": linker_flags,
           "exclude_dirs": list(exclude_dirs), "exclude_files": list(exclude_files), "output_dir_set": output_dir_set,
           "obj_dir_set": obj_dir_set, "debug_set": debug_set, "opt_set": opt_set, "errors": list(errors),
           "warnings": list(warnings), "allpaths": list(allpaths),
           "chunks": list(chunks), "use_chunks": use_chunks, "chunk_tolerance": chunk_tolerance,
           "chunk_size": chunk_size, "chunk_filesize": chunk_filesize, "chunk_size_tolerance": chunk_size_tolerance,
           "header_recursion": header_recursion, "ignore_external_headers": ignore_external_headers,
           "default_target": default_target, "chunk_precompile": chunk_precompile, "precompile": list(precompile),
           "precompile_exclude": list(precompile_exclude), "headerfile": headerfile, "unity": unity,
           "precompile_done": precompile_done, "no_warnings": no_warnings, "compiler_model": compiler_model, "cmd": cmd,
           "recompile_all": recompile_all, "targets": dict(targets), "targetName": targetName,
           "final_chunk_set": list(final_chunk_set),
           "needs_precompile": needs_precompile, "compiles_completed": compiles_completed,
           "compile_failed": compile_failed,
           "copy": copy}

    return ret

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

import fnmatch
import os
import re
import hashlib
import subprocess
import threading
import time
import sys
import math
import datetime
import platform
import glob
import itertools

from csbuild import log
from csbuild import _shared_globals
from csbuild import _utils

class projectSettings(object):
    def __init__(self, setupDict=True):
        if not setupDict:
            return
        
        self.name = ""
        self.workingDirectory = "./"
        self.linkDepends = []
        self.srcDepends = []
        self.func = None

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
        self.cxxpccmd = ""  # return value of get_base_cxx_precompile_command
        self.ccpccmd = ""  # return value of get_base_cc_precompile_command

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

    def prepareBuild(self):
        wd = os.getcwd()
        os.chdir(self.workingDirectory)

        self.activeToolchain = self.toolchains[self.activeToolchainName]
        self.obj_dir = os.path.abspath(self.obj_dir)
        self.output_dir = os.path.abspath(self.output_dir)
        self.csbuild_dir = os.path.abspath(self.csbuild_dir)

        self.exclude_dirs.append(self.csbuild_dir)

        projectSettings.currentProject = self

        if self.ext is None:
            self.ext = self.activeToolchain.get_default_extension(self.type)

        self.output_name += self.ext
        log.LOG_BUILD("Preparing build tasks for {}...".format(self.output_name))

        if not os.path.exists(self.csbuild_dir):
            os.makedirs(self.csbuild_dir)

        self.cccmd = self.activeToolchain.get_base_cc_command(self)
        self.cxxcmd = self.activeToolchain.get_base_cxx_command(self)
        self.ccpccmd = self.activeToolchain.get_base_cc_precompile_command(self)
        self.cxxpccmd = self.activeToolchain.get_base_cxx_precompile_command(self)

        cmdfile = "{0}/{1}.csbuild".format(self.csbuild_dir, self.targetName)
        cmd = ""
        if os.path.exists(cmdfile):
            with open(cmdfile, "r") as f:
                cmd = f.read()

        if self.cxxcmd + self.cccmd != cmd:
            self.recompile_all = True
            with open(cmdfile, "w") as f:
                f.write(self.cxxcmd + self.cccmd)

        if not self.chunks:
            self.get_files(self.allsources)

            if not self.allsources:
                return

            #We'll do this even if _use_chunks is false, because it simplifies the linker logic.
            self.chunks = self.make_chunks(self.allsources)
        else:
            self.allsources = list(itertools.chain(*self.chunks))

        if not _shared_globals.CleanBuild and not _shared_globals.do_install:
            for source in self.allsources:
                if self.should_recompile(source):
                    self.sources.append(source)
        else:
            self.sources = list(self.allsources)

        _shared_globals.allfiles += self.sources

        os.chdir(wd)        


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
            "name": self.name,
            "workingDirectory": self.workingDirectory,
            "linkDepends": list(self.linkDepends),
            "srcDepends": list(self.srcDepends),
            "func": self.func,
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


    def get_files(self, sources=None, headers=None):
        """
        Steps through the current directory tree and finds all of the source and header files, and returns them as a list.
        Accepts two lists as arguments, which it populates. If sources or headers are excluded from the parameters, it will
        ignore files of the relevant types.
        """

        exclude_files = set()
        exclude_dirs = set()

        for exclude in self.exclude_files:
            exclude_files |= set(glob.glob(exclude))

        for exclude in self.exclude_dirs:
            exclude_dirs |= set(glob.glob(exclude))

        for root, dirnames, filenames in os.walk('.'):
            absroot = os.path.abspath(root)
            if absroot in exclude_dirs:
                if absroot != self.csbuild_dir:
                    log.LOG_INFO("Skipping dir {0}".format(root))
                continue
            if absroot == self.csbuild_dir or absroot.startswith(self.csbuild_dir):
                continue
            bFound = False
            for testDir in exclude_dirs:
                if absroot.startswith(testDir):
                    bFound = True
                    break
            if bFound:
                if not absroot.startswith(self.csbuild_dir):
                    log.LOG_INFO("Skipping dir {0}".format(root))
                continue
            log.LOG_INFO("Looking in directory {0}".format(root))
            if sources is not None:
                for filename in fnmatch.filter(filenames, '*.cpp'):
                    path = os.path.join(absroot, filename)
                    if path not in exclude_files:
                        sources.append(os.path.abspath(path))
                        self.hasCppFiles = True
                for filename in fnmatch.filter(filenames, '*.c'):
                    path = os.path.join(absroot, filename)
                    if path not in exclude_files:
                        sources.append(os.path.abspath(path))

                sources.sort(key=str.lower)

            if headers is not None:
                for filename in fnmatch.filter(filenames, '*.hpp'):
                    path = os.path.join(absroot, filename)
                    if path not in exclude_files:
                        headers.append(os.path.abspath(path))
                        self.hasCppFiles = True
                for filename in fnmatch.filter(filenames, '*.h'):
                    path = os.path.join(absroot, filename)
                    if path not in exclude_files:
                        headers.append(os.path.abspath(path))
                for filename in fnmatch.filter(filenames, '*.inl'):
                    path = os.path.join(absroot, filename)
                    if path not in exclude_files:
                        headers.append(os.path.abspath(path))

                headers.sort(key=str.lower)


    def get_full_path(self, headerFile):
        if os.path.exists(headerFile):
            path = headerFile
        else:
            path = "{0}/{1}".format(os.path.dirname(headerFile), headerFile)
            if not os.path.exists(path):
                for incDir in self.include_dirs:
                    path = "{0}/{1}".format(incDir, headerFile)
                    if os.path.exists(path):
                        break
                        #A lot of standard C and C++ headers will be in a compiler-specific directory that we won't
                        # check.
                        #Just ignore them to speed things up.
            if not os.path.exists(path):
                return ""

        return path


    def get_included_files(self, headerFile):
        headers = []
        if sys.version_info >= (3, 0):
            f = open(headerFile, encoding="latin-1")
        else:
            f = open(headerFile)
        with f:
            for line in f:
                if line[0] != '#':
                    continue

                RMatch = re.search("#include\s*[<\"](.*?)[\">]", line)
                if RMatch is None:
                    continue

                if "." not in RMatch.group(1):
                    continue

                headers.append(RMatch.group(1))

        return headers


    def follow_headers(self, headerFile, allheaders):
        """Follow the headers in a file.
        First, this will check to see if the given header has been followed already.
        If it has, it pulls the list from the allheaders global dictionary and returns it.
        If not, it populates a new allheaders list with follow_headers2, and then adds
        that to the allheaders dictionary
        """
        headers = []

        if not headerFile:
            return

        path = self.get_full_path(headerFile)

        if not path:
            return

        if path in _shared_globals.allheaders:
            allheaders += _shared_globals.allheaders[path]
            return

        headers = self.get_included_files(path)

        for header in headers:

            #Find the header in the listed includes.
            path = self.get_full_path(header)

            if self.ignore_external_headers and not path.startswith(self.workingDirectory):
                continue

            #If we've already looked at this header (i.e., it was included twice) just ignore it
            if path in allheaders:
                continue

            if path in _shared_globals.allheaders:
                continue

            allheaders.append(path)

            theseheaders = set()

            if self.header_recursion != 1:
                #Check to see if we've already followed this header.
                #If we have, the list we created from it is already stored in _allheaders under this header's key.
                try:
                    allheaders += _shared_globals.allheaders[path]
                except KeyError:
                    pass
                else:
                    continue

                self.follow_headers2(path, theseheaders, 1)

            _shared_globals.allheaders.update({path: theseheaders})
            allheaders += theseheaders


    def follow_headers2(self, headerFile, allheaders, n):
        """More intensive, recursive, and cpu-hogging function to follow a header.
        Only executed the first time we see a given header; after that the information is cached."""
        headers = []

        if not headerFile:
            return

        path = self.get_full_path(headerFile)

        if not path:
            return

        if path in _shared_globals.allheaders:
            allheaders += _shared_globals.allheaders[path]
            return

        headers = self.get_included_files(path)

        for header in headers:
            path = self.get_full_path(header)

            if self.ignore_external_headers and not path.startswith(self.workingDirectory):
                continue

                #Check to see if we've already followed this header.
            #If we have, the list we created from it is already stored in _allheaders under this header's key.
            if path in allheaders:
                continue

            if path in _shared_globals.allheaders:
                continue

            allheaders.add(path)

            theseheaders = set(allheaders)

            if self.header_recursion == 0 or n < self.header_recursion:
                #Check to see if we've already followed this header.
                #If we have, the list we created from it is already stored in _allheaders under this header's key.
                try:
                    allheaders |= _shared_globals.allheaders[path]
                except KeyError:
                    pass
                else:
                    continue

                self.follow_headers2(path, theseheaders, n + 1)

            _shared_globals.allheaders.update({path: theseheaders})
            allheaders |= theseheaders

    def should_recompile(self, srcFile, ofile=None, for_precompiled_header=False):
        """Checks various properties of a file to determine whether or not it needs to be recompiled."""

        log.LOG_INFO("Checking whether to recompile {0}...".format(srcFile))

        if self.recompile_all:
            log.LOG_INFO(
                "Going to recompile {0} because settings have changed in the makefile that will impact output.".format(
                    srcFile))
            return True

        basename = os.path.basename(srcFile).split('.')[0]
        if not ofile:
            ofile = "{0}/{1}_{2}.o".format(self.obj_dir, basename,
                self.targetName)

        if self.use_chunks:
            chunk = self.get_chunk(srcFile)
            chunkfile = "{0}/{1}_{2}.o".format(self.obj_dir, chunk,
                self.targetName)

            #First check: If the object file doesn't exist, we obviously have to create it.
            if not os.path.exists(ofile):
                ofile = chunkfile

        if not os.path.exists(ofile):
            log.LOG_INFO(
                "Going to recompile {0} because the associated object file does not exist.".format(srcFile))
            return True

        #Third check: modified time.
        #If the source file is newer than the object file, we assume it's been changed and needs to recompile.
        mtime = os.path.getmtime(srcFile)
        omtime = os.path.getmtime(ofile)

        if mtime > omtime:
            if for_precompiled_header:
                log.LOG_INFO(
                    "Going to recompile {0} because it has been modified since the last successful build.".format(
                        srcFile))
                return True

            oldmd5 = 1
            newmd5 = 9

            try:
                newmd5 = _shared_globals.newmd5s[srcFile]
            except KeyError:
                with open(srcFile, "r") as f:
                    newmd5 = _utils.get_md5(f)
                _shared_globals.newmd5s.update({srcFile: newmd5})

            md5file = "{0}/md5s/{1}.md5".format(self.csbuild_dir,
                os.path.abspath(srcFile))

            if os.path.exists(md5file):
                try:
                    oldmd5 = _shared_globals.oldmd5s[md5file]
                except KeyError:
                    with open(md5file, "rb") as f:
                        oldmd5 = f.read()
                    _shared_globals.oldmd5s.update({md5file: oldmd5})

            if oldmd5 != newmd5:
                log.LOG_INFO(
                    "Going to recompile {0} because it has been modified since the last successful build.".format(
                        
                        srcFile))
                return True

        #Fourth check: Header files
        #If any included header file (recursive, to include headers included by headers) has been changed,
        #then we need to recompile every source that includes that header.
        #Follow the headers for this source file and find out if any have been changed o necessitate a recompile.
        headers = []

        self.follow_headers(srcFile, headers)

        updatedheaders = []

        for header in headers:
            if os.path.exists(header):
                path = header
            else:
                continue

            header_mtime = os.path.getmtime(path)

            if header_mtime > omtime:
                if for_precompiled_header:
                    updatedheaders.append([header, path])
                    continue

                #newmd5 is 0, oldmd5 is 1, so that they won't report equal if we ignore them.
                newmd5 = 0
                oldmd5 = 1

                md5file = "{0}/md5s/{1}.md5".format(self.csbuild_dir,
                    os.path.abspath(path))

                if os.path.exists(md5file):
                    try:
                        newmd5 = _shared_globals.newmd5s[path]
                    except KeyError:
                        if sys.version_info >= (3, 0):
                            f = open(path, encoding="latin-1")
                        else:
                            f = open(path)
                        with f:
                            newmd5 = _utils.get_md5(f)
                        _shared_globals.newmd5s.update({path: newmd5})
                    if os.path.exists(md5file):
                        try:
                            oldmd5 = _shared_globals.oldmd5s[md5file]
                        except KeyError:
                            with open(md5file, "rb") as f:
                                oldmd5 = f.read()
                            _shared_globals.oldmd5s.update({md5file: oldmd5})

                if oldmd5 != newmd5:
                    updatedheaders.append([header, path])

        if updatedheaders:
            files = []
            for pair in updatedheaders:
                files.append(pair[0])
                path = pair[1]
                if path not in self.allpaths:
                    self.allpaths.append(path)
            log.LOG_INFO(
                "Going to recompile {0} because included headers {1} have been modified since the last successful build."
                .format(
                    srcFile, files))
            return True

        #If we got here, we assume the object file's already up to date.
        log.LOG_INFO("Skipping {0}: Already up to date".format(srcFile))
        return False


    def check_libraries(self):
        """Checks the libraries designated by the make script.
        Invokes ld to determine whether or not the library exists.1
        Uses the -t flag to get its location.
        And then stores the library's last modified time to a global list to be used by the linker later, to determine
        whether or not a project with up-to-date objects still needs to link against new libraries.
        """
        log.LOG_INFO("Checking required libraries...")

        def check_libraries(libraries, force_static, force_shared):
            libraries_ok = True
            for library in libraries:
                bFound = False
                for depend in self.linkDepends:
                    if _shared_globals.projects[depend].output_name == library or \
                            _shared_globals.projects[depend].output_name.startswith(
                                    "lib{}".format(library)):
                        bFound = True
                        break
                if bFound:
                    continue

                log.LOG_INFO("Looking for lib{0}...".format(library))
                lib = self.activeToolchain.find_library(library, self.library_dirs,
                    force_static, force_shared)
                if lib:
                    mtime = os.path.getmtime(lib)
                    log.LOG_INFO("Found library lib{0} at {1}".format(library, lib))
                    _shared_globals.library_mtimes.append(mtime)
                else:
                    log.LOG_ERROR("Could not locate library: {0}".format(library))
                    libraries_ok = False
            return libraries_ok

        libraries_ok = check_libraries(self.libraries, False, False)
        libraries_ok = check_libraries(self.static_libraries, True, False) and libraries_ok
        libraries_ok = check_libraries(self.shared_libraries, False, True) and libraries_ok
        if not libraries_ok:
            log.LOG_ERROR("Some dependencies are not met on your system.")
            log.LOG_ERROR("Check that all required libraries are installed.")
            log.LOG_ERROR(
                "If they are installed, ensure that the path is included in the makefile (use csbuild.LibDirs() to set "
                "them)")
            return False
        log.LOG_INFO("Libraries OK!")
        return True

    def make_chunks(self, l):
        """ Converts the list into a list of lists - i.e., "chunks"
        Each chunk represents one compilation unit in the chunked build system.
        """
        sorted_list = sorted(l, key=os.path.getsize, reverse=True)
        if self.unity or not self.use_chunks:
            return [l]
        chunks = []
        if self.chunk_filesize > 0:
            chunksize = 0
            chunk = []
            while sorted_list:
                chunksize = 0
                chunk = [sorted_list[0]]
                chunksize += os.path.getsize(sorted_list[0])
                sorted_list.pop(0)
                for srcFile in reversed(sorted_list):
                    filesize = os.path.getsize(srcFile)
                    if chunksize + filesize > self.chunk_filesize:
                        chunks.append(chunk)
                        log.LOG_INFO("Made chunk: {0}".format(chunk))
                        log.LOG_INFO("Chunk size: {0}".format(chunksize))
                        break
                    else:
                        chunk.append(srcFile)
                        chunksize += filesize
                        sorted_list.pop()
            chunks.append(chunk)
            log.LOG_INFO("Made chunk: {0}".format(chunk))
            log.LOG_INFO("Chunk size: {0}".format(chunksize))
        elif self.chunk_size > 0:
            for i in range(0, len(l), self.chunk_size):
                chunks.append(l[i:i + self.chunk_size])
        else:
            return [l]
        return chunks


    def get_chunk(self, srcFile):
        """Retrieves the chunk that a given file belongs to."""
        for chunk in self.chunks:
            if srcFile in chunk:
                return "{0}_chunk_{1}".format(self.output_name.split('.')[0],
                    "__".join(_utils.base_names(chunk)))


    def save_md5(self, inFile):
        tempInFile = os.path.abspath(inFile)

        # If we're running on Windows, we need to remove the drive letter from the input file path.
        if platform.system() == "Windows":
            tempInFile = tempInFile[2:]

        md5file = "{}{}".format(self.csbuild_dir,
            os.path.join(os.path.sep, "md5s", tempInFile))

        md5dir = os.path.dirname(md5file)
        if not os.path.exists(md5dir):
            os.makedirs(md5dir)
        newmd5 = ""
        try:
            newmd5 = _shared_globals.newmd5s[inFile]
        except KeyError:
            if sys.version_info >= (3, 0):
                f = open(inFile, encoding="latin-1")
            else:
                f = open(inFile)
            with f:
                newmd5 = _utils.get_md5(f)
        finally:
            with open(md5file, "wb") as f:
                f.write(newmd5)


    def save_md5s(self, sources, headers):
        for source in sources:
            self.save_md5(source)

        for header in headers:
            self.save_md5(header)

        for path in self.allpaths:
            self.save_md5(os.path.abspath(path))


    def precompile_headers(self):
        if not self.needs_c_precompile and not self.needs_cpp_precompile:
            return True

        starttime = time.time()
        log.LOG_BUILD("Precompiling headers...")

        _shared_globals.built_something = True

        if not os.path.exists(self.obj_dir):
            os.makedirs(self.obj_dir)

        thread = None
        cthread = None
        cppobj = ""
        cobj = ""
        if self.needs_cpp_precompile:
            if not _shared_globals.semaphore.acquire(False):
                if _shared_globals.max_threads != 1:
                    log.LOG_INFO("Waiting for a build thread to become available...")
                _shared_globals.semaphore.acquire(True)
            if _shared_globals.interrupted:
                sys.exit(2)

            log.LOG_BUILD(
                "Precompiling {0} ({1}/{2})...".format(
                    self.cppheaderfile,
                    _shared_globals.current_compile,
                    _shared_globals.total_compiles))

            _shared_globals.current_compile += 1

            cppobj = self.activeToolchain.get_pch_file(self.cppheaderfile)

            #precompiled headers block on current thread - run runs on current thread rather than starting a new one
            thread = _utils.threaded_build(self.cppheaderfile, cppobj, self, True)
            thread.start()

        if self.needs_c_precompile:
            if not _shared_globals.semaphore.acquire(False):
                if _shared_globals.max_threads != 1:
                    log.LOG_INFO("Waiting for a build thread to become available...")
                _shared_globals.semaphore.acquire(True)
            if _shared_globals.interrupted:
                sys.exit(2)

            log.LOG_BUILD(
                "Precompiling {0} ({1}/{2})...".format(
                    self.cheaderfile,
                    _shared_globals.current_compile,
                    _shared_globals.total_compiles))

            _shared_globals.current_compile += 1

            cobj = self.activeToolchain.get_pch_file(self.cheaderfile)

            #precompiled headers block on current thread - run runs on current thread rather than starting a new one
            cthread = _utils.threaded_build(self.cheaderfile, cobj, self, True)
            cthread.start()

        if thread:
            thread.join()
            _shared_globals.precompiles_done += 1
        if cthread:
            cthread.join()
            _shared_globals.precompiles_done += 1

        totaltime = time.time() - starttime
        totalmin = math.floor(totaltime / 60)
        totalsec = round(totaltime % 60)
        log.LOG_BUILD("Precompile took {0}:{1:02}".format(int(totalmin), int(totalsec)))

        self.precompile_done = True

        return not self.compile_failed


currentProject = projectSettings()

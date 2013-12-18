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

"""
csbuild.py
Python-powered build utility for C and C++
Uses advanced techniques to reduce build time to a minimum, while attempting to always ensure that  the correct build
operations are performed every time without need of a clean operation. Eliminates redundant and unnecessary build
operations, and incorporates the Unity Build concept for larger builds to speed up project compilation, while avoiding
it for smaller build operations to speed up iteration.

See www.github.net/ShadauxCat/csbuild for more information and documentation.
"""

import argparse
import shutil
import signal
import itertools
import math
import subprocess
import os
import sys
import time

from csbuild import _utils
from csbuild import log
from csbuild import _shared_globals
from csbuild import projectSettings

__author__ = 'Jaedyn K Draper'
__copyright__ = 'Copyright (C) 2013 Jaedyn K Draper'
__license__ = 'MIT'
__version__ = '1.0.0'

__all__ = []

signal.signal(signal.SIGINT, signal.SIG_DFL)

#TODO: Specify number of jobs (in code and on command line)
#TODO: Specify C compiler or C++ compiler for precompiled headers
#TODO: -stdlib

#TODO: Verify compiler features
#TODO: Mark scripts uncallable
#TODO: csbuild.ScriptLocation()?


#<editor-fold desc="Setters">
#Setters
def NoBuiltinTargets():
    if projectSettings.targets["debug"] == debug:
        del projectSettings.targets["debug"]
    if projectSettings.targets["release"] == release:
        del projectSettings.targets["release"]

def InstallOutput(s="lib"):
    """Enables installation of the compiled output file. Default target is /usr/local/lib."""
    projectSettings.output_install_dir = s


def InstallHeaders(s="include"):
    """Enables installation of the project's headers. Default target is /usr/local/include."""
    projectSettings.header_install_dir = s


def InstallSubdir(s):
    projectSettings.header_subdir = s


def ExcludeDirs(*args):
    """Excludes the given subdirectories from the build. Accepts multiple string arguments."""
    args = list(args)
    newargs = []
    for arg in args:
        if arg[0] != '/' and not arg.startswith("./"):
            arg = "./" + arg
        newargs.append(os.path.abspath(arg))
    projectSettings.exclude_dirs += newargs


def ExcludeFiles(*args):
    """Excludes the given files from the build. Accepts multiple string arguments."""
    args = list(args)
    newargs = []
    for arg in args:
        if arg[0] != '/' and not arg.startswith("./"):
            arg = "./" + arg
        newargs.append(os.path.abspath(arg))
    projectSettings.exclude_files += newargs


def Libraries(*args):
    """List of libraries to link against. Multiple string arguments. gcc/g++ -l."""
    projectSettings.libraries += list(args)


def StaticLibraries(*args):
    """List of libraries to link statically against. Multiple string arguments. gcc/g++ -l."""
    projectSettings.static_libraries += list(args)


def IncludeDirs(*args):
    """List of directories to search for included headers. Multiple string arguments. gcc/g++ -I
    By default, this list contains /usr/include and /usr/local/include.
    Using this function will add to the existing list, not replace it.
    """
    for arg in args:
        arg = os.path.abspath(arg)
        if not os.path.exists(arg):
            log.LOG_ERROR("Include path {0} does not exist! Aborting!".format(arg))
            sys.exit(1)
        projectSettings.include_dirs.append(arg)


def LibDirs(*args):
    """List of directories to search for libraries. Multiple string arguments. gcc/g++ -L
    By default, this list contains /usr/lib and /usr/local/lib
    Using this function will add to the existing list, not replace it"""
    for arg in args:
        arg = os.path.abspath(arg)
        if not os.path.exists(arg):
            log.LOG_ERROR("Library path {0} does not exist! Aborting!".format(arg))
            sys.exit(1)
        projectSettings.library_dirs.append(arg)


def ClearLibraries():
    """Clears the list of libraries"""
    projectSettings.libraries = []


def ClearStaticLibraries():
    """Clears the list of libraries"""
    projectSettings.static_libraries = []


def ClearIncludeDirs():
    """Clears the include directories, including the defaults."""
    projectSettings.include_dirs = []


def ClearLibDirs():
    """Clears the library directories, including the defaults"""
    projectSettings.library_dirs = []


def Opt(i):
    """Sets the optimization level. gcc/g++ -O"""
    projectSettings.opt_level = i
    projectSettings.opt_set = True


def Debug(i):
    """Sets the debug level. gcc/g++ -g"""
    projectSettings.debug_level = i
    projectSettings.debug_set = True


def Define(*args):
    """Sets defines for the project. Accepts multiple arguments. gcc/g++ -D"""
    projectSettings.defines += list(args)


def ClearDefines():
    """clears the list of defines"""
    projectSettings.defines = []


def Undefine(*args):
    """Sets undefines for the project. Multiple arguments. gcc/g++ -U"""
    projectSettings.undefines += list(args)


def ClearUndefines():
    """clears the list of undefines"""
    projectSettings.undefines = []


def CppCompiler(s):
    """Sets the compiler to use for the project. Default is g++"""
    projectSettings.cxx = s


def CCompiler(s):
    """Sets the compiler to use for the project. Default is gcc"""
    projectSettings.cc = s


def Output(s):
    """Sets the output file for the project. If unset, the project will be compiled as "a.out"""""
    projectSettings.output_name = s


def OutDir(s):
    """Sets the directory to place the compiled result"""
    projectSettings.output_dir = os.path.abspath(s)
    projectSettings.output_dir_set = True


def ObjDir(s):
    """Sets the directory to place pre-link objects"""
    projectSettings.obj_dir = os.path.abspath(s)
    projectSettings.obj_dir_set = True


def WarnFlags(*args):
    """Sets warn flags for the project. Multiple arguments. gcc/g++ -W"""
    projectSettings.warn_flags += list(args)


def ClearWarnFlags():
    """Clears the list of warning flags"""
    projectSettings.warn_flags = []


def Flags(*args):
    """Sets miscellaneous flags for the project. Multiple arguments. gcc/g++ -f"""
    projectSettings.flags += list(args)


def ClearFlags():
    """Clears the list of misc flags"""
    projectSettings.flags = []


def DisableAutoMake():
    """Disables the automatic build of the project at conclusion of the script
    If you turn this off, you will need to explicitly call either make() to build and link,
    or build() and link() to take each step individually
    """
    projectSettings.automake = False


def EnableAutoMake():
    """Turns the automatic build back on after disabling it"""
    projectSettings.automake = True


def Shared():
    """Builds the project as a shared library. Enables -shared in the linker and -fPIC in the compiler."""
    projectSettings.shared = True
    projectSettings.static = False


def NotShared():
    """Turns shared object mode back off after it was enabled."""
    projectSettings.shared = False


def Static():
    """Builds the project as a shared library. Enables -shared in the linker and -fPIC in the compiler."""
    projectSettings.static = True
    projectSettings.shared = False


def NotStatic():
    """Turns shared object mode back off after it was enabled."""
    projectSettings.static = False


def EnableProfile():
    """Enables profiling optimizations. gcc/g++ -pg"""
    projectSettings.profile = True


def DisableProfile():
    """Turns profiling back off."""
    projectSettings.profile = False


def ExtraFlags(s):
    """Literal string of extra flags to be passed directly to the compiler"""
    projectSettings.extra_flags = s


def ClearExtraFlags():
    """Clears the extra flags string"""
    projectSettings.extra_flags = ""


def LinkerFlags(s):
    """Literal string of extra flags to be passed directly to the linker"""
    projectSettings.linker_flags = s


def ClearLinkerFlags():
    """Clears the linker flags string"""
    projectSettings.linker_flags = ""


def CppStandard(s):
    """The C/C++ standard to be used when compiling. gcc/g++ --std"""
    projectSettings.cppstandard = s


def CStandard(s):
    """The C/C++ standard to be used when compiling. gcc/g++ --std"""
    projectSettings.cstandard = s


def DisableChunkedBuild():
    """Turn off the chunked/unity build system and build using individual files."""
    projectSettings.use_chunks = False


def EnableChunkedBuild():
    """Turn chunked/unity build on and build using larger compilation units. This is the default."""
    projectSettings.use_chunks = True


def ChunkNumFiles(i):
    """Set the size of the chunks used in the chunked build. This indicates the number of files per compilation unit.
    The default is 10.
    This value is ignored if SetChunks is called.
    Mutually exclusive with ChunkFilesize().
    """
    projectSettings.chunk_size = i
    projectSettings.chunk_filesize = 0


def ChunkFilesize(i):
    """Sets the maximum filesize for a chunk. The default is 500000. This value is ignored if SetChunks is called.
    Mutually exclusive with ChunkNumFiles()
    """
    projectSettings.chunk_filesize = i
    projectSettings.chunk_size = i


def ChunkTolerance(i):
    """Set the number of files above which the files will be built as a chunk.
    For example, if you set this to 3 (the default), then a chunk will be built as a chunk
    if more than three of its files need to be built; if three or less need to be built, they will
    be built individually to save build time.
    """
    if projectSettings.chunk_filesize > 0:
        projectSettings.chunk_size_tolerance = i
    elif projectSettings.chunk_size > 0:
        projectSettings.chunk_tolerance = i
    else:
        log.LOG_WARN("Chunk size and chunk filesize are both zero or negative, cannot set a tolerance.")


def SetChunks(*chunks):
    """Explicitly set the chunks used as compilation units.
    This accepts multiple arguments, each of which should be a list of files.
    Each list is one chunk.
    NOTE that setting this will disable the automatic file gathering, so any files you have
    """
    chunks = list(chunks)
    projectSettings.chunks = chunks


def ClearChunks():
    """Clears the explicitly set list of chunks and returns the behavior to the default."""
    projectSettings.chunks = []


def HeaderRecursionLevel(i):
    """Sets the depth to search for header files. If set to 0, it will search with unlimited recursion to find included
    headers. Otherwise, it will travel to a depth of i to check headers. If set to 1, this will only check first-level
    headers and not check headers included in other headers; if set to 2, this will check headers included in headers,
    but not headers included by *those* headers; etc.

    This is very useful if you're using a large library (such as boost) or a very large project and are experiencing
    long waits prior to compilation.
    """
    projectSettings.header_recursion = i


def IgnoreExternalHeaders():
    """If this option is set, external headers will not be checked or followed when building. Only headers within the
    base project's directory and its subdirectories will be checked. This will speed up header checking, but if you
    modify any external headers, you will need to manually --clean the project.
    """
    projectSettings.ignore_external_headers = True


def DisableWarnings():
    """Disables ALL warnings, including gcc/g++'s built-in warnings."""
    projectSettings.no_warnings = True


def DefaultTarget(s):
    """Sets the default target if none is specified. The default value for this is release."""
    projectSettings.default_target = s.lower()


def Precompile(*args):
    """Explicit list of header files to precompile. Disables chunk precompile when called."""
    projectSettings.precompile = []
    for arg in list(args):
        projectSettings.precompile.append(os.path.abspath(arg))
    projectSettings.chunk_precompile = False


def PrecompileAsC(*args):
    projectSettings.cheaders = []
    for arg in list(args):
        projectSettings.cheaders.append(os.path.abspath(arg))


def ChunkPrecompile():
    """When this is enabled, all header files will be precompiled into a single "superheader" and included in all
    files."""
    projectSettings.chunk_precompile = True


def NoPrecompile(*args):
    """Disables precompilation and handles headers as usual."""
    args = list(args)
    if args:
        newargs = []
        for arg in args:
            if arg[0] != '/' and not arg.startswith("./"):
                arg = "./" + arg
            newargs.append(arg)
            projectSettings.precompile_exclude += newargs
    else:
        projectSettings.chunk_precompile = False


def EnableUnity():
    """Turns on true unity builds, combining all files into only one compilation unit."""
    projectSettings.unity = True


def StaticRuntime():
    projectSettings.static_runtime = True


def SharedRuntime():
    projectSettings.static_runtime = False


def DebugRuntime():
    projectSettings.debug_runtime = True


def ReleaseRuntime():
    projectSettings.debug_runtime = False


def Force32Bit():
    projectSettings.force_32_bit = True
    projectSettings.force_64_bit = False


def Force64Bit():
    projectSettings.force_64_bit = True
    projectSettings.force_32_bit = False

#</editor-fold>

#<editor-fold desc="decorators">


def project(name, workingDirectory, linkDepends=None, srcDepends=None):
    if not linkDepends:
        linkDepends = []
    if not srcDepends:
        srcDepends = []
    if isinstance(linkDepends, str):
        linkDepends = [linkDepends]
    if isinstance(srcDepends, str):
        srcDepends = [srcDepends]

    class projectData(object):
        def __init__(self, name, workingDirectory, linkDepends, srcDepends, func, globalDict):
            self.name = name
            self.workingDirectory = os.path.abspath(workingDirectory)
            self.linkDepends = linkDepends
            self.srcDepends = srcDepends
            self.func = func
            self.globalDict = globalDict

        def prepareBuild(self):
            wd = os.getcwd()
            os.chdir(self.workingDirectory)

            self.globalDict.obj_dir = os.path.abspath(self.globalDict.obj_dir)
            self.globalDict.output_dir = os.path.abspath(self.globalDict.output_dir)
            self.globalDict.csbuild_dir = os.path.abspath(self.globalDict.csbuild_dir)

            self.globalDict.exclude_dirs.append(self.globalDict.csbuild_dir)

            projectSettings.__dict__.update(self.globalDict.__dict__)

            log.LOG_BUILD("Preparing build tasks for {}...".format(self.globalDict.output_name))

            if not os.path.exists(self.globalDict.csbuild_dir):
                os.makedirs(self.globalDict.csbuild_dir)

            self.globalDict.cccmd = self.globalDict.compiler_model.get_base_cc_command(self)
            self.globalDict.cxxcmd = self.globalDict.compiler_model.get_base_cxx_command(self)

            cmdfile = "{0}/{1}.csbuild".format(self.globalDict.csbuild_dir, self.globalDict.targetName)
            cmd = ""
            if os.path.exists(cmdfile):
                with open(cmdfile, "r") as f:
                    cmd = f.read()

            if self.globalDict.cxxcmd + self.globalDict.cccmd != cmd:
                self.globalDict.recompile_all = True
                clean(True)
                with open(cmdfile, "w") as f:
                    f.write(self.globalDict.cxxcmd + self.globalDict.cccmd)

            if not self.globalDict.chunks:
                _utils.get_files(self, self.globalDict.allsources)

                if not self.globalDict.allsources:
                    return

                #We'll do this even if _use_chunks is false, because it simplifies the linker logic.
                self.globalDict.chunks = _utils.make_chunks(self.globalDict.allsources)
            else:
                self.globalDict.allsources = list(itertools.chain(*self.globalDict.chunks))

            if not _shared_globals.CleanBuild and not _shared_globals.do_install:
                for source in self.globalDict.allsources:
                    if _utils.should_recompile(source):
                        self.globalDict.sources.append(source)
            else:
                self.globalDict.sources = list(self.globalDict.allsources)

            _shared_globals.allfiles += self.globalDict.sources

            os.chdir(wd)

    def wrap(projectFunction):
        oldGlobals = projectSettings.copy()
        projectFunction()

        if _shared_globals.target:
            projectSettings.targetName = _shared_globals.target
        else:
            projectSettings.targetName = projectSettings.default_target

        projectSettings.targets[projectSettings.targetName]()

        projectGlobals = type("pseudomodule", (object,), projectSettings.copy())

        _shared_globals.projects.update({name: projectData(name, workingDirectory,
            linkDepends, srcDepends, projectFunction, projectGlobals)})

        projectSettings.__dict__.update(oldGlobals)
        return projectFunction

    return wrap


def target(name):
    def wrap(targetFunction):
        projectSettings.targets.update({name: targetFunction})
        return targetFunction

    return wrap

#</editor-fold>

_barWriter = log.bar_writer()

_shared_globals.starttime = time.time()


def build():
    """Build the project.
    This step handles:
    Checking library dependencies.
    Checking which files need to be built.
    And spawning a build thread for each one that does.
    """

    _barWriter.start()

    built = False
    _utils.chunked_build()
    _utils.prepare_precompiles()

    for project in _shared_globals.sortedProjects:
        _shared_globals.total_compiles += len(project.globalDict.final_chunk_set)

    _shared_globals.total_compiles += _shared_globals.total_precompiles
    _shared_globals.current_compile = 1

    projects_in_flight = set()
    projects_done = set()
    pending_links = set()
    pending_builds = _shared_globals.sortedProjects

    starttime = time.time()

    while pending_builds:
        theseBuilds = pending_builds
        pending_builds = []
        for project in theseBuilds:
            for depend in project.srcDepends:
                if depend not in projects_done:
                    pending_builds.append(project)
                    continue
            projects_in_flight.add(project)

            os.chdir(project.workingDirectory)

            projectSettings.__dict__.update(project.globalDict.__dict__)

            project.starttime = time.time()

            log.LOG_BUILD(
                "Preparing to build {0} ({1})".format(projectSettings.output_name, project.globalDict.targetName))

            if not _utils.check_libraries():
                continue

            log.LOG_BUILD("Building {0} ({1})".format(projectSettings.output_name, project.globalDict.targetName))

            if _utils.precompile_headers(project):
                _shared_globals.built_something = True

                if not os.path.exists(projectSettings.obj_dir):
                    os.makedirs(projectSettings.obj_dir)

                if projectSettings.precompile_done:
                    _shared_globals.current_compile += 1

                for chunk in projectSettings.final_chunk_set:
                    built = True
                    obj = "{0}/{1}_{2}.o".format(projectSettings.obj_dir, os.path.basename(chunk).split('.')[0],
                        project.globalDict.targetName)
                    if not _shared_globals.semaphore.acquire(False):
                        if _shared_globals.max_threads != 1:
                            log.LOG_THREAD("Waiting for a build thread to become available...")
                        _shared_globals.semaphore.acquire(True)

                    for otherProj in list(projects_in_flight):
                        if otherProj.globalDict.compiles_completed >= len(otherProj.globalDict.final_chunk_set) + int(
                                otherProj.globalDict.needs_c_precompile) + int(
                                otherProj.globalDict.needs_cpp_precompile):
                            totaltime = (time.time() - otherProj.starttime)
                            minutes = math.floor(totaltime / 60)
                            seconds = round(totaltime % 60)

                            log.LOG_BUILD(
                                "Compile of {0} took {1}:{2:02}".format(otherProj.globalDict.output_name, minutes,
                                    seconds))
                            projects_in_flight.remove(otherProj)
                            if otherProj.globalDict.compile_failed:
                                log.LOG_ERROR("Build of {0} failed! Finishing up non-dependent build tasks...".format(
                                    otherProj.globalDict.output_name))
                                continue

                            okToLink = True
                            if otherProj.linkDepends:
                                for depend in otherProj.linkDepends:
                                    if depend not in projects_done:
                                        okToLink = False
                                        break
                            if okToLink:
                                link(otherProj)
                                log.LOG_BUILD("Finished {0}".format(otherProj.globalDict.output_name))
                                projects_done.add(otherProj.name)
                            else:
                                log.LOG_LINKER(
                                    "Linking for {0} deferred until all dependencies have finished building...".format(
                                        otherProj.globalDict.output_name))
                                pending_links.add(otherProj)

                    for otherProj in list(pending_links):
                        okToLink = True
                        for depend in otherProj.linkDepends:
                            if depend not in projects_done:
                                okToLink = False
                                break
                        if okToLink:
                            link(otherProj)
                            log.LOG_BUILD("Finished {0}".format(otherProj.globalDict.output_name))
                            projects_done.add(otherProj.name)
                            pending_links.remove(otherProj)

                    if _shared_globals.interrupted:
                        sys.exit(2)
                    if _shared_globals.times:
                        totaltime = (time.time() - starttime)
                        _shared_globals.lastupdate = totaltime
                        minutes = math.floor(totaltime / 60)
                        seconds = round(totaltime % 60)
                        avgtime = sum(_shared_globals.times) / (len(_shared_globals.times))
                        esttime = totaltime + ((avgtime * (
                            _shared_globals.total_compiles - len(_shared_globals.times))) / _shared_globals.max_threads)
                        if esttime < totaltime:
                            esttime = totaltime
                            _shared_globals.esttime = esttime
                        estmin = math.floor(esttime / 60)
                        estsec = round(esttime % 60)
                        log.LOG_BUILD(
                            "Building {0}... ({1}/{2}) - {3}:{4:02}/{5}:{6:02}".format(obj,
                                _shared_globals.current_compile, _shared_globals.total_compiles, int(minutes),
                                int(seconds), int(estmin),
                                int(estsec)))
                    else:
                        totaltime = (time.time() - starttime)
                        minutes = math.floor(totaltime / 60)
                        seconds = round(totaltime % 60)
                        log.LOG_BUILD(
                            "Building {0}... ({1}/{2}) - {3}:{4:02}".format(obj, _shared_globals.current_compile,
                                _shared_globals.total_compiles, int(minutes), int(seconds)))
                    _utils.threaded_build(chunk, obj, project).start()
                    _shared_globals.current_compile += 1

        #Wait until all threads are finished. Simple way to do this is acquire the semaphore until it's out of
        # resources.
        for j in range(_shared_globals.max_threads):
            if not _shared_globals.semaphore.acquire(False):
                if _shared_globals.max_threads != 1:
                    if _shared_globals.times:
                        totaltime = (time.time() - starttime)
                        _shared_globals.lastupdate = totaltime
                        minutes = math.floor(totaltime / 60)
                        seconds = round(totaltime % 60)
                        avgtime = sum(_shared_globals.times) / (len(_shared_globals.times))
                        esttime = totaltime + ((avgtime * (_shared_globals.total_compiles - len(
                            _shared_globals.times))) / _shared_globals.max_threads)
                        if esttime < totaltime:
                            esttime = totaltime
                        estmin = math.floor(esttime / 60)
                        estsec = round(esttime % 60)
                        _shared_globals.esttime = esttime
                        log.LOG_THREAD(
                            "Waiting on {0} more build thread{1} to finish... ({2}:{3:02}/{4}:{5:02})".format(
                                _shared_globals.max_threads - j,
                                "s" if _shared_globals.max_threads - j != 1 else "", int(minutes),
                                int(seconds), int(estmin), int(estsec)))
                    else:
                        log.LOG_THREAD(
                            "Waiting on {0} more build thread{1} to finish...".format(
                                _shared_globals.max_threads - j,
                                "s" if _shared_globals.max_threads - j != 1 else ""))
                _shared_globals.semaphore.acquire(True)
                if _shared_globals.interrupted:
                    sys.exit(2)

        #Then immediately release all the semaphores once we've reclaimed them.
        #We're not using any more threads so we don't need them now.
        for j in range(_shared_globals.max_threads):
            _shared_globals.semaphore.release()

        for otherProj in list(projects_in_flight):
            if otherProj.globalDict.compiles_completed >= len(otherProj.globalDict.final_chunk_set) + int(
                    otherProj.globalDict.needs_c_precompile) + int(
                    otherProj.globalDict.needs_cpp_precompile):
                totaltime = (time.time() - otherProj.starttime)
                minutes = math.floor(totaltime / 60)
                seconds = round(totaltime % 60)

                log.LOG_BUILD(
                    "Compile of {0} took {1}:{2:02}".format(otherProj.globalDict.output_name, minutes, seconds))
                projects_in_flight.remove(otherProj)
                if otherProj.globalDict.compile_failed:
                    log.LOG_ERROR("Build of {0} failed! Finishing up non-dependent build tasks...".format(
                        otherProj.globalDict.output_name))
                    continue

                okToLink = True
                if otherProj.linkDepends:
                    for depend in otherProj.linkDepends:
                        if depend not in projects_done:
                            okToLink = False
                            break
                if okToLink:
                    link(otherProj)
                    log.LOG_BUILD("Finished {0}".format(otherProj.globalDict.output_name))
                    projects_done.add(otherProj.name)
                else:
                    log.LOG_LINKER("Linking for {0} deferred until all dependencies have finished building...".format(
                        otherProj.globalDict.output_name))
                    pending_links.add(otherProj)

        for otherProj in list(pending_links):
            okToLink = True
            for depend in otherProj.linkDepends:
                if depend not in projects_done:
                    okToLink = False
                    break
            if okToLink:
                link(otherProj)
                log.LOG_BUILD("Finished {0}".format(otherProj.globalDict.output_name))
                projects_done.add(otherProj.name)
                pending_links.remove(otherProj)

        if projects_in_flight:
            log.LOG_ERROR("Could not complete all projects. This is probably very bad and should never happen."
                          " Remaining projects: {0}".format(list(projects_in_flight)))
        if pending_links:
            log.LOG_ERROR("Could not link all projects. Do you have unmet dependencies in your makefile?"
                          " Remaining projects: {0}".format(list(pending_links)))

        compiletime = time.time() - starttime
        totalmin = math.floor(compiletime / 60)
        totalsec = round(compiletime % 60)
        log.LOG_BUILD("Compilation took {0}:{1:02}".format(int(totalmin), int(totalsec)))

        _utils.save_md5s(projectSettings.allsources, projectSettings.headers)
    if not built:
        log.LOG_BUILD("Nothing to build.")
    return _shared_globals.build_success


def link(project, *objs):
    """Linker:
    Links all the built files.
    Accepts an optional list of object files to link; if this list is not provided it will use the auto-generated
    list created by build()
    This function also checks (if nothing was built) the modified times of all the required libraries, to see if we need
    to relink anyway, even though nothing was compiled.
    """

    starttime = time.time()

    output = "{0}/{1}".format(project.globalDict.output_dir, project.globalDict.output_name)

    objs = list(objs)
    if not objs:
        for chunk in project.globalDict.chunks:
            if not project.globalDict.unity:
                obj = "{0}/{1}_chunk_{2}_{3}.o".format(project.globalDict.obj_dir,
                    project.globalDict.output_name.split('.')[0],
                    "__".join(_utils.base_names(chunk)), project.globalDict.targetName)
            else:
                obj = "{0}/{1}_unity_{2}.o".format(project.globalDict.obj_dir, project.globalDict.output_name,
                    project.globalDict.targetName)
            if project.globalDict.use_chunks and os.path.exists(obj):
                objs.append(obj)
            else:
                if type(chunk) == list:
                    for source in chunk:
                        obj = "{0}/{1}_{2}.o".format(project.globalDict.obj_dir, os.path.basename(source).split('.')[0],
                            project.globalDict.targetName)
                        if os.path.exists(obj):
                            objs.append(obj)
                        else:
                            log.LOG_ERROR(
                                "Some object files are missing. Either the build failed, or you haven't built yet.")
                            return False
                else:
                    obj = "{0}/{1}_{2}.o".format(project.globalDict.obj_dir, os.path.basename(chunk).split('.')[0],
                        project.globalDict.targetName)
                    if os.path.exists(obj):
                        objs.append(obj)
                    else:
                        log.LOG_ERROR(
                            "Some object files are missing. Either the build failed, or you haven't built yet.")
                        return False

    if not objs:
        return True

    if not _shared_globals.built_something:
        if os.path.exists(output):
            mtime = os.path.getmtime(output)
            for obj in objs:
                if os.path.getmtime(obj) > mtime:
                    #If the obj time is later, something got built in another run but never got linked...
                    #Maybe the linker failed last time.
                    #We should count that as having built something, because we do need to link.
                    #Otherwise, if the object time is earlier, there's a good chance that the existing
                    #output file was linked using a different target, so let's link it again to be safe.
                    _shared_globals.built_something = True
                    break

            #Even though we didn't build anything, we should verify all our libraries are up to date too.
            #If they're not, we need to relink.
            for i in range(len(_shared_globals.library_mtimes)):
                if _shared_globals.library_mtimes[i] > mtime:
                    log.LOG_LINKER(
                        "Library {0} has been modified since the last successful build. Relinking to new library."
                        .format(
                            project.globalDict.libraries[i]))
                    _shared_globals.built_something = True

            #Barring the two above cases, there's no point linking if the compiler did nothing.
            if not _shared_globals.built_something:
                if not _shared_globals.called_something:
                    log.LOG_LINKER("Nothing to link.")
                return True

    log.LOG_LINKER("Linking {0}...".format(output))

    if not os.path.exists(project.globalDict.output_dir):
        os.makedirs(project.globalDict.output_dir)

    #Remove the output file so we're not just clobbering it
    #If it gets clobbered while running it could cause BAD THINGS (tm)
    if os.path.exists(output):
        os.remove(output)

    cmd = project.globalDict.compiler_model.get_link_command(project, output, objs)
    if _shared_globals.show_commands:
        print(cmd)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        log.LOG_ERROR("Linking failed.")
        return False

    totaltime = time.time() - starttime
    totalmin = math.floor(totaltime / 60)
    totalsec = round(totaltime % 60)
    log.LOG_LINKER("Link time: {0}:{1:02}".format(int(totalmin), int(totalsec)))
    #if _buildtime >= 0:
    #    totaltime = totaltime + _buildtime
    #    totalmin = math.floor(totaltime / 60)
    #    totalsec = round(totaltime % 60)
    #    log.LOG_BUILD("Total build time: {0}:{1:02}".format(int(totalmin), int(totalsec)))
    return True


def clean(silent=False):
    """Cleans the project.
    Invoked with --clean.
    Deletes all of the object files to make sure they're rebuilt cleanly next run.
    Does NOT delete the actual compiled file.
    """
    for project in _shared_globals.sortedProjects:

        if not silent:
            log.LOG_BUILD("Cleaning {0} ({1})...".format(project.globalDict.output_name, project.globalDict.targetName))
        for source in project.globalDict.sources:
            obj = "{0}/{1}_{2}.o".format(project.globalDict.obj_dir, os.path.basename(source).split('.')[0],
                project.globalDict.targetName)
            if os.path.exists(obj):
                if not silent:
                    log.LOG_INFO("Deleting {0}".format(obj))
                os.remove(obj)
        headerfile = "{0}/{1}_cpp_precompiled_headers.hpp".format(project.globalDict.csbuild_dir,
            project.globalDict.output_name.split('.')[0])
        obj = "{0}/{1}_{2}.hpp.gch".format(os.path.dirname(headerfile), os.path.basename(headerfile).split('.')[0],
            project.globalDict.targetName)
        if os.path.exists(obj):
            if not silent:
                log.LOG_INFO("Deleting {0}".format(obj))
            os.remove(obj)

        headerfile = "{0}/{1}_c_precompiled_headers.h".format(project.globalDict.csbuild_dir,
            project.globalDict.output_name.split('.')[0])
        obj = "{0}/{1}_{2}.h.gch".format(os.path.dirname(headerfile), os.path.basename(headerfile).split('.')[0],
            project.globalDict.targetName)
        if os.path.exists(obj):
            if not silent:
                log.LOG_INFO("Deleting {0}".format(obj))
            os.remove(obj)

        if not silent:
            log.LOG_BUILD("Done.")


def install():
    """Installer.
    Invoked with --install.
    Installs the generated output file and/or header files to the specified directory.
    Does nothing if neither InstallHeaders() nor InstallOutput() has been called in the make script.
    """
    for project in _shared_globals.sortedProjects:
        output = "{0}/{1}".format(project.globalDict.output_dir, project.globalDict.output_name)
        install_something = False

        if not project.globalDict.output_install_dir or os.path.exists(output):
            #install output file
            if project.globalDict.output_install_dir:
                outputDir = "{0}/{1}".format(project.globalDict.install_prefix, project.globalDict.output_install_dir)
                if not os.path.exists(outputDir):
                    os.makedirs(outputDir)
                log.LOG_INSTALL("Installing {0} to {1}...".format(output, outputDir))
                shutil.copy(output, outputDir)
                install_something = True

            #install headers
            subdir = project.globalDict.header_subdir
            if not subdir:
                subdir = _utils.get_base_name(project.globalDict.output_name)
            if project.globalDict.header_install_dir:
                install_dir = "{0}/{1}/{2}".format(project.globalDict.install_prefix,
                    project.globalDict.header_install_dir, subdir)
                if not os.path.exists(install_dir):
                    os.makedirs(install_dir)
                headers = []
                _utils.get_files(project, headers=headers)
                for header in headers:
                    log.LOG_INSTALL("Installing {0} to {1}...".format(header, install_dir))
                    shutil.copy(header, install_dir)
                install_something = True

            if not install_something:
                log.LOG_INSTALL("Nothing to install.")
            else:
                log.LOG_INSTALL("Done.")
        else:
            log.LOG_ERROR("Output file {0} does not exist! You must build without --install first.".format(output))


def make():
    """Performs both the build and link steps of the process.
    Aborts if the build fails.
    """
    if not build():
        _shared_globals.build_success = False
        log.LOG_ERROR("Build failed. Aborting.")
    else:
        log.LOG_BUILD("Build complete.")


def AddScript(incFile):
    path = os.path.dirname(incFile)
    wd = os.getcwd()
    os.chdir(path)
    with open(incFile, "r") as f:
        exec(f.read(), _shared_globals.makefile_dict, _shared_globals.makefile_dict)
    os.chdir(wd)


@target("debug")
def debug():
    """Default debug target."""
    if not projectSettings.opt_set:
        Opt(0)
    if not projectSettings.debug_set:
        Debug(3)
    if not projectSettings.output_dir_set:
        projectSettings.output_dir = "Debug"
    if not projectSettings.obj_dir_set:
        projectSettings.obj_dir = "Debug/obj"


@target("release")
def release():
    """Default release target."""
    if not projectSettings.opt_set:
        Opt(3)
    if not projectSettings.debug_set:
        Debug(0)
    if not projectSettings.output_dir_set:
        projectSettings.output_dir = "Release"
    if not projectSettings.obj_dir_set:
        projectSettings.obj_dir = "Release/obj"


parser = argparse.ArgumentParser(description='CSB: Build files in local directories and subdirectories.')
parser.add_argument('target', nargs="?", help='Target for build')
parser.add_argument("--project", action="append",
    help="Build only the specified project. May be specified multiple times.")
group = parser.add_mutually_exclusive_group()
group.add_argument('--clean', action="store_true", help='Clean the target build')
group.add_argument('--install', action="store_true", help='Install the target build')
group2 = parser.add_mutually_exclusive_group()
group2.add_argument('-v', action="store_const", const=0, dest="quiet",
    help="Verbose. Enables additional INFO-level logging.", default=1)
group2.add_argument('-q', action="store_const", const=2, dest="quiet",
    help="Quiet. Disables all logging except for WARN and ERROR.", default=1)
group2.add_argument('-qq', action="store_const", const=3, dest="quiet",
    help="Very quiet. Disables all csb-specific logging.", default=1)
parser.add_argument('--show-commands', help="Show all commands sent to the system.", action="store_true")
parser.add_argument('--no-progress', help="Turn off the progress bar.", action="store_true")
parser.add_argument('--force-color', help="Force color on even if the terminal isn't detected as accepting it.",
    action="store_true")
parser.add_argument('--prefix', help="install prefix (default /usr/local)", action="store")
parser.add_argument("-H", "--makefile_help", action="store_true",
    help="Displays specific help for your makefile (if any)")
args, remainder = parser.parse_known_args()

if args.target is not None:
    _shared_globals.target = args.target.lower()
_shared_globals.CleanBuild = args.clean
_shared_globals.do_install = args.install
_shared_globals.quiet = args.quiet
_shared_globals.show_commands = args.show_commands
if args.project:
    _shared_globals.project_build_list = set(args.project)
if args.no_progress:
    _shared_globals.columns = 0
if args.force_color:
    _shared_globals.color_supported = True

if args.prefix:
    _shared_globals.install_prefix = args.prefix

makefile_help = args.makefile_help

if makefile_help:
    remainder.append("-h")

args = remainder

mainfile = sys.modules['__main__'].__file__
if mainfile is not None:
    mainfile = os.path.basename(os.path.abspath(mainfile))
else:
    mainfile = "<makefile>"

#Import the file that imported this file.
#This ensures any options set in that file are executed before we continue.
#It also pulls in its target definitions.
if mainfile != "<makefile>":
    with open(mainfile, "r") as f:
        exec(f.read(), _shared_globals.makefile_dict, _shared_globals.makefile_dict)
else:
    log.LOG_ERROR("CSB cannot be run from the interactive console.")
    sys.exit(1)

if makefile_help:
    sys.exit(0)

if _shared_globals.project_build_list:
    newProjList = {}
    for proj in _shared_globals.project_build_list:
        projData = _shared_globals.projects[proj]
        newProjList[proj] = projData
        for depend in projData.linkDepends:
            newProjList[depend] = _shared_globals.projects[depend]
        for depend in projData.srcDepends:
            newProjList[depend] = _shared_globals.projects[depend]
    _shared_globals.projects = newProjList

_shared_globals.sortedProjects = _utils.sortProjects()

for proj in _shared_globals.sortedProjects:
    proj.prepareBuild()

_utils.check_version()

totaltime = time.time() - _shared_globals.starttime
totalmin = math.floor(totaltime / 60)
totalsec = round(totaltime % 60)
log.LOG_BUILD("Build preparation took {0}:{1:02}".format(int(totalmin), int(totalsec)))

if _shared_globals.CleanBuild:
    clean()
elif _shared_globals.do_install:
    install()
else:
    make()

#Print out any errors or warnings incurred so the user doesn't have to scroll to see what went wrong
for proj in _shared_globals.sortedProjects:
    if proj.globalDict.warnings:
        print("\n")
        log.LOG_WARN("Warnings encountered during build:")
        for warn in proj.globalDict.warnings[0:-1]:
            log.LOG_WARN(warn)
    if proj.globalDict.errors:
        print("\n")
        log.LOG_ERROR("Errors encountered during build:")
        for error in proj.globalDict.errors[0:-1]:
            log.LOG_ERROR(error)

_barWriter.stop()

if not _shared_globals.build_success:
    sys.exit(1)
else:
    sys.exit(0)

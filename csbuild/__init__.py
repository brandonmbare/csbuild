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
import math
import subprocess
import os
import sys
import threading
import time
import platform
import hashlib

class ProjectType(object):
    Application = 0
    SharedLibrary = 1
    StaticLibrary = 2
from csbuild import _utils
from csbuild import toolchain
from csbuild import toolchain_msvc
from csbuild import toolchain_gcc
from csbuild import log
from csbuild import _shared_globals
from csbuild import projectSettings
from csbuild import project_generator_qtcreator
from csbuild import project_generator


__author__ = "Jaedyn K. Draper, Brandon M. Bare"
__copyright__ = 'Copyright (C) 2012-2014 Jaedyn K. Draper'
__credits__ = ["Jaedyn K. Draper", "Brandon M. Bare", "Jeff Grills", "Randy Culley"]
__license__ = 'MIT'

__maintainer__ = "Jaedyn K. Draper"
__email__ = "jaedyn.csbuild-contact@jaedyn.co"
__status__ = "Development"

__all__ = []


signal.signal(signal.SIGINT, signal.SIG_DFL)


class ArchitectureType(object):
    def __init__(self, archString, vendor="unknown", sys="unknown", abi="unknown"):
        self.archString = archString
        self.clangTriple = "{}-{}-{}-{}".format(archString, vendor, sys, abi)

    def __eq__(self, other):
        return self.archString == other.archString

ArchitectureX86 = ArchitectureType("i386")
ArchitectureWIN32 = ArchitectureType("i386", "pc", "win32")

ArchitectureX64 = ArchitectureType("x86_64")
ArchitectureAMD64 = ArchitectureX64
ArchitectureWIN64 = ArchitectureType("x86_64", "pc", "win32")

ArchitectureARM = ArchitectureType("arm")
ArchitectureXScale = ArchitectureARM
ArchitectureAARCH64 = ArchitectureType("aarch64")


ArchitecturePowerPC = ArchitectureType("powerpc")
ArchitecturePowerPC64 = ArchitectureType("powerpc64")
ArchitecturePPU = ArchitecturePowerPC64
#TODO: More of these?

#<editor-fold desc="Setters">
#Setters
def NoBuiltinTargets():
    if projectSettings.currentProject.targets["debug"] == debug:
        del projectSettings.currentProject.targets["debug"]
    if projectSettings.currentProject.targets["release"] == release:
        del projectSettings.currentProject.targets["release"]

def InstallOutput(s="lib"):
    """Enables installation of the compiled output file. Default target is /usr/local/lib."""
    projectSettings.currentProject.output_install_dir = s


def InstallHeaders(s="include"):
    """Enables installation of the project's headers. Default target is /usr/local/include."""
    projectSettings.currentProject.header_install_dir = s


def InstallSubdir(s):
    projectSettings.currentProject.header_subdir = s


def ExcludeDirs(*args):
    """Excludes the given subdirectories from the build. Accepts multiple string arguments."""
    args = list(args)
    newargs = []
    for arg in args:
        if arg[0] != '/' and not arg.startswith("./"):
            arg = "./" + arg
        newargs.append(os.path.abspath(arg))
    projectSettings.currentProject.exclude_dirs += newargs


def ExcludeFiles(*args):
    """Excludes the given files from the build. Accepts multiple string arguments."""
    args = list(args)
    newargs = []
    for arg in args:
        if arg[0] != '/' and not arg.startswith("./"):
            arg = "./" + arg
        newargs.append(os.path.abspath(arg))
    projectSettings.currentProject.exclude_files += newargs


def Libraries(*args):
    """List of libraries to link against. Multiple string arguments. gcc/g++ -l."""
    projectSettings.currentProject.libraries += list(args)


def StaticLibraries(*args):
    """List of libraries to link statically against. Multiple string arguments. gcc/g++ -l."""
    projectSettings.currentProject.static_libraries += list(args)


def SharedLibraries(*args):
    """List of libraries to link statically against. Multiple string arguments. gcc/g++ -l."""
    projectSettings.currentProject.shared_libraries += list(args)
def IncludeDirs(*args):
    """List of directories to search for included headers. Multiple string arguments. gcc/g++ -I
    By default, this list contains /usr/include and /usr/local/include.
    Using this function will add to the existing list, not replace it.
    """
    for arg in args:
        arg = os.path.abspath(arg)
        if not os.path.exists(arg):
            log.LOG_WARN("Include path {0} does not exist!".format(arg))
        projectSettings.currentProject.include_dirs.append(arg)


def LibDirs(*args):
    """List of directories to search for libraries. Multiple string arguments. gcc/g++ -L
    By default, this list contains /usr/lib and /usr/local/lib
    Using this function will add to the existing list, not replace it"""
    for arg in args:
        arg = os.path.abspath(arg)
        if not os.path.exists(arg):
            log.LOG_WARN("Library path {0} does not exist!".format(arg))
        projectSettings.currentProject.library_dirs.append(arg)


def ClearLibraries():
    """Clears the list of libraries"""
    projectSettings.currentProject.libraries = []


def ClearStaticLibraries():
    """Clears the list of libraries"""
    projectSettings.currentProject.static_libraries = []


def ClearSharedibraries():
    """Clears the list of libraries"""
    projectSettings.currentProject.shared_libraries = []


def ClearIncludeDirs():
    """Clears the include directories, including the defaults."""
    projectSettings.currentProject.include_dirs = []


def ClearLibDirs():
    """Clears the library directories, including the defaults"""
    projectSettings.currentProject.library_dirs = []


def Opt(i):
    """Sets the optimization level. gcc/g++ -O"""
    projectSettings.currentProject.opt_level = i
    projectSettings.currentProject.opt_set = True


def Debug(i):
    """Sets the debug level. gcc/g++ -g"""
    projectSettings.currentProject.debug_level = i
    projectSettings.currentProject.debug_set = True


def Define(*args):
    """Sets defines for the project. Accepts multiple arguments. gcc/g++ -D"""
    projectSettings.currentProject.defines += list(args)


def ClearDefines():
    """clears the list of defines"""
    projectSettings.currentProject.defines = []


def Undefine(*args):
    """Sets undefines for the project. Multiple arguments. gcc/g++ -U"""
    projectSettings.currentProject.undefines += list(args)


def ClearUndefines():
    """clears the list of undefines"""
    projectSettings.currentProject.undefines = []


def CppCompiler(s):
    """Sets the compiler to use for the project. Default is g++"""
    projectSettings.currentProject.cxx = s


def CCompiler(s):
    """Sets the compiler to use for the project. Default is gcc"""
    projectSettings.currentProject.cc = s


def Output(name, projectType = ProjectType.Application):
    """Sets the output file for the project. If unset, the project will be compiled as "a.out"""""
    projectSettings.currentProject.output_name = name
    projectSettings.currentProject.type = projectType


def Extension(name):
    projectSettings.currentProject.ext = name


def OutDir(s):
    """Sets the directory to place the compiled result"""
    projectSettings.currentProject.output_dir = os.path.abspath(s)
    projectSettings.currentProject.output_dir_set = True


def ObjDir(s):
    """Sets the directory to place pre-link objects"""
    projectSettings.currentProject.obj_dir = os.path.abspath(s)
    projectSettings.currentProject.obj_dir_set = True


def EnableProfile():
    """Enables profiling optimizations. gcc/g++ -pg"""
    projectSettings.currentProject.profile = True


def DisableProfile():
    """Turns profiling back off."""
    projectSettings.currentProject.profile = False


def CppCompilerFlags(*args):
    """Literal string of extra flags to be passed directly to the compiler"""
    projectSettings.currentProject.cpp_compiler_flags += list(args)


def ClearCppCompilerFlags():
    """Clears the extra flags string"""
    projectSettings.currentProject.cpp_compiler_flags = []


def CCompilerFlags(*args):
    """Literal string of extra flags to be passed directly to the compiler"""
    projectSettings.currentProject.c_compiler_flags += list(args)


def ClearCCompilerFlags():
    """Clears the extra flags string"""
    projectSettings.currentProject.c_compiler_flags = []

def CompilerFlags(*args):
    """Literal string of extra flags to be passed directly to the compiler"""
    CCompilerFlags(*args)
    CppCompilerFlags(*args)


def ClearCompilerFlags():
    """Clears the extra flags string"""
    ClearCCompilerFlags()
    ClearCppCompilerFlags()

def LinkerFlags(*args):
    """Literal string of extra flags to be passed directly to the linker"""
    projectSettings.currentProject.linker_flags += list(args)


def ClearLinkerFlags():
    """Clears the linker flags string"""
    projectSettings.currentProject.linker_flags = []


def DisableChunkedBuild():
    """Turn off the chunked/unity build system and build using individual files."""
    projectSettings.currentProject.use_chunks = False


def EnableChunkedBuild():
    """Turn chunked/unity build on and build using larger compilation units. This is the default."""
    projectSettings.currentProject.use_chunks = True


def ChunkNumFiles(i):
    """Set the size of the chunks used in the chunked build. This indicates the number of files per compilation unit.
    The default is 10.
    This value is ignored if SetChunks is called.
    Mutually exclusive with ChunkFilesize().
    """
    projectSettings.currentProject.chunk_size = i
    projectSettings.currentProject.chunk_filesize = 0


def ChunkFilesize(i):
    """Sets the maximum filesize for a chunk. The default is 500000. This value is ignored if SetChunks is called.
    Mutually exclusive with ChunkNumFiles()
    """
    projectSettings.currentProject.chunk_filesize = i
    projectSettings.currentProject.chunk_size = i


def ChunkTolerance(i):
    """Set the number of files above which the files will be built as a chunk.
    For example, if you set this to 3 (the default), then a chunk will be built as a chunk
    if more than three of its files need to be built; if three or less need to be built, they will
    be built individually to save build time.
    """
    if projectSettings.currentProject.chunk_filesize > 0:
        projectSettings.currentProject.chunk_size_tolerance = i
    elif projectSettings.currentProject.chunk_size > 0:
        projectSettings.currentProject.chunk_tolerance = i
    else:
        log.LOG_WARN("Chunk size and chunk filesize are both zero or negative, cannot set a tolerance.")


def SetChunks(*chunks):
    """Explicitly set the chunks used as compilation units.
    This accepts multiple arguments, each of which should be a list of files.
    Each list is one chunk.
    NOTE that setting this will disable the automatic file gathering, so any files you have
    """
    chunks = list(chunks)
    projectSettings.currentProject.chunks = chunks


def ClearChunks():
    """Clears the explicitly set list of chunks and returns the behavior to the default."""
    projectSettings.currentProject.chunks = []


def HeaderRecursionLevel(i):
    """Sets the depth to search for header files. If set to 0, it will search with unlimited recursion to find included
    headers. Otherwise, it will travel to a depth of i to check headers. If set to 1, this will only check first-level
    headers and not check headers included in other headers; if set to 2, this will check headers included in headers,
    but not headers included by *those* headers; etc.

    This is very useful if you're using a large library (such as boost) or a very large project and are experiencing
    long waits prior to compilation.
    """
    projectSettings.currentProject.header_recursion = i


def IgnoreExternalHeaders():
    """If this option is set, external headers will not be checked or followed when building. Only headers within the
    base project's directory and its subdirectories will be checked. This will speed up header checking, but if you
    modify any external headers, you will need to manually --clean the project.
    """
    projectSettings.currentProject.ignore_external_headers = True


def DisableWarnings():
    """Disables ALL warnings, including gcc/g++'s built-in warnings."""
    projectSettings.currentProject.no_warnings = True


def DefaultTarget(s):
    """Sets the default target if none is specified. The default value for this is release."""
    projectSettings.currentProject.default_target = s.lower()


def Precompile(*args):
    """Explicit list of header files to precompile. Disables chunk precompile when called."""
    projectSettings.currentProject.precompile = []
    for arg in list(args):
        projectSettings.currentProject.precompile.append(os.path.abspath(arg))
    projectSettings.currentProject.chunk_precompile = False


def PrecompileAsC(*args):
    projectSettings.currentProject.cheaders = []
    for arg in list(args):
        projectSettings.currentProject.cheaders.append(os.path.abspath(arg))


def ChunkPrecompile():
    """When this is enabled, all header files will be precompiled into a single "superheader" and included in all
    files."""
    projectSettings.currentProject.chunk_precompile = True


def NoPrecompile(*args):
    """Disables precompilation and handles headers as usual."""
    args = list(args)
    if args:
        newargs = []
        for arg in args:
            if arg[0] != '/' and not arg.startswith("./"):
                arg = "./" + arg
            newargs.append(os.path.abspath(arg))
            projectSettings.currentProject.precompile_exclude += newargs
    else:
        projectSettings.currentProject.chunk_precompile = False


def EnableUnity():
    """Turns on true unity builds, combining all files into only one compilation unit."""
    projectSettings.currentProject.unity = True


def StaticRuntime():
    projectSettings.currentProject.static_runtime = True


def SharedRuntime():
    projectSettings.currentProject.static_runtime = False


def Force32Bit():
    projectSettings.currentProject.force_32_bit = True
    projectSettings.currentProject.force_64_bit = False


def Force64Bit():
    projectSettings.currentProject.force_64_bit = True
    projectSettings.currentProject.force_32_bit = False


def OutputArchitecture(arch):
    projectSettings.currentProject.outputArchitecture = arch


def EnableWarningsAsErrors():
    projectSettings.currentProject.warnings_as_errors = True


def DisableWarningsAsErrors():
    projectSettings.currentProject.warnings_as_errors = False


def RegisterToolchain(name, toolchain):
    _shared_globals.alltoolchains[name] = toolchain
    projectSettings.currentProject.toolchains[name] = toolchain()


def RegisterProjectGenerator(name, generator):
    _shared_globals.allgenerators[name] = generator
    _shared_globals.project_generators[name] = generator


def Toolchain(*args):
    toolchains = []
    for arg in list(args):
        toolchains.append(projectSettings.currentProject.toolchains[arg])
    return toolchain.combined_toolchains(toolchains)


def SetActiveToolchain(name):
    projectSettings.currentProject.activeToolchainName = name

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

    def wrap(projectFunction):
        if name in _shared_globals.projects:
            log.LOG_ERROR("Multiple projects with the same name: {}. Ignoring.".format(name))
            return
        previousProject = projectSettings.currentProject.copy()
        projectFunction()

        if _shared_globals.target:
            projectSettings.currentProject.targetName = _shared_globals.target
        else:
            projectSettings.currentProject.targetName = projectSettings.currentProject.default_target

        if projectSettings.currentProject.targetName not in projectSettings.currentProject.targets:
            log.LOG_INFO("Project {} has no rules specified for target {}. Skipping.".format(projectSettings.currentProject.name, projectSettings.currentProject.targetName))
            projectSettings.currentProject = previousProject
            return

        projectSettings.currentProject.targets[projectSettings.currentProject.targetName]()

        newProject = projectSettings.currentProject.copy()

        newProject.name = "{}@{}".format(name, projectSettings.currentProject.targetName)
        newProject.workingDirectory = os.path.abspath(workingDirectory)

        alteredLinkDepends = []
        alteredSrcDepends = []
        for depend in linkDepends:
            alteredLinkDepends.append("{}@{}".format(depend, projectSettings.currentProject.targetName))
        for depend in srcDepends:
            alteredSrcDepends.append("{}@{}".format(depend, projectSettings.currentProject.targetName))

        newProject.linkDepends = alteredLinkDepends
        newProject.srcDepends = alteredSrcDepends
        newProject.func = projectFunction

        _shared_globals.projects.update({"{}@{}".format(name, projectSettings.currentProject.targetName): newProject})
        projectSettings.currentGroup.projects.update({name: newProject})

        projectSettings.currentProject = previousProject
        return projectFunction

    return wrap

def projectGroup(name):
    def wrap(groupFunction):
        if name in projectSettings.currentGroup.subgroups:
            projectSettings.currentGroup = projectSettings.currentGroup.subgroups[name]
        else:
            newGroup = projectSettings.ProjectGroup(name, projectSettings.currentGroup)
            projectSettings.currentGroup.subgroups.update({name: newGroup})
            projectSettings.currentGroup = newGroup

        groupFunction()

        projectSettings.currentGroup = projectSettings.currentGroup.parentGroup

    return wrap

def target(name):
    def wrap(targetFunction):
        projectSettings.currentProject.targets.update({name: targetFunction})
        return targetFunction

    _shared_globals.alltargets.add(name)
    return wrap

#</editor-fold>

_shared_globals.starttime = time.time()

_barWriter = log.bar_writer()

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
        _shared_globals.total_compiles += len(project.final_chunk_set)

    _shared_globals.total_compiles += _shared_globals.total_precompiles
    _shared_globals.current_compile = 1

    projects_in_flight = []
    projects_done = set()
    pending_links = []
    pending_builds = _shared_globals.sortedProjects
    #projects_needing_links = set()

    for project in _shared_globals.sortedProjects:
        log.LOG_BUILD("Verifying libraries for {} ({})".format(project.output_name, project.targetName))
        if not project.check_libraries():
            sys.exit(1)
        #if _utils.needs_link(project):
        #    projects_needing_links.add(project.name)

    starttime = time.time()

    while pending_builds:
        theseBuilds = pending_builds
        pending_builds = []
        for project in theseBuilds:
            for depend in project.srcDepends:
                if depend not in projects_done:
                    pending_builds.append(project)
                    continue
            projects_in_flight.append(project)

            os.chdir(project.workingDirectory)

            projectSettings.currentProject = project

            project.starttime = time.time()

            log.LOG_BUILD("Building {0} ({1})".format(project.output_name, project.targetName))

            if project.precompile_headers():
                if not os.path.exists(projectSettings.currentProject.obj_dir):
                    os.makedirs(projectSettings.currentProject.obj_dir)

                for chunk in projectSettings.currentProject.final_chunk_set:
                    #not set until here because final_chunk_set may be empty.
                    project.built_something = True

                    built = True
                    obj = "{0}/{1}_{2}.o".format(projectSettings.currentProject.obj_dir, os.path.basename(chunk).split('.')[0],
                        project.targetName)
                    if not _shared_globals.semaphore.acquire(False):
                        if _shared_globals.max_threads != 1:
                            log.LOG_INFO("Waiting for a build thread to become available...")
                        _shared_globals.semaphore.acquire(True)

                    LinkedSomething = True
                    while LinkedSomething:
                        LinkedSomething = False
                        for otherProj in list(projects_in_flight):
                            if otherProj.compiles_completed >= len(otherProj.final_chunk_set) + int(
                                    otherProj.needs_c_precompile) + int(
                                    otherProj.needs_cpp_precompile):
                                totaltime = (time.time() - otherProj.starttime)
                                minutes = math.floor(totaltime / 60)
                                seconds = round(totaltime % 60)

                                if otherProj.final_chunk_set:
                                    log.LOG_BUILD(
                                        "Compile of {0} ({3}) took {1}:{2:02}".format(otherProj.output_name, int(minutes),
                                            int(seconds), otherProj.targetName))
                                projects_in_flight.remove(otherProj)
                                if otherProj.compile_failed:
                                    log.LOG_ERROR("Build of {} ({}) failed! Finishing up non-dependent build tasks...".format(
                                        otherProj.output_name, otherProj.targetName))
                                    continue

                                okToLink = True
                                if otherProj.linkDepends:
                                    for depend in otherProj.linkDepends:
                                        if depend not in projects_done:
                                            okToLink = False
                                            break
                                if okToLink:
                                    if not link(otherProj):
                                        _shared_globals.build_success = False
                                    LinkedSomething = True
                                    log.LOG_BUILD("Finished {} ({})".format(otherProj.output_name, otherProj.targetName))
                                    projects_done.add(otherProj.name)
                                else:
                                    log.LOG_LINKER(
                                        "Linking for {} ({}) deferred until all dependencies have finished building...".format(
                                            otherProj.output_name, otherProj.targetName))
                                    pending_links.append(otherProj)

                        for otherProj in list(pending_links):
                            okToLink = True
                            for depend in otherProj.linkDepends:
                                if depend not in projects_done:
                                    okToLink = False
                                    break
                            if okToLink:
                                if not link(otherProj):
                                    _shared_globals.build_success = False
                                LinkedSomething = True
                                log.LOG_BUILD("Finished {} ({})".format(otherProj.output_name, otherProj.targetName))
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
                            "Compiling {0}... ({1}/{2}) - {3}:{4:02}/{5}:{6:02}".format(os.path.basename(obj),
                                _shared_globals.current_compile, _shared_globals.total_compiles, int(minutes),
                                int(seconds), int(estmin),
                                int(estsec)))
                    else:
                        totaltime = (time.time() - starttime)
                        minutes = math.floor(totaltime / 60)
                        seconds = round(totaltime % 60)
                        log.LOG_BUILD(
                            "Compiling {0}... ({1}/{2}) - {3}:{4:02}".format(os.path.basename(obj), _shared_globals.current_compile,
                                _shared_globals.total_compiles, int(minutes), int(seconds)))
                    _utils.threaded_build(chunk, obj, project).start()
                    _shared_globals.current_compile += 1
            else:
                projects_in_flight.remove(project)
                log.LOG_ERROR("Build of {} ({}) failed! Finishing up non-dependent build tasks...".format(
                    project.output_name, project.targetName))

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

        LinkedSomething = True
        while LinkedSomething:
            LinkedSomething = False
            for otherProj in list(projects_in_flight):
                if otherProj.compiles_completed >= len(otherProj.final_chunk_set) + int(
                        otherProj.needs_c_precompile) + int(
                        otherProj.needs_cpp_precompile):
                    totaltime = (time.time() - otherProj.starttime)
                    minutes = math.floor(totaltime / 60)
                    seconds = round(totaltime % 60)

                    log.LOG_BUILD(
                        "Compile of {0} ({3}) took {1}:{2:02}".format(otherProj.output_name, int(minutes), int(seconds), otherProj.targetName))
                    projects_in_flight.remove(otherProj)
                    if otherProj.compile_failed:
                        log.LOG_ERROR("Build of {} ({}) failed! Finishing up non-dependent build tasks...".format(
                            otherProj.output_name, otherProj.targetName))
                        continue

                    okToLink = True
                    if otherProj.linkDepends:
                        for depend in otherProj.linkDepends:
                            if depend not in projects_done:
                                okToLink = False
                                break
                    if okToLink:
                        link(otherProj)
                        LinkedSomething = True
                        log.LOG_BUILD("Finished {} ({})".format(otherProj.output_name, otherProj.targetName))
                        projects_done.add(otherProj.name)
                    else:
                        log.LOG_LINKER("Linking for {} ({}) deferred until all dependencies have finished building...".format(
                            otherProj.output_name, otherProj.targetName))
                        pending_links.append(otherProj)

            for otherProj in list(pending_links):
                okToLink = True
                for depend in otherProj.linkDepends:
                    if depend not in projects_done:
                        okToLink = False
                        break
                if okToLink:
                    link(otherProj)
                    LinkedSomething = True
                    log.LOG_BUILD("Finished {} ({})".format(otherProj.output_name, otherProj.targetName))
                    projects_done.add(otherProj.name)
                    pending_links.remove(otherProj)

    if projects_in_flight:
        log.LOG_ERROR("Could not complete all projects. This is probably very bad and should never happen."
                      " Remaining projects: {0}".format([p.name for p in projects_in_flight]))
    if pending_links:
        log.LOG_ERROR("Could not link all projects. Do you have unmet dependencies in your makefile?"
                      " Remaining projects: {0}".format([p.name for p in pending_links]))

    compiletime = time.time() - starttime
    totalmin = math.floor(compiletime / 60)
    totalsec = round(compiletime % 60)
    log.LOG_BUILD("Compilation took {0}:{1:02}".format(int(totalmin), int(totalsec)))

    for proj in _shared_globals.sortedProjects:
        proj.save_md5s(proj.allsources, proj.allheaders)

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

    output = "{0}/{1}".format(project.output_dir, project.output_name)

    objs = list(objs)
    if not objs:
        for chunk in project.chunks:
            if not project.unity:
                obj = "{}/{}_{}.o".format(
                    project.obj_dir,
                    hashlib.md5(
                        "{}_chunk_{}".format(
                            project.output_name.split('.')[0],
                            "__".join(_utils.base_names(chunk))
                        )
                    ).hexdigest(),
                    project.targetName
                )
            else:
                obj = "{0}/{1}_unity_{2}.o".format(project.obj_dir, project.output_name,
                    project.targetName)
            if project.use_chunks and os.path.exists(obj):
                objs.append(obj)
            else:
                if type(chunk) == list:
                    for source in chunk:
                        obj = "{0}/{1}_{2}.o".format(project.obj_dir, os.path.basename(source).split('.')[0],
                            project.targetName)
                        if os.path.exists(obj):
                            objs.append(obj)
                        else:
                            log.LOG_ERROR(
                                "Some object files are missing. Either the build failed, or you haven't built yet.")
                            return False
                else:
                    obj = "{0}/{1}_{2}.o".format(project.obj_dir, os.path.basename(chunk).split('.')[0],
                        project.targetName)
                    if os.path.exists(obj):
                        objs.append(obj)
                    else:
                        log.LOG_ERROR(
                            "Some object files are missing. Either the build failed, or you haven't built yet.")
                        return False

    if not objs:
        return True

    if not project.built_something:
        if os.path.exists(output):
            mtime = os.path.getmtime(output)
            for obj in objs:
                if os.path.getmtime(obj) > mtime:
                    #If the obj time is later, something got built in another run but never got linked...
                    #Maybe the linker failed last time.
                    #We should count that as having built something, because we do need to link.
                    #Otherwise, if the object time is earlier, there's a good chance that the existing
                    #output file was linked using a different target, so let's link it again to be safe.
                    project.built_something = True
                    break

            #Even though we didn't build anything, we should verify all our libraries are up to date too.
            #If they're not, we need to relink.
            for i in range(len(project.library_mtimes)):
                if project.library_mtimes[i] > mtime:
                    log.LOG_LINKER(
                        "Library {0} has been modified since the last successful build. Relinking to new library."
                        .format(
                            project.libraries[i]))
                    project.built_something = True

            #Barring the two above cases, there's no point linking if the compiler did nothing.
            if not project.built_something:
                if not _shared_globals.called_something:
                    log.LOG_LINKER("Nothing to link.")
                return True

    log.LOG_LINKER("Linking {0}...".format(os.path.abspath(output)))

    if not os.path.exists(project.output_dir):
        os.makedirs(project.output_dir)

    #Remove the output file so we're not just clobbering it
    #If it gets clobbered while running it could cause BAD THINGS (tm)
    if os.path.exists(output):
        os.remove(output)

    cmd = project.activeToolchain.get_link_command(project, output, objs)
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
    """
    for project in _shared_globals.sortedProjects:

        if not silent:
            log.LOG_BUILD("Cleaning {0} ({1})...".format(project.output_name, project.targetName))
        for source in project.sources:
            obj = "{0}/{1}_{2}.o".format(project.obj_dir, os.path.basename(source).split('.')[0],
                project.targetName)
            if os.path.exists(obj):
                if not silent:
                    log.LOG_INFO("Deleting {0}".format(obj))
                os.remove(obj)
        headerfile = "{0}/{1}_cpp_precompiled_headers_{2}.hpp".format(project.csbuild_dir, project.output_name.split('.')[0],
            project.targetName)
        obj = project.activeToolchain.get_pch_file(headerfile)
        if os.path.exists(obj):
            if not silent:
                log.LOG_INFO("Deleting {0}".format(obj))
            os.remove(obj)

        headerfile = "{0}/{1}_c_precompiled_headers_{2}.h".format(project.csbuild_dir, project.output_name.split('.')[0],
            project.targetName)
        obj = project.activeToolchain.get_pch_file(headerfile)
        if os.path.exists(obj):
            if not silent:
                log.LOG_INFO("Deleting {0}".format(obj))
            os.remove(obj)

        outpath = os.path.join(project.output_dir, project.output_name)
        if os.path.exists(outpath):
            log.LOG_INFO("Deleting {}".format(outpath))

        if not silent:
            log.LOG_BUILD("Done.")


def install():
    """Installer.
    Invoked with --install.
    Installs the generated output file and/or header files to the specified directory.
    Does nothing if neither InstallHeaders() nor InstallOutput() has been called in the make script.
    """
    for project in _shared_globals.sortedProjects:
        os.chdir(project.workingDirectory)
        output = "{0}/{1}".format(project.output_dir, project.output_name)
        install_something = False

        if not project.output_install_dir or os.path.exists(output):
            #install output file
            if project.output_install_dir:
                outputDir = "{0}/{1}".format(_shared_globals.install_prefix, project.output_install_dir)
                if not os.path.exists(outputDir):
                    os.makedirs(outputDir)
                log.LOG_INSTALL("Installing {0} to {1}...".format(output, outputDir))
                shutil.copy(output, outputDir)
                install_something = True

            #install headers
            subdir = project.header_subdir
            if not subdir:
                subdir = _utils.get_base_name(project.output_name)
            if project.header_install_dir:
                install_dir = "{0}/{1}/{2}".format(_shared_globals.install_prefix,
                    project.header_install_dir, subdir)
                if not os.path.exists(install_dir):
                    os.makedirs(install_dir)
                headers = []
                project.get_files(headers=headers)
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
    incFile = os.path.abspath(incFile)
    wd = os.getcwd()
    os.chdir(path)
    _execfile(incFile, _shared_globals.makefile_dict, _shared_globals.makefile_dict)
    os.chdir(wd)

def debug():
    """Default debug target."""
    if not projectSettings.currentProject.opt_set:
        Opt(0)
    if not projectSettings.currentProject.debug_set:
        Debug(3)
    if not projectSettings.currentProject.output_dir_set:
        projectSettings.currentProject.output_dir = "Debug"
    if not projectSettings.currentProject.obj_dir_set:
        projectSettings.currentProject.obj_dir = "Debug/obj"
    if not projectSettings.currentProject.toolchains["msvc"].settingsOverrides["debug_runtime_set"]:
        projectSettings.currentProject.toolchains["msvc"].settingsOverrides["debug_runtime"] = True

def release():
    """Default release target."""
    if not projectSettings.currentProject.opt_set:
        Opt(3)
    if not projectSettings.currentProject.debug_set:
        Debug(0)
    if not projectSettings.currentProject.output_dir_set:
        projectSettings.currentProject.output_dir = "Release"
    if not projectSettings.currentProject.obj_dir_set:
        projectSettings.currentProject.obj_dir = "Release/obj"
    if not projectSettings.currentProject.toolchains["msvc"].settingsOverrides["debug_runtime_set"]:
        projectSettings.currentProject.toolchains["msvc"].settingsOverrides["debug_runtime"] = False


def _setupdefaults():
    RegisterToolchain("gcc", toolchain_gcc.toolchain_gcc)
    RegisterToolchain("msvc", toolchain_msvc.toolchain_msvc)

    RegisterProjectGenerator("qtcreator", project_generator_qtcreator.project_generator_qtcreator)

    if platform.system() == "Windows":
        SetActiveToolchain("msvc")
    else:
        SetActiveToolchain("gcc")

    target("debug")(debug)
    target("release")(release)


def get_option(option):
    option = option.replace("-", "_")
    global args
    if hasattr(args, option):
        return getattr(args, option)
    else:
        return None

_options = []

def add_option(*args, **kwargs):
    _options.append([args, kwargs])

def get_args():
    global args
    return vars(args)

def get_default_arg(argname):
    global parser
    return parser.get_default(argname)


class dummy(object):
    def __setattr__(self, key, value):
        pass

    def __getattribute__(self, item):
        return ""


def _execfile(file, glob, loc):
    if sys.version_info >= (3, 0):
        with open(file, "r") as f:
            exec(f.read(), glob, loc)
    else:
        execfile(file, glob, loc)

mainfile = ""

def _run():
    _setupdefaults()

    global args
    args = dummy()

    global mainfile
    mainfile = sys.modules['__main__'].__file__
    mainfileDir = None
    if mainfile is not None:
        mainfileDir = os.path.abspath(os.path.dirname(mainfile))
        if mainfileDir:
            os.chdir(mainfileDir)
            mainfile = os.path.basename(os.path.abspath(mainfile))
        else:
            mainfileDir = os.path.abspath(os.getcwd())
        if "-h" in sys.argv or "--help" in sys.argv:
            _execfile(mainfile, _shared_globals.makefile_dict, _shared_globals.makefile_dict)
            _shared_globals.sortedProjects = _utils.sortProjects()

    else:
        log.LOG_ERROR("CSB cannot be run from the interactive console.")
        sys.exit(1)

    epilog = "    ------------------------------------------------------------    \n\nProjects available in this makefile (listed in build order):\n\n"

    projtable = [[]]
    i = 1
    j = 0

    maxcols = min(math.floor(len(_shared_globals.sortedProjects) / 4), 4)

    for proj in _shared_globals.sortedProjects:
        projtable[j].append(proj.name.rsplit("@", 1)[0])
        if i < maxcols:
            i += 1
        else:
            projtable.append([])
            i = 1
            j += 1

    if projtable:
        maxlens = [15] * len(projtable[0])
        for index in range(len(projtable)):
            col = projtable[index]
            for subindex in range(len(col)):
                maxlens[subindex] = max(maxlens[subindex], len(col[subindex]))

        for index in range(len(projtable)):
            col = projtable[index]
            for subindex in range(len(col)):
                item = col[subindex]
                epilog += "  "
                epilog += item
                for space in range(maxlens[subindex] - len(item)):
                    epilog += " "
                epilog += "  "
            epilog += "\n"

    epilog += "\nTargets available in this makefile:\n\n"

    targtable = [[]]
    i = 1
    j = 0

    maxcols = min(math.floor(len(_shared_globals.alltargets) / 4), 4)

    for targ in _shared_globals.alltargets:
        targtable[j].append(targ)
        if i < maxcols:
            i += 1
        else:
            targtable.append([])
            i = 1
            j += 1

    if targtable:
        maxlens = [15] * len(targtable[0])
        for index in range(len(targtable)):
            col = targtable[index]
            for subindex in range(len(col)):
                maxlens[subindex] = max(maxlens[subindex], len(col[subindex]))

        for index in range(len(targtable)):
            col = targtable[index]
            for subindex in range(len(col)):
                item = col[subindex]
                epilog += "  "
                epilog += item
                for space in range(maxlens[subindex] - len(item)):
                    epilog += " "
                epilog += "  "
            epilog += "\n"

    global parser
    parser = argparse.ArgumentParser(
        prog=mainfile, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('target', nargs="*", help='Target(s) for build', metavar="target")
    parser.add_argument('-a', "--all-targets", action="store_true", help="Build all targets")

    parser.add_argument(
        "-p",
        "--project",
        action="append",
        help="Build only the specified project. May be specified multiple times."
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--clean', action="store_true", help='Clean the target build')
    group.add_argument('--install', action="store_true", help='Install the target build')
    group.add_argument('--version', action="store_true", help="Print version information and exit")
    group.add_argument('-r', '--rebuild', action="store_true", help='Clean the target build and then build it')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('-v', '--verbose', action="store_const", const=0, dest="quiet",
        help="Verbose. Enables additional INFO-level logging.", default=1)
    group2.add_argument('-q', '--quiet', action="store_const", const=2, dest="quiet",
        help="Quiet. Disables all logging except for WARN and ERROR.", default=1)
    group2.add_argument('-qq', '--very-quiet', action="store_const", const=3, dest="quiet",
        help="Very quiet. Disables all csb-specific logging.", default=1)
    parser.add_argument("-j", "--jobs", action="store", dest="jobs", type=int)
    parser.add_argument('--show-commands', help="Show all commands sent to the system.", action="store_true")
    parser.add_argument('--no-progress', help="Turn off the progress bar.", action="store_true")
    parser.add_argument('--force-color', help="Force color on or off.",
        action="store", choices=["on", "off"], default=None, const="on", nargs="?")
    parser.add_argument('--force-progress-bar', help="Force progress bar on or off.",
        action="store", choices=["on", "off"], default=None, const="on", nargs="?")
    parser.add_argument('--prefix', help="install prefix (default /usr/local)", action="store")
    parser.add_argument('-t', '--toolchain', help="Toolchain to use for compiling.", choices=_shared_globals.alltoolchains, action="store")
    parser.add_argument('--no-precompile', help="Disable precompiling globally, affects all projects", action="store_true")
    parser.add_argument('--no-chunks', help="Disable chunking globally, affects all projects", action="store_true")

    group = parser.add_argument_group("Solution generation", "Commands to generate a solution")
    group.add_argument('--generate-solution', help="Generate a solution file for use with the given IDE.", choices=_shared_globals.allgenerators.keys(), action="store")
    group.add_argument('--solution-path', help="Path to output the solution file (default is ./Solutions/<solutiontype>)", action="store", default="")
    group.add_argument('--solution-name', help="Name of solution output file (default is csbuild)", action = "store", default="csbuild")

    for chain in _shared_globals.alltoolchains.items():
        if chain[1].additional_args != toolchain.toolchainBase.additional_args:
            group = parser.add_argument_group("Options for toolchain {}".format(chain[0]))
            chain[1].additional_args(group)

    for gen in _shared_globals.allgenerators.items():
        if gen[1].additional_args != project_generator.project_generator.additional_args:
            group = parser.add_argument_group("Options for solution generator {}".format(gen[0]))
            gen[1].additional_args(group)

    if _options:
        group = parser.add_argument_group("Local makefile options")
        for option in _options:
            group.add_argument(*option[0], **option[1])

    args = parser.parse_args()

    if args.version:
        with open(os.path.dirname(__file__) + "/version", "r") as f:
            csbuild_version = f.read()
        print("CSBuild version {}".format(csbuild_version))
        print(__copyright__)
        print("Code by {}".format(__author__))
        print("Additional credits: {}".format(", ".join(__credits__)))
        print("\nMaintainer: {} - {}".format(__maintainer__, __email__))
        return

    _shared_globals.CleanBuild = args.clean
    _shared_globals.do_install = args.install
    _shared_globals.quiet = args.quiet
    _shared_globals.show_commands = args.show_commands
    _shared_globals.rebuild = args.rebuild
    project_build_list = None
    if args.project:
        project_build_list = set(args.project)
    if args.no_progress:
        _shared_globals.columns = 0

    if args.force_color == "on":
        _shared_globals.color_supported = True
    elif args.force_color == "off":
        _shared_globals.color_supported = False

    if args.force_progress_bar == "on":
        _shared_globals.columns = 80
    elif args.force_progress_bar == "off":
        _shared_globals.columns = 0

    if args.prefix:
        _shared_globals.install_prefix = args.prefix

    if args.toolchain:
        SetActiveToolchain(args.toolchain)

    if args.jobs:
        _shared_globals.max_threads = args.jobs
        _shared_globals.semaphore = threading.BoundedSemaphore(value=_shared_globals.max_threads)

    _shared_globals.disable_chunks = args.no_chunks
    _shared_globals.disable_precompile = args.no_precompile

    def BuildWithTarget(target):
        if target is not None:
            _shared_globals.target = target.lower()

        #there's an execfile on this up above, but if we got this far we didn't pass --help or -h, so we need to do this here instead
        _execfile(mainfile, _shared_globals.makefile_dict, _shared_globals.makefile_dict)

    if args.all_targets:
        for target in _shared_globals.alltargets:
            BuildWithTarget(target)
    elif args.target:
        for target in args.target:
            BuildWithTarget(target)
        for target in args.target:
            if target.lower() not in _shared_globals.alltargets:
                log.LOG_ERROR("Unknown target: {}".format(target))
                return
    else:
        BuildWithTarget(None)

    if project_build_list:
        for proj in _shared_globals.projects.keys():
            if proj.rsplit("@", 1)[0] in project_build_list:
                _shared_globals.project_build_list.add(proj)

    already_errored_link = {}
    already_errored_source = {}
    def insert_depends(proj, projList, already_inserted=set()):
        already_inserted.add(proj.name)
        if project not in already_errored_link:
            already_errored_link[project] = set()
            already_errored_source[project] = set()
        for index in range(len(proj.linkDepends)):
            depend = proj.linkDepends[index]

            if depend in already_inserted:
                log.LOG_ERROR("Circular dependencies detected: {0} and {1} in linkDepends".format(depend.rsplit("@", 1)[0], proj.name.rsplit("@", 1)[0]))
                sys.exit(1)

            if depend not in _shared_globals.projects:
                if depend not in already_errored_link[project]:
                    log.LOG_ERROR("Project {} references non-existent link dependency {}".format(proj.name.rsplit("@", 1)[0], depend.rsplit("@", 1)[0]))
                    already_errored_link[project].add(depend)
                    del proj.linkDepends[index]
                continue

            projData = _shared_globals.projects[depend]
            projList[depend] = projData

            insert_depends(projData, projList)

        for index in range(len(proj.srcDepends)):
            depend = proj.srcDepends[index]

            if depend in already_inserted:
                log.LOG_ERROR("Circular dependencies detected: {0} and {1} in linkDepends".format(depend.rsplit("@", 1)[0], proj.name.rsplit("@", 1)[0]))
                sys.exit(1)


            if depend not in _shared_globals.projects:
                if depend not in already_errored_link[project]:
                    log.LOG_ERROR("Project {} references non-existent link dependency {}".format(proj.name.rsplit("@", 1)[0], depend.rsplit("@", 1)[0]))
                    already_errored_link[project].add(depend)
                    del proj.linkDepends[index]
                continue

            projData = _shared_globals.projects[depend]
            projList[depend] = projData

            insert_depends(projData, projList)
        already_inserted.remove(proj.name)


    if _shared_globals.project_build_list:
        newProjList = {}
        for proj in _shared_globals.project_build_list:
            projData = _shared_globals.projects[proj]
            newProjList[proj] = projData
            insert_depends(projData, newProjList)
        _shared_globals.projects = newProjList

    _shared_globals.sortedProjects = _utils.sortProjects()

    for proj in _shared_globals.sortedProjects:
        proj.prepareBuild()

    _utils.check_version()

    totaltime = time.time() - _shared_globals.starttime
    totalmin = math.floor(totaltime / 60)
    totalsec = round(totaltime % 60)
    log.LOG_BUILD("Task preparation took {0}:{1:02}".format(int(totalmin), int(totalsec)))

    if args.generate_solution is not None:
        if not args.solution_path:
            args.solution_path = os.path.join(".", "Solutions", args.generate_solution)
        if args.generate_solution not in _shared_globals.project_generators:
            log.LOG_ERROR("No solution generator present for solution of type {}".format(args.generate_solution))
            sys.exit(0)
        generator = _shared_globals.project_generators[args.generate_solution](args.solution_path, args.solution_name)

        generator.write_solution()
        log.LOG_BUILD("Done")

    elif _shared_globals.CleanBuild:
        clean()
    elif _shared_globals.do_install:
        install()
    elif _shared_globals.rebuild:
        clean()
        make()
    else:
        make()

    #Print out any errors or warnings incurred so the user doesn't have to scroll to see what went wrong
    if _shared_globals.warnings:
        print("\n")
        log.LOG_WARN("Warnings encountered during build:")
        for warn in _shared_globals.warnings[0:-1]:
            log.LOG_WARN(warn)
    if _shared_globals.errors:
        print("\n")
        log.LOG_ERROR("Errors encountered during build:")
        for error in _shared_globals.errors[0:-1]:
            log.LOG_ERROR(error)

    _barWriter.stop()

    if not _shared_globals.build_success:
        sys.exit(1)
    else:
        sys.exit(0)

try:
    _run()
except:
    _barWriter.stop()
    raise

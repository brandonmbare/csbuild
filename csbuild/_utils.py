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
import re
import hashlib
import subprocess
import threading
import time
import sys
import datetime
import platform
import glob

from csbuild import log
from csbuild import _shared_globals


def remove_comments(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return ""
        else:
            return s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)


def remove_whitespace(text):
    #This isn't working correctly, turning it off.
    return text
    #shlexer = shlex.shlex(text)
    #out = []
    #token = ""
    #while True:
    #    token = shlexer.get_token()
    #    if token == "":
    #        break
    #    out.append(token)
    #return "".join(out)


def get_md5(inFile):
    if sys.version_info >= (3,0):
        return hashlib.md5(remove_whitespace(remove_comments(inFile.read())).encode('utf-8')).digest()
    else:
        return hashlib.md5(remove_whitespace(remove_comments(inFile.read()))).digest()


def get_size(chunk):
    size = 0
    if type(chunk) == list:
        for source in chunk:
            size += os.path.getsize(source)
        return size
    else:
        return os.path.getsize(chunk)


class threaded_build(threading.Thread):
    """Multithreaded build system, launches a new thread to run the compiler in.
    Uses a threading.BoundedSemaphore object to keep the number of threads equal to the number of processors on the
    machine.
    """

    def __init__(self, infile, inobj, proj, forPrecompiledHeader=False):
        """Initialize the object. Also handles above-mentioned bug with dummy threads."""
        threading.Thread.__init__(self)
        self.file = infile
        self.obj = os.path.abspath(inobj)
        self.project = proj
        self.forPrecompiledHeader = forPrecompiledHeader
        #Prevent certain versions of python from choking on dummy threads.
        if not hasattr(threading.Thread, "_Thread__block"):
            threading.Thread._Thread__block = _shared_globals.dummy_block()

    def run(self):
        """Actually run the build process."""
        starttime = time.time()
        try:
            inc = ""
            headerfile = ""
            if self.file.endswith(".c") or self.file == self.project.cheaderfile:
                if self.project.cheaders and not self.forPrecompiledHeader:
                    headerfile = self.project.cheaderfile
                baseCommand = self.project.cccmd
            else:
                if (self.project.precompile or self.project.chunk_precompile) \
                        and not self.forPrecompiledHeader:
                    headerfile = self.project.cppheaderfile
                baseCommand = self.project.cxxcmd

            if headerfile:
                inc += headerfile
            if self.forPrecompiledHeader:
                cmd = self.project.activeToolchain.get_extended_precompile_command(baseCommand,
                    self.project, inc, self.obj, os.path.abspath(self.file))
            else:
                cmd = self.project.activeToolchain.get_extended_command(baseCommand,
                    self.project, inc, self.obj, os.path.abspath(self.file))

            if _shared_globals.show_commands:
                print(cmd)
            if os.path.exists(self.obj):
                os.remove(self.obj)

            # We have to use os.popen here on Linux, not subprocess.Popen. For some reason, any call to subprocess
            # likes to freeze here when running under Linux, but os.popen works fine.  However, Windows needs subprocess
            # because os.popen won't pipe its output.
            if platform.system() == "Windows":
                fd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (output, errors) = fd.communicate()
                ret = fd.returncode
                sys.stdout.flush()
                sys.stderr.flush()
                sys.stdout.write(output)
                sys.stderr.write(errors)
            else:
                fd = os.popen(cmd)
                output = fd.read()
                ret = fd.close()
                sys.stdout.flush()
                sys.stdout.write(output)

            if ret:
                if str(ret) == str(self.project.activeToolchain.interrupt_exit_code()):
                    _shared_globals.lock.acquire()
                    if not _shared_globals.interrupted:
                        log.LOG_ERROR("Keyboard interrupt received. Aborting build.")
                    _shared_globals.interrupted = True
                    log.LOG_BUILD("Releasing lock...")
                    _shared_globals.lock.release()
                    log.LOG_BUILD("Releasing semaphore...")
                    _shared_globals.semaphore.release()
                    log.LOG_BUILD("Closing thread...")
                if not _shared_globals.interrupted:
                    log.LOG_ERROR("Compile of {} failed!  (Return code: {})".format(self.file, ret))
                _shared_globals.build_success = False
                self.project.compile_failed = True
                self.project.compiles_completed += 1
        except Exception as e:
            #If we don't do this with ALL exceptions, any unhandled exception here will cause the semaphore to never
            # release...
            #Meaning the build will hang. And for whatever reason ctrl+c won't fix it.
            #ABSOLUTELY HAVE TO release the semaphore on ANY exception.
            #if os.path.dirname(self.file) == _csbuild_dir:
            #   os.remove(self.file)
            _shared_globals.semaphore.release()
            self.project.compile_failed = True
            self.project.compiles_completed += 1
            raise e
        else:
            #if os.path.dirname(self.file) == _csbuild_dir:
            #   os.remove(self.file)
            #if inc or (not self.project.precompile and not self.project.chunk_precompile):
            endtime = time.time()
            _shared_globals.times.append(endtime - starttime)
            _shared_globals.semaphore.release()
            self.project.compiles_completed += 1


def base_names(l):
    ret = []
    for srcFile in l:
        ret.append(os.path.basename(srcFile).split(".")[0])
    return ret


def get_base_name(name):
    """This converts an output name into a directory name. It removes extensions, and also removes the prefix 'lib'"""
    ret = name.split(".")[0]
    if ret.startswith("lib"):
        ret = ret[3:]
    return ret


def check_version():
    """Checks the currently installed version against the latest version, and logs a warning if the current version
    is out of date."""
    with open(os.path.dirname(__file__) + "/version", "r") as f:
        csbuild_version = f.read()

    if "-Dev-" in csbuild_version:
        return

    if not os.path.exists(os.path.expanduser("~/.csbuild/check")):
        csbuild_date = ""
    else:
        with open(os.path.expanduser("~/.csbuild/check"), "r") as f:
            csbuild_date = f.read()

    date = datetime.date.today().isoformat()

    if date == csbuild_date:
        return

    if not os.path.exists(os.path.expanduser("~/.csbuild")):
        os.makedirs(os.path.expanduser("~/.csbuild"))

    with open(os.path.expanduser("~/.csbuild/check"), "w") as f:
        f.write(date)

    try:
        out = subprocess.check_output(["pip", "search", "csbuild"])
    except:
        return
    else:
        RMatch = re.search("LATEST:\s*(\S*)$", out)
        if not RMatch:
            return
        latest_version = RMatch.group(1)
        if latest_version != csbuild_version:
            log.LOG_WARN(
                "A new version of csbuild is available. Current version: {0}, latest: {1}".format(csbuild_version,
                    latest_version))
            log.LOG_WARN("Use 'sudo pip install csbuild --upgrade' to get the latest version.")


def sortProjects():
    ret = []

    def insert_depends(project, already_inserted=set()):
        already_inserted.add(project.name)
        for depend in project.linkDepends:
            if depend in already_inserted:
                log.LOG_ERROR("Circular dependencies detected: {0} and {1} in linkDepends".format(depend, project.name))
                sys.exit(1)
            insert_depends(_shared_globals.projects[depend], already_inserted)
        for depend in project.srcDepends:
            if depend in already_inserted:
                log.LOG_ERROR("Circular dependencies detected: {0} and {1} in srcDepends".format(depend, project.name))
                sys.exit(1)
            insert_depends(_shared_globals.projects[depend], already_inserted)
        if project not in ret:
            ret.append(project)
        already_inserted.remove(project.name)

    for project in _shared_globals.projects.values():
        insert_depends(project)

    return ret




def prepare_precompiles():
    if _shared_globals.disable_precompile:
        return

    wd = os.getcwd()
    for project in _shared_globals.projects.values():
        os.chdir(project.workingDirectory)

        precompile_exclude = set()
        for exclude in project.precompile_exclude:
            precompile_exclude |= set(glob.glob(exclude))


        def handleHeaderFile(headerfile, allheaders, forCpp):
            obj = project.activeToolchain.get_pch_file(headerfile)

            precompile = False
            if not os.path.exists(headerfile) or project.should_recompile(headerfile, obj, True):
                precompile = True
            else:
                for header in allheaders:
                    if project.should_recompile(header, obj, True):
                        precompile = True
                        break

            if not precompile:
                return False, headerfile

            with open(headerfile, "w") as f:
                for header in allheaders:
                    if header in precompile_exclude:
                        continue
                    externed = False
                    if forCpp and os.path.abspath(header) in project.cheaders:
                        f.write("extern \"C\"\n{\n\t")
                        externed = True
                    f.write('#include "{0}"\n'.format(os.path.abspath(header)))
                    if externed:
                        f.write("}\n")
            return True, headerfile

        if project.chunk_precompile or project.precompile:
            allheaders = []

            if project.chunk_precompile:
                project.get_files(headers=allheaders)
            else:
                allheaders = project.precompile

            if not allheaders:
                project.needs_cpp_precompile = False
                continue

            project.headers = allheaders

            if not project.precompile and not project.chunk_precompile:
                project.needs_cpp_precompile = False
                continue
                
            project.cppheaderfile = "{0}/{1}_cpp_precompiled_headers_{2}.hpp".format(project.csbuild_dir,
                project.output_name.split('.')[0],
                project.targetName)
                
            project.needs_cpp_precompile, project.cppheaderfile = \
                handleHeaderFile(project.cppheaderfile, allheaders, True)

            _shared_globals.total_precompiles += int(project.needs_cpp_precompile)

        if project.cheaders:
            project.cheaderfile = "{0}/{1}_c_precompiled_headers_{2}.h".format(project.csbuild_dir,
                project.output_name.split('.')[0],
                project.targetName)
                
            project.needs_c_precompile, project.cheaderfile = \
                handleHeaderFile(project.cheaderfile, project.cheaders, False)

            _shared_globals.total_precompiles += int(project.needs_c_precompile)
    os.chdir(wd)




def chunked_build():
    """Prepares the files for a chunked build.
    This function steps through all of the sources that are on the slate for compilation and determines whether each
    needs to be compiled individually or as a chunk. If it is to be compiled as a chunk, this function also creates
    the chunk file to be compiled. It then returns an updated list of files - individual files, chunk files, or both -
    that are to be compiled.
    """

    chunks_to_build = []
    totalChunks = 0
    owningProject = None

    for project in _shared_globals.projects.values():
        for source in project.sources:
            chunk = project.get_chunk(source)
            if project.unity:
                outFile = "{0}/{1}_unity.cpp".format(project.csbuild_dir,
                    project.output_name)
            else:
                outFile = "{0}/{1}.cpp".format(project.csbuild_dir, chunk)
            if chunk not in chunks_to_build and os.path.exists(outFile):
                chunks_to_build.append(chunk)

        totalChunks += len(project.chunks)

        #if we never get a second chunk, we'll want to know about the project that made the first one
        if totalChunks == 1:
            owningProject = project

    #Not enough chunks being built, build as plain files.
    if totalChunks == 0:
        return

    if totalChunks == 1 and not owningProject.unity:
        chunkname = hashlib.md5("{0}_chunk_{1}".format(owningProject.output_name.split('.')[0],
            "__".join(base_names(owningProject.chunks[0])))).hexdigest()
        obj = "{0}/{1}_{2}.o".format(owningProject.obj_dir, chunkname,
            owningProject.targetName)
        if os.path.exists(obj):
            log.LOG_WARN_NOPUSH(
                "Breaking chunk ({0}) into individual files to improve future iteration turnaround.".format(
                    owningProject.chunks[0]))
        owningProject.final_chunk_set = owningProject.sources
        return

    dont_split_any = False
    #If we have to build more than four chunks, or more than a quarter of the total number if that's less than four,
    #then we're not dealing with a "small build" that we can piggyback on to split the chunks back up.
    #Just build them as chunks for now; we'll split them up in another, smaller build.
    if len(chunks_to_build) > min(totalChunks / 4, 4):
        log.LOG_INFO("Not splitting any existing chunks because we would have to build too many.")
        dont_split_any = True

    for project in _shared_globals.projects.values():
        dont_split = dont_split_any
        if project.unity:
            dont_split = True

        for chunk in project.chunks:
            sources_in_this_chunk = []
            for source in project.sources:
                if source in chunk:
                    sources_in_this_chunk.append(source)

            chunksize = get_size(sources_in_this_chunk)

            if project.unity:
                outFile = "{0}/{1}_unity.cpp".format(project.csbuild_dir,
                    project.output_name)
            else:
                outFile = "{}/{}.cpp".format(
                    project.csbuild_dir,
                    hashlib.md5(
                        "{}_chunk_{}".format(
                            project.output_name.split( '.' )[0],
                            "__".join( base_names( chunk ) )
                        )
                    ).hexdigest()
                )

            #If only one or two sources in this chunk need to be built, we get no benefit from building it as a unit.
            # Split unless we're told not to.
            if project.use_chunks and len(chunk) > 1 and (
                        (project.chunk_size > 0 and len(
                                sources_in_this_chunk) > project.chunk_tolerance) or (
                                project.chunk_filesize > 0 and chunksize > project
                        .chunk_size_tolerance) or (
                            dont_split and (project.unity or os.path.exists(outFile)) and len(
                            sources_in_this_chunk) > 0)):
                log.LOG_INFO("Going to build chunk {0} as {1}".format(chunk, outFile))
                with open(outFile, "w") as f:
                    f.write("//Automatically generated file, do not edit.\n")
                    for source in chunk:
                        f.write(
                            '#include "{0}" // {1} bytes\n'.format(os.path.abspath(source),
                                os.path.getsize(source)))
                        obj = "{0}/{1}_{2}.o".format(project.obj_dir,
                            os.path.basename(source).split('.')[0],
                            project.targetName)
                        if os.path.exists(obj):
                            os.remove(obj)
                    f.write("//Total size: {0} bytes".format(chunksize))

                project.final_chunk_set.append(outFile)
            elif len(sources_in_this_chunk) > 0:
                chunkname = hashlib.md5("{0}_chunk_{1}".format(project.output_name.split('.')[0],
                    "__".join(base_names(chunk))))
                obj = "{0}/{1}_{2}.o".format(project.obj_dir, chunkname,
                    project.targetName)
                if os.path.exists(obj):
                    #If the chunk object exists, the last build of these files was the full chunk.
                    #We're now splitting the chunk to speed things up for future incremental builds,
                    # which means the chunk
                    #is getting deleted and *every* file in it needs to be recompiled this time only.
                    #The next time any of these files changes, only that section of the chunk will get built.
                    #This keeps large builds fast through the chunked build, without sacrificing the speed of smaller
                    #incremental builds (except on the first build after the chunk)
                    os.remove(obj)
                    add_chunk = chunk
                    if project.use_chunks:
                        log.LOG_INFO(
                            "Keeping chunk ({0}) broken up because chunking has been disabled for this project".format(
                                chunk))
                    else:
                        log.LOG_WARN_NOPUSH(
                            "Breaking chunk ({0}) into individual files to improve future iteration turnaround.".format(
                                chunk))
                else:
                    add_chunk = sources_in_this_chunk
                if len(add_chunk) == 1:
                    if len(chunk) == 1:
                        log.LOG_INFO(
                            "Going to build {0} as an individual file because it's the only file in its chunk.".format(
                                chunk[0]))
                    else:
                        log.LOG_INFO("Going to build {0} as an individual file.".format(add_chunk))
                else:
                    log.LOG_INFO("Going to build chunk {0} as individual files.".format(add_chunk))
                project.final_chunk_set += add_chunk

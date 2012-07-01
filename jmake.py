import argparse
import atexit
import subprocess
import os
import fnmatch
import sys
import re
import threading
import multiprocessing
import shutil

#NOTE: All this <editor-fold desc="Whatever"> stuff is specific to the PyCharm editor, which allows custom folding blocks.

#<editor-fold desc="Logging">

def LOG_MSG(level, msg):
   """Print a message to stdout"""
   print " ", level, msg

def LOG_ERROR(msg):
   """Log an error message"""
   global _errors
   LOG_MSG("\033[31;1mERROR:\033[0m", msg)
   _errors.append(msg)

def LOG_WARN(msg):
   """Log a warning"""
   global _warnings
   LOG_MSG("\033[33;1mWARN:\033[0m", msg)
   _warnings.append(msg)

def LOG_INFO(msg):
   """Log general info"""
   LOG_MSG("\033[36;1mINFO:\033[0m", msg)

def LOG_BUILD(msg):
   """Log info related to building"""
   LOG_MSG("\033[35;1mBUILD:\033[0m", msg)

def LOG_LINKER(msg):
   """Log info related to linking"""
   LOG_MSG("\033[32;1mLINKER:\033[0m", msg)

def LOG_THREAD(msg):
   """Log info related to threads, particularly stalls caused by waiting on another thread to finish"""
   LOG_MSG("\033[34;1mTHREAD:\033[0m", msg)

def LOG_INSTALL(msg):
   """Log info related to the installer"""
   LOG_MSG("\033[37;1mINSTALL:\033[0m", msg)

#</editor-fold>

#<editor-fold desc="Private">
#<editor-fold desc="Private Variables">
#Private Variables
_libraries = []

_include_dirs = [
   "/usr/include",
   "/usr/local/include"
]

_library_dirs = [
   "/usr/lib",
   "/usr/local/lib"
]

_opt_level = 0
_debug_level = 0
_warn_flags = []
_flags = []
_defines = []
_undefines = []
_compiler = "g++"
_obj_dir = "."
_output_dir = "."
_jmake_dir = "./.jmake"
_output_name = "JMade"
_output_install_dir = ""
_header_install_dir = ""
_automake = True
_standard = ""

_c_files = []
_headers = []
_objs = []

_shared = False
_profile = False

_max_threads = multiprocessing.cpu_count()

_semaphore = threading.BoundedSemaphore(value=_max_threads)

_extra_flags = ""
_linker_flags = ""

_exclude_dirs = []
_exclude_files = []

_built_something = False
_build_success = True
_called_something = False
_overrides = ""

_library_mtimes = []

_output_dir_set = False
_obj_dir_set = False
_debug_set = False
_opt_set = False

_errors = []
_warnings = []

_allheaders = {}
#</editor-fold>

#<editor-fold desc="Private Functions">
#Private Functions
def _get_warnings():
   """Returns a string containing all of the passed warning flags, formatted to be passed to gcc/g++."""
   ret = ""
   for flag in _warn_flags:
      ret += "-W{0} ".format(flag)
   return ret

def _get_defines():
   """Returns a string containing all of the passed defines and undefines, formatted to be passed to gcc/g++."""
   ret = ""
   for define in _defines:
      ret += "-D{0} ".format(define)
   for undefine in _undefines:
      ret += "-U{0} ".format(undefine)
   return ret

def _get_include_dirs():
   """Returns a string containing all of the passed include directories, formatted to be passed to gcc/g++."""
   ret = ""
   for inc in _include_dirs:
      ret += "-I{0} ".format(inc)
   return ret
   
def _get_libraries():
   """Returns a string containing all of the passed libraries, formatted to be passed to gcc/g++."""
   ret = ""
   for lib in _libraries:
      ret += "-l{0} ".format(lib)
   return ret

def _get_library_dirs():
   """Returns a string containing all of the passed library dirs, formatted to be passed to gcc/g++."""
   ret = ""
   for lib in _library_dirs:
      ret += "-L{0} ".format(lib)
   return ret


def _get_flags():
   """Returns a string containing all of the passed flags, formatted to be passed to gcc/g++."""
   ret = ""
   for flag in _flags:
      ret += "-f{0} ".format(flag)
   return ret

def _get_files(sources=None, headers=None):
   """Steps through the current directory tree and finds all of the source and header files, and returns them as a list.
   Accepts two lists as arguments, which it populates. If sources or headers are excluded from the parameters, it will
   ignore files of the relevant types.
   """
   for root, dirnames, filenames in os.walk('.'):
      if root in _exclude_dirs:
         continue
      if sources is not None:
         for filename in fnmatch.filter(filenames, '*.cpp'):
            path = os.path.join(root, filename)
            if path not in _exclude_files:
               sources.append(path)
         for filename in fnmatch.filter(filenames, '*.c'):
            path = os.path.join(root, filename)
            if path not in _exclude_files:
               sources.append(path)

         sources.sort(key=str.lower)

      if headers is not None:
         for filename in fnmatch.filter(filenames, '*.hpp'):
            path = os.path.join(root, filename)
            if path not in _exclude_files:
               headers.append(path)
         for filename in fnmatch.filter(filenames, '*.h'):
            path = os.path.join(root, filename)
            if path not in _exclude_files:
               headers.append(path)

         headers.sort(key=str.lower)

def _follow_headers(file, allheaders):
   """Follow the headers in a file.
   First, this will check to see if the given header has been followed already.
   If it has, it pulls the list from the _allheaders global dictionary and returns it.
   If not, it populates a new allheaders list with _follow_headers2, and then adds
   that to the _allheaders dictionary
   """
   headers = []
   global _allheaders
   if not file:
      return
   with open(file) as f:
      for line in f:
         if line[0] != '#':
            continue

         RMatch = re.search("#include [<\"](.*?)[\">]", line)
         if RMatch is None:
            continue

         if "." not in RMatch.group(1):
            continue

         headers.append(RMatch.group(1))

   path = ""
   for header in headers:
      #If we've already looked at this header (i.e., it was included twice) just ignore it
      if header in allheaders:
         continue
      allheaders.append(header)

      #Check to see if we've already followed this header.
      #If we have, the list we created from it is already stored in _allheaders under this header's key.
      try:
         allheaders += _allheaders[header]
      except KeyError:
         pass
      else:
         continue

      #Find the header in the listed includes.
      path = "{0}/{1}".format(os.path.dirname(file), header)
      if not os.path.exists(path):
         for dir in _include_dirs:
            path = "{0}/{1}".format(dir, header)
            if os.path.exists(path):
               break
      #A lot of standard C and C++ headers will be in a compiler-specific directory that we won't check.
      #Just ignore them to speed things up.
      if not os.path.exists(path):
         continue
      _follow_headers2(path, allheaders)
      _allheaders.update({header : allheaders})

def _follow_headers2(file, allheaders):
   """More intensive, recursive, and cpu-hogging function to follow a header.
   Only executed the first time we see a given header; after that the information is cached."""
   headers = []
   if not file:
      return
   with open(file) as f:
      for line in f:
         if line[0] != '#':
            continue

         RMatch = re.search("#include [<\"](.*?)[\">]", line)
         if RMatch is None:
            continue

         if "." not in RMatch.group(1):
            continue

         headers.append(RMatch.group(1))

   path = ""
   for header in headers:
      #Check to see if we've already followed this header.
      #If we have, the list we created from it is already stored in _allheaders under this header's key.
      if header in allheaders:
         continue
      allheaders.append(header)
      if header in _allheaders:
         continue
      path = "{0}/{1}".format(os.path.dirname(file), header)
      if not os.path.exists(path):
         for dir in _include_dirs:
            path = "{0}/{1}".format(dir, header)
            if os.path.exists(path):
               break
      #A lot of standard C and C++ headers will be in a compiler-specific directory that we won't check.
      #Just ignore them to speed things up.
      if not os.path.exists(path):
         continue
      _follow_headers2(path, allheaders)

def _should_recompile(file):
   """Checks various properties of a file to determine whether or not it needs to be recompiled."""

   basename = os.path.basename(file).split('.')[0]
   ofile = "{0}/{1}.o".format(_obj_dir, basename)

   #First check: If the object file doesn't exist, we obviously have to create it.
   if not os.path.exists(ofile):
      LOG_INFO("Going to recompile {0} because the associated object file does not exist.".format(file))
      return True

   #Second check: Last compilation's debug and optimization settings.
   #If they're different, we want to recompile.
   #This is checked using hidden files in the .jmake subdirectory of the output folder for this target.
   dbg = -1
   opt = -1
   f = "{0}/{1}.jmake".format(_jmake_dir, file)
   if os.path.exists(f):
      with open(f) as f:
         dbg = f.readline()[0:-1]
         opt = f.readline()[0:-1]

      if dbg != str(_debug_level) or opt != str(_opt_level):
         LOG_INFO("Going to recompile {0} because it was compiled with different optimization settings.".format(file))
         return True

   #Third check: modified time.
   #If the source file is newer than the object file, we assume it's been changed and needs to recompile.
   mtime = os.path.getmtime(file)
   omtime = os.path.getmtime(ofile)

   if mtime > omtime:
      LOG_INFO("Going to recompile {0} because it has been modified since the last successful build.".format(file))
      return True

   #Fourth check: Header files
   #If any included header file (recursive, to include headers included by headers) has been changed,
   #then we need to recompile every source that includes that header.
   #Follow the headers for this source file and find out if any have been changed o necessitate a recompile.
   headers = []
   _follow_headers(file, headers)

   for header in headers:
      path = "{0}/{1}".format(os.path.dirname(file), header)
      if not os.path.exists(path):
         for dir in _include_dirs:
            path = "{0}/{1}".format(dir, header)
            if os.path.exists(path):
               break
      #A lot of standard C and C++ headers will be in a compiler-specific directory that we won't check.
      #Just ignore them to speed things up.
      if not os.path.exists(path):
         continue

      header_mtime = os.path.getmtime(path)
      if header_mtime > omtime:
         LOG_INFO("Going to recompile {0} because included header {1} has been modified since the last successful build.".format(file, header))
         return True

   #If we got here, we assume the object file's already up to date.
   LOG_INFO("Skipping {0}: Already up to date".format(file))
   return False

def _check_libraries():
   """Checks the libraries designated by the make script.
   Invokes ld to determine whether or not the library exists.
   Uses the -t flag to get its location.
   And then stores the library's last modified time to a global list to be used by the linker later, to determine
   whether or not a project with up-to-date objects still needs to link against new libraries.
   """
   libraries_ok = True
   mtime = 0
   LOG_INFO("Checking required libraries...")
   for library in _libraries:
      LOG_INFO("Looking for lib{0}...".format(library))
      success = True
      try:
         out = subprocess.check_output(["ld", "-t", "-l{0}".format(library)], stderr=subprocess.STDOUT)
      except subprocess.CalledProcessError as e:
         out = e.output
         success = False
      finally:
         mtime = 0
         RMatch = re.search("-l{0} \\((.*)\\)".format(library), out)
         #Some libraries (such as -liberty) will return successful but don't have a file (internal to ld maybe?)
         #In those cases we can probably assume they haven't been modified.
         #Set the mtime to 0 and return success as long as ld didn't return an error code.
         if RMatch is not None:
               lib = RMatch.group(1)
               mtime = os.path.getmtime(lib)
         elif not success:
            LOG_ERROR("Could not locate library: {0}".format(library))
            libraries_ok = False
         _library_mtimes.append(mtime)
   if not libraries_ok:
      LOG_ERROR("Some dependencies are not met on your system.")
      LOG_ERROR("Check that all required libraries are installed.")
      LOG_ERROR("If they are installed, ensure that the path is included in the makefile (use jmake.LibDirs() to set them)")
      return False
   LOG_INFO("Libraries OK!")
   return True

class _dummy_block:
   """Some versions of python have a bug in threading where a dummy thread will try and use a value that it deleted.
   To keep that from erroring on systems with those versions of python, this is a dummy object with the required
   methods in it, which can be recreated in __init__ for the thread object to prevent this bug from happening.
   """
   def __init__(self):
      return

   def acquire(self):
      return

   def release(self):
      return

   def notify_all(self):
      return

class _threaded_build(threading.Thread):
   """Multithreaded build system, launches a new thread to run the compiler in.
   Uses a threading.BoundedSemaphore object to keep the number of threads equal to the number of processors on the machine.
   """
   def __init__(self, file, obj):
      """Initialize the object. Also handles above-mentioned bug with dummy threads."""
      threading.Thread.__init__(self)
      self.file = file
      self.obj = obj
      #Prevent certain versions of python from choking on dummy threads.
      if not hasattr(threading.Thread, "_Thread__block"):
         threading.Thread._Thread__block = _dummy_block()

   def run(self):
      """Actually run the build process."""
      try:
         global _build_success
         cmd = "{0} -c {1}{2}{3}-g{4} -O{5} {6}{7}{8}{11}{12} -o\"{9}\" \"{10}\"".format(_compiler, _get_warnings(), _get_defines(), _get_include_dirs(), _debug_level, _opt_level, "-fPIC " if _shared else "", "-pg " if _profile else "", "--std={0}".format(_standard) if _standard != "" else "", self.obj, self.file, _get_flags(), _extra_flags)
         #We have to use os.system here, not subprocess.call. For some reason, subprocess.call likes to freeze here, but os.system works fine.
         if os.system(cmd):
            LOG_ERROR("Compile of {0} failed!".format(self.file))
            _build_success = False
         else:
            #Record the debug and optimization level for this build for future reference.
            outpath = "{0}/{1}".format(_jmake_dir, os.path.dirname(self.file))
            if not os.path.exists(outpath):
               os.makedirs(outpath)
            with open("{0}/{1}.jmake".format(_jmake_dir, self.file), "w") as f:
               f.write("{0}\n".format(_debug_level))
               f.write("{0}\n".format(_opt_level))
      except Exception as e:
         #If we don't do this with ALL exceptions, any unhandled exception here will cause the semaphore to never release...
         #Meaning the build will hang. And for whatever reason ctrl+c won't fix it.
         #ABSOLUTELY HAVE TO release the semaphore on ANY exception.
         _semaphore.release()
         raise e
      else:
         _semaphore.release()

#</editor-fold>
#</editor-fold>

#<editor-fold desc="Public">
#<editor-fold desc="Public Variables">
#Public Variables
target = "release"
CleanBuild = False
do_install = False
#</editor-fold>

#<editor-fold desc="Setters">
#Setters
def InstallOutput( s = "/usr/local/lib" ):
   """Enables installation of the compiled output file. Default target is /usr/local/lib."""
   global _output_install_dir
   _output_install_dir = s

def InstallHeaders( s = "/usr/local/include" ):
   """Enables installation of the project's headers. Default target is /usr/local/include."""
   global _header_install_dir
   _header_install_dir = s

def ExcludeDirs( *args ):
   """Excludes the given subdirectories from the build. Accepts multiple string arguments."""
   args = list(args)
   newargs = []
   for arg in args:
      if arg[0] != '/' and not arg.startswith("./"):
         arg = "./" + arg
      newargs.append(arg)
   global _exclude_dirs
   _exclude_dirs += newargs

def ExcludeFiles( *args ):
   """Excludes the given files from the build. Accepts multiple string arguments."""
   args = list(args)
   newargs = []
   for arg in args:
      if arg[0] != '/' and not arg.startswith("./"):
         arg = "./" + arg
      newargs.append(arg)
   global _exclude_files
   _exclude_files += newargs


def Libraries( *args ):
   """List of libraries to link against. Multiple string arguments. gcc/g++ -l."""
   global _libraries
   _libraries += list(args)

def IncludeDirs( *args ):
   """List of directories to search for included headers. Multiple string arguments. gcc/g++ -I
   By default, this list contains /usr/include and /usr/local/include.
   Using this function will add to the existing list, not replace it.
   """
   global _include_dirs
   _include_dirs += list(args)

def LibDirs( *args ):
   """List of directories to search for libraries. Multiple string arguments. gcc/g++ -L
   By default, this list contains /usr/lib and /usr/local/lib
   Using this function will add to the existing list, not replace it"""
   global _library_dirs
   _library_dirs += list(args)
   
def ClearLibraries( ):
   """Clears the list of libraries"""
   global _libraries
   _libraries = []

def ClearIncludeDirs( ):
   """Clears the include directories, including the defaults."""
   global _include_dirs
   _include_dirs = []

def ClearLibDirs( ):
   """Clears the library directories, including the defaults"""
   global _library_dirs
   _library_dirs = []

def Opt(i):
   """Sets the optimization level. gcc/g++ -O"""
   global _opt_level
   global _opt_set
   _opt_level = i
   _opt_set = True

def Debug(i):
   """Sets the debug level. gcc/g++ -g"""
   global _debug_level
   global _debug_set
   _debug_level = i
   _debug_set = True
   
def Define( *args ):
   """Sets defines for the project. Accepts multiple arguments. gcc/g++ -D"""
   global _defines
   _defines += list(args)
   
def ClearDefines( ):
   """clears the list of defines"""
   global _defines
   _defines = []
   
def Undefine( *args ):
   """Sets undefines for the project. Multiple arguments. gcc/g++ -U"""
   global _undefines
   _undefines += list(args)
   
def ClearUndefines( ):
   """clears the list of undefines"""
   global _undefines
   _undefines = []
   
def Compiler(s):
   """Sets the compiler to use for the project. Default is g++"""
   global _compiler
   _compiler = s
   
def Output(s):
   """Sets the output file for the project. If unset, the project will be compiled as "JMade"""""
   global _output_name
   _output_name = s
   
def OutDir(s):
   """Sets the directory to place the compiled result"""
   global _output_dir
   global _output_dir_set
   _output_dir = s
   _output_dir_set = True
   
def ObjDir(s):
   """Sets the directory to place pre-link objects"""
   global _obj_dir
   global _obj_dir_set
   _obj_dir = s
   _obj_dir_set = True
   
def WarnFlags( *args ):
   """Sets warn flags for the project. Multiple arguments. gcc/g++ -W"""
   global _warn_flags
   _warn_flags += list(args)
   
def ClearWarnFlags( ):
   """Clears the list of warning flags"""
   global _warn_flags
   _warn_flags = []
   
def Flags( *args ):
   """Sets miscellaneous flags for the project. Multiple arguments. gcc/g++ -f"""
   global _flags
   _flags += list(args)
   
def ClearFlags( ):
   """Clears the list of misc flags"""
   global _flags
   _flags = []
   
def DisableAutoMake():
   """Disables the automatic build of the project at conclusion of the script
   If you turn this off, you will need to explicitly call either make() to build and link,
   or build() and link() to take each step individually
   """
   global _automake
   _automake = False
   
def EnableAutoMake():
   """Turns the automatic build back on after disabling it"""
   global _automake
   _automake = True
   
def Shared():
   """Builds the project as a shared library. Enables -shared in the linker and -fPIC in the compiler."""
   global _shared
   _shared = True

def NotShared():
   """Turns shared object mode back off after it was enabled."""
   global _shared
   _shared = False
   
def Profile():
   """Enables profiling optimizations. gcc/g++ -pg"""
   global _profile
   _profile = True
   
def Unprofile():
   """Turns profiling back off."""
   global _profile
   _profile = False
   
def ExtraFlags(s):
   """Literal string of extra flags to be passed directly to the compiler"""
   global _extra_flags
   _extra_flags = s
   
def ClearExtraFlags():
   """Clears the extra flags string"""
   global _extra_flags
   _extra_flags = ""

def LinkerFlags(s):
   """Literal string of extra flags to be passed directly to the linker"""
   global _linker_flags
   _linker_flags = s

def ClearLinkerFlags():
   """Clears the linker flags string"""
   global _linker_flags
   _linker_flags = ""
   
def Standard(s):
   """The C/C++ standard to be used when compiling. gcc/g++ --std"""
   global _standard
   _standard = s
#</editor-fold>

#<editor-fold desc="Workers">
def build():
   """Build the project.
   This step handles:
   Checking library dependencies.
   Checking which files need to be built.
   And spawning a build thread for each one that does.
   """
   if not _check_libraries():
      return False

   sources = []

   _get_files(sources)

   if not sources:
      return True

   global _build_success

   LOG_BUILD("Building {0} ({1})".format(_output_name, target))

   if not os.path.exists(_obj_dir):
      os.makedirs(_obj_dir)

   global _jmake_dir
   _jmake_dir = "{0}/.jmake".format(_obj_dir)
   if not os.path.exists(_jmake_dir):
      os.makedirs(_jmake_dir)

   global _objs
   global _max_threads

   for source in sources:
      obj = "{0}/{1}.o".format(_obj_dir, os.path.basename(source).split('.')[0])
      if _should_recompile(source):
         global _built_something
         _built_something = True
         if not _semaphore.acquire(False):
            if _max_threads != 1:
               LOG_THREAD("Waiting for a build thread to become available...")
            _semaphore.acquire(True)
         LOG_BUILD("Building {0}...".format(obj))
         _threaded_build(source, obj).start()
      _objs.append(obj)

   #Wait until all threads are finished. Simple way to do this is acquire the semaphore until it's out of resources.
   for i in range(_max_threads):
      if _max_threads != 1 and not _semaphore.acquire(False):
         LOG_THREAD("Waiting on {0} more build thread{1} to finish...".format(_max_threads - i, "s" if _max_threads - i != 1 else ""))
         _semaphore.acquire(True)

   #Then immediately release all the semaphores once we've reclaimed them.
   #We're not using any more threads so we don't need them now.
   for i in range(_max_threads):
      _semaphore.release()

   if not _built_something:
      LOG_BUILD("Nothing to build.")

   return _build_success
   
def link(*objs):
   """Linker:
   Links all the built files.
   Accepts an optional list of object files to link; if this list is not provided it will use the auto-generated list created by build()
   This function also checks (if nothing was built) the modified times of all the required libraries, to see if we need
   to relink anyway, even though nothing was compiled.
   """
   output = "{0}/{1}".format(_output_dir, _output_name)

   objs = list(objs)
   if not objs:
      objs = _objs

   if not objs:
      return

   global _built_something
   if not _built_something:
      if os.path.exists(output):
         mtime = os.path.getmtime(output)
         for obj in _objs:
            if os.path.getmtime(obj) > mtime:
               #Something got built in another run but never got linked...
               #Maybe the linker failed last time.
               #We should count that as having built something, because we do need to link.
               _built_something = True
               break

         #Even though we didn't build anything, we should verify all our libraries are up to date too.
         #If they're not, we need to relink.
         for i in range(len(_library_mtimes)):
            if _library_mtimes[i] > mtime:
               LOG_LINKER("Library {0} has been modified since the last successful build. Relinking to new library.".format(_libraries[i]))
               _built_something = True

         #Barring the two above cases, there's no point linking if the compiler did nothing.
         if not _built_something:
            if not _called_something:
               LOG_LINKER("Nothing to link.")
            return

   LOG_LINKER("Linking {0}...".format(output))

   objstr = ""

   #Generate the list of objects to link
   for obj in objs:
      objstr += obj + " "

   if not os.path.exists(_output_dir):
      os.makedirs(_output_dir)

   #Remove the output file so we're not just clobbering it
   #If it gets clobbered while running it could cause BAD THINGS (tm)
   if os.path.exists(output):
      os.remove(output)

   subprocess.call("{0} -o{1} {7} {2}{3}-g{4} -O{5} {6} {8}".format(_compiler, output, _get_libraries(), _get_library_dirs(), _debug_level, _opt_level, "-shared " if _shared else "", objstr, _linker_flags), shell=True)


def make():
   """Performs both the build and link steps of the process.
   Aborts if the build fails.
   """
   if not build():
      LOG_ERROR("Build failed. Aborting.")
   else:
      link()
      LOG_BUILD("Build complete.")

def clean():
   """Cleans the project.
   Invoked with --clean.
   Deletes all of the object files to make sure they're rebuilt cleanly next run.
   Does NOT delete the actual compiled file.
   """
   sources = []
   _get_files(sources)
   if not sources:
      return

   LOG_INFO("Cleaning {0} ({1})...".format(_output_name, target))
   for source in sources:
      obj = "{0}/{1}.o".format(_obj_dir, os.path.basename(source).split('.')[0])
      if os.path.exists(obj):
         os.remove(obj)
   LOG_INFO("Done.")

def install():
   """Installer.
   Invoked with --install.
   Installs the generated output file and/or header files to the specified directory.
   Does nothing if neither InstallHeaders() nor InstallOutput() has been called in the make script.
   """
   output = "{0}/{1}".format(_output_dir, _output_name)
   install_something = False

   if os.path.exists(output):
      #install output file
      if _output_install_dir:
         if not os.path.exists(_output_install_dir):
            LOG_ERROR("Install directory {0} does not exist!".format(_output_install_dir))
         else:
            LOG_INSTALL("Installing {0} to {1}...".format(output, _output_install_dir))
            shutil.copy(output, _output_install_dir)
            install_something = True

      #install headers
      if _header_install_dir:
         if not os.path.exists(_header_install_dir):
            LOG_ERROR("Install directory {0} does not exist!".format(_header_install_dir))
         else:
            headers = []
            _get_files(headers=headers)
            for header in headers:
               LOG_INSTALL("Installing {0} to {1}...".format(header, _header_install_dir))
               shutil.copy(header, _header_install_dir)
            install_something = True

      if not install_something:
         LOG_INSTALL("Nothing to install.")
      else:
         LOG_INSTALL("Done.")
   else:
      LOG_ERROR("Output file {0} does not exist! You must build without --install first.".format(output))

#</editor-fold>

#<editor-fold desc="Misc. Public Functions">
def call(s):
   """Calls another makefile script.
   This can be used for multi-tiered projects where each subproject needs its own build script.
   The top-level script will then jmake.call() the other scripts.
   """
   path = os.path.dirname(s)
   file = os.path.basename(s)
   ExcludeDirs(path)
   isMakefile = False
   with open(file) as f:
      for line in f:
         if "import jbuild" in line or "from jbuild import" in line:
            isMakefile = True
   if not isMakefile:
      LOG_ERROR("Called script is not a makefile script!")
   cwd = os.getcwd()
   os.chdir(path)
   LOG_INFO("Entered directory: {0}".format(path))
   args = ["python", file]
   if CleanBuild:
      args.append("--clean")
   if do_install:
      args.append("--install")
   args.append(target)
   subprocess.call(args)
   os.chdir(cwd)
   LOG_INFO("Left directory: {0}".format(path))
   global _called_something
   _called_something = True

#</editor-fold>
#</editor-fold>

#<editor-fold desc="startup">
#<editor-fold desc="Preprocessing">

#This stuff DOES need to run when the module is imported by another file.
#Lack of an if __name__ == __main__ is intentional.
mainfile = sys.modules['__main__'].__file__
if mainfile is not None:
   mainfile = os.path.basename(os.path.abspath(mainfile))
else:
   mainfile = "<makefile>"

parser = argparse.ArgumentParser(description='JMake: Build files in local directories and subdirectories.')
parser.add_argument('target', nargs="?", help='Target for build', default="release")
group = parser.add_mutually_exclusive_group()
group.add_argument('--clean', action="store_true", help='Clean the target build')
group.add_argument('--install', action="store_true", help='Install the target build')
parser.add_argument('--overrides', help="Makefile overrides, semicolon-separated. The contents of the string passed to this will be executed as additional script after the makefile is processed.")
parser.add_argument('remainder', nargs=argparse.REMAINDER, help="Additional arguments (if any) defined by the make script. Use \"python {0} none -h\" to view makefile-defined options.".format(mainfile))
args = parser.parse_args()

#Using argparse.REMAINDER requires that all optional commands be entered before positional ones.
#Creating a second parser to parse the remainder with the same optional commands fixes this.
subparser = argparse.ArgumentParser(description="Dummy.")
subgroup = subparser.add_mutually_exclusive_group()
subgroup.add_argument('--clean', action="store_true", help='Clean the target build')
subgroup.add_argument('--install', action="store_true", help='Install the target build')
subparser.add_argument('remainder', nargs=argparse.REMAINDER, help="")
subparser.add_argument('--overrides', help="")
subargs = subparser.parse_args(args.remainder)

target = args.target.lower()
CleanBuild = args.clean
do_install = args.install
_overrides = args.overrides

#If we didn't get these from args, check subargs to be safe
if not CleanBuild:
   CleanBuild = subargs.clean
if not do_install:
   do_install = subargs.install
if not _overrides:
   _overrides = subargs.overrides

args = subargs.remainder

if target[0] == "_":
   LOG_ERROR("Invalid target: {0}.".format(target))
   sys.exit(1)

def debug():
   if not _opt_set:
      Opt(0)
   if not _debug_set:
      Debug(3)
   if not _output_dir_set:
      OutDir("Debug")
   if not _obj_dir_set:
      ObjDir("Debug/obj")
def release():
   if not _opt_set:
      Opt(3)
   if not _debug_set:
      Debug(0)
   if not _output_dir_set:
      OutDir("Release")
   if not _obj_dir_set:
      ObjDir("Release/obj")
def none():
   sys.exit(0)

#Import the file that imported this file.
#This ensures any options set in that file are executed before we continue.
#It also pulls in its target definitions.
if mainfile != "<makefile>":
   exec("import {0} as __mainfile__".format(mainfile.split(".")[0]))
else:
   LOG_ERROR("JMake cannot be run from the interactive console.")
   sys.exit(1)

#Check if the default debug, release, and none targets have been defined in the makefile script
#If not, set them to the defaults defined above.
try:
   exec "__mainfile__.{0}".format(target)
except AttributeError:
   if target == "debug":
      __mainfile__.debug = debug
   elif target == "release":
      __mainfile__.release = release
   elif target == "none":
      __mainfile__.none = none

#Try to execute the requested target function
#If it doesn't exist, throw an error
try:
   exec "__mainfile__.{0}()".format(target)
except AttributeError:
   LOG_ERROR("Invalid target: {0}".format(target))
else:
   #Execute any overrides that have been passed
   #These will supercede anything set in the makefile script.
   if _overrides:
      exec _overrides
   #If automake hasn't been disabled by the makefile script, call the proper function
   #clean() on --clean
   #install() on --install
   #and make() in any other case
   if _automake:
      if CleanBuild:
         clean()
      elif do_install:
         install()
      else:
         make()
   #Print out any errors or warnings incurred so the user doesn't have to scroll to see what went wrong
   if _warnings:
      LOG_WARN("Warnings encountered during build:")
      for warn in _warnings[0:-1]:
         LOG_WARN(warn)
   if _errors:
      LOG_ERROR("Errors encountered during build:")
      for error in _errors[0:-1]:
         LOG_ERROR(error)

#And finally, explicitly exit! If we don't do this, the makefile script runs again after this.
#That looks sloppy if it does anything visible, and besides that, it takes up needless cycles
sys.exit(0)
#</editor-fold>
#</editor-fold>

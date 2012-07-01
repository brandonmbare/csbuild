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

#<editor-fold desc="Logging">

def LOG_MSG(level, msg):
   print " ", level, msg

def LOG_ERROR(msg):
   global _errors
   LOG_MSG("\033[31;1mERROR:\033[0m", msg)
   _errors.append(msg)

def LOG_WARN(msg):
   global _warnings
   LOG_MSG("\033[33;1mWARN:\033[0m", msg)
   _warnings.append(msg)

def LOG_INFO(msg):
   LOG_MSG("\033[36;1mINFO:\033[0m", msg)

def LOG_BUILD(msg):
   LOG_MSG("\033[35;1mBUILD:\033[0m", msg)

def LOG_LINKER(msg):
   LOG_MSG("\033[32;1mLINKER:\033[0m", msg)

def LOG_THREAD(msg):
   LOG_MSG("\033[34;1mTHREAD:\033[0m", msg)

def LOG_INSTALL(msg):
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
def _AutoMake():
   try:
      exec "{0}()".format(target)
   except NameError:
      LOG_ERROR("Invalid target: {0}".format(target))
   else:
      if _overrides:
         exec _overrides
      global _automake
      if _automake:
         if CleanBuild:
            clean()
         elif do_install:
            install()
         else:
            make()
      
def _get_warnings():
   ret = ""
   for flag in _warn_flags:
      ret += "-W{0} ".format(flag)
   return ret

def _get_defines():
   ret = ""
   for define in _defines:
      ret += "-D{0} ".format(define)
   for undefine in _undefines:
      ret += "-U{0} ".format(undefine)
   return ret

def _get_include_dirs():
   ret = ""
   for inc in _include_dirs:
      ret += "-I{0} ".format(inc)
   return ret
   
def _get_libraries():
   ret = ""
   for lib in _libraries:
      ret += "-l{0} ".format(lib)
   return ret

def _get_library_dirs():
   ret = ""
   for lib in _library_dirs:
      ret += "-L{0} ".format(lib)
   return ret

def _get_files(sources=None, headers=None):
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

def _uniq(seq, idfun=None):
# order preserving
   if idfun is None:
      def idfun(x): return x
   seen = {}
   result = []
   for item in seq:
      marker = idfun(item)
      # in old Python versions:
      # if seen.has_key(marker)
      # but in new ones:
      if marker in seen: continue
      seen[marker] = 1
      result.append(item)
   return result

def _follow_headers(file, allheaders):
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
      if header in allheaders:
         continue
      allheaders.append(header)

      try:
         allheaders += _allheaders[header]
      except KeyError:
         pass
      else:
         continue

      path = "{0}/{1}".format(os.path.dirname(file), header)
      if not os.path.exists(path):
         for dir in _include_dirs:
            path = "{0}/{1}".format(dir, header)
            if os.path.exists(path):
               break
      if not os.path.exists(path):
         continue
      _follow_headers2(path, allheaders)
      _allheaders.update({header : allheaders})

def _follow_headers2(file, allheaders):
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
      if not os.path.exists(path):
         continue
      _follow_headers2(path, allheaders)

def _should_recompile(file):
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

   mtime = os.path.getmtime(file)

   basename = os.path.basename(file).split('.')[0]
   ofile = "{0}/{1}.o".format(_obj_dir, basename)

   if not os.path.exists(ofile):
      LOG_INFO("Going to recompile {0} because the associated object file does not exist.".format(file))
      return True

   omtime = os.path.getmtime(ofile)

   if mtime > omtime:
      LOG_INFO("Going to recompile {0} because it has been modified since the last successful build.".format(file))
      return True

   headers = []
   _follow_headers(file, headers)
   _uniq(headers)

   for header in headers:
      path = "{0}/{1}".format(os.path.dirname(file), header)
      if not os.path.exists(path):
         for dir in _include_dirs:
            path = "{0}/{1}".format(dir, header)
            if os.path.exists(path):
               break
      if not os.path.exists(path):
         #LOG_WARN("Could not find header {0} included by {1}".format(header, file))
         continue

      header_mtime = os.path.getmtime(path)
      if header_mtime > omtime:
         LOG_INFO("Going to recompile {0} because included header {1} has been modified since the last successful build.".format(file, header))
         return True

   LOG_INFO("Skipping {0}: Already up to date".format(file))
   return False

def _check_libraries():
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
         if RMatch != None:
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
   def __init__(self):
      return

   def acquire(self):
      return

   def release(self):
      return

   def notify_all(self):
      return

class _threaded_build(threading.Thread):
   def __init__(self, file, obj):
      threading.Thread.__init__(self)
      self.file = file
      self.obj = obj
      if not hasattr(threading.Thread, "_Thread__block"):
         threading.Thread._Thread__block = _dummy_block()

   def run(self):
      try:
         global _build_success
         cmd = "{0} -c {1}{2}{3}-g{4} -O{5} {6}{7}{8} -o\"{9}\" \"{10}\"".format(_compiler, _get_warnings(), _get_defines(), _get_include_dirs(), _debug_level, _opt_level, "-fPIC " if _shared else "", "-pg " if _profile else "", "--std={0}".format(_standard) if _standard != "" else "", self.obj, self.file)
         if os.system(cmd):
            LOG_ERROR("Compile of {0} failed!".format(self.file))
            _build_success = False
         else:
            with open("{0}/{1}.jmake".format(_jmake_dir, self.file), "w") as f:
               f.write("{0}\n".format(_debug_level))
               f.write("{0}\n".format(_opt_level))
      except Exception as e:
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
   global _output_install_dir
   _output_install_dir = s

def InstallHeaders( s = "/usr/local/include" ):
   global _header_install_dir
   _header_install_dir = s

def ExcludeDirs( *args ):
   args = list(args)
   newargs = []
   for arg in args:
      if arg[0] != '/' and not arg.startswith("./"):
         arg = "./" + arg
      newargs.append(arg)
   global _exclude_dirs
   _exclude_dirs += newargs

def ExcludeFiles( *args ):
   args = list(args)
   newargs = []
   for arg in args:
      if arg[0] != '/' and not arg.startswith("./"):
         arg = "./" + arg
      newargs.append(arg)
   global _exclude_files
   _exclude_files += newargs


def Libraries( *args ):
   global _libraries
   _libraries += list(args)

def IncludeDirs( *args ):
   global _include_dirs
   _include_dirs += list(args)

def LibDirs( *args ):
   global _library_dirs
   _library_dirs += list(args)
   
def ClearLibraries( *args ):
   global _libraries
   _libraries = []

def ClearIncludeDirs( *args ):
   global _include_dirs
   _include_dirs = []

def ClearLibDirs( *args ):
   global _library_dirs
   _library_dirs = []

def Opt(i):
   global _opt_level
   global _opt_set
   _opt_level = i
   _opt_set = True

def Debug(i):
   global _debug_level
   global _debug_set
   _debug_level = i
   _debug_set = True
   
def Define( *args ):
   global _defines
   _defines += list(args)
   
def ClearDefines( *args ):
   global _defines
   _defines = []
   
def Undefine( *args ):
   global _undefines
   _undefines += list(args)
   
def ClearUnefines( *args ):
   global _undefines
   _undefines = []
   
def Compiler(s):
   global _compiler
   _compiler = s
   
def Output(s):
   global _output_name
   _output_name = s
   
def OutDir(s):
   global _output_dir
   global _output_dir_set
   _output_dir = s
   _output_dir_set = True
   
def ObjDir(s):
   global _obj_dir
   global _obj_dir_set
   _obj_dir = s
   _obj_dir_set = True
   
def WarnFlags( *args ):
   global _warn_flags
   _warn_flags += list(args)
   
def ClearWarnFlags( *args ):
   global _warn_flags
   _warn_flags = []
   
def Flags( *args ):
   global _flags
   _flags += list(args)
   
def ClearFlags( *args ):
   global _flags
   _flags = []
   
def DisableAutoMake():
   global _automake
   _automake = False
   
def EnableAutoMake():
   global _automake
   _automake = True
   
def Shared():
   global _shared
   _shared = True

def NotShared():
   global _shared
   _shared = False
   
def Profile():
   global _profile
   _profile = True
   
def Unprofile():
   global _profile
   _profile = False
   
def ExtraFlags(s):
   global _extra_flags
   _extra_flags = s
   
def ClearExtraFlags():
   global _extra_flags
   _extra_flags = ""
   
def Standard(s):
   global _standard
   _standard = s
#</editor-fold>

#<editor-fold desc="Workers">
def build():
   if not _check_libraries():
      return False

   sources = []
   headers = []

   _get_files(sources, headers)

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

   #modified_sources = _check_sources(sources)
   #modified_sources += _check_headers(headers, sources)

   #os.remove("{0}/{1}".format(_output_dir, _output_name))
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
         #cmd = "{0} -c {1}{2}{3}-g{4} -O{5} {6}{7}{8} -o\"{9}\" \"{10}\"".format(_compiler, _get_warnings(), _get_defines(), _get_include_dirs(), _debug_level, _opt_level, "-fPIC " if _shared else "", "-pg " if _profile else "", "--std={0}".format(_standard) if _standard != "" else "", obj, source)
         #_build_success &= not subprocess.call(cmd, shell=True)
         #_semaphore.release()
      _objs.append(obj)

   #Wait until all threads are finished. Simple way to do this is acquire the semaphore until it's out of resources.
   for i in range(_max_threads):
      if _max_threads != 1 and not _semaphore.acquire(False):
         LOG_THREAD("Waiting on {0} more build thread{1} to finish...".format(_max_threads - i, "s" if _max_threads - i != 1 else ""))
         _semaphore.acquire(True)

   if not _built_something:
      LOG_BUILD("Nothing to build.")

   return _build_success
   
def link(*objs):
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
               #Something got built but never got linked...
               #Maybe the linker failed last time.
               #We should count that as having built something, because we do need to link.
               _built_something = True

         for i in range(len(_library_mtimes)):
            if _library_mtimes[i] > mtime:
               LOG_LINKER("Library {0} has been modified since the last successful build. Relinking to new library.".format(_libraries[i]))
               _built_something = True

         if not _built_something:
            if not _called_something:
               LOG_LINKER("Nothing to link.")
            return

   LOG_LINKER("Linking {0}...".format(output))

   if len(objs) == 1:
      shutil.copy(objs[0], output)
      return

   objstr = ""

   for obj in objs:
      objstr += obj + " "

   if not os.path.exists(_output_dir):
      os.makedirs(_output_dir)

   if os.path.exists(output):
      os.remove(output)

   subprocess.call("{0} -o{1} {7} {2}{3}-g{4} -O{5} {6}".format(_compiler, output, _get_libraries(), _get_library_dirs(), _debug_level, _opt_level, "-shared " if _shared else "", objstr), shell=True)
   for i in range(_max_threads):
      _semaphore.release()

def make():
   if not build():
      LOG_ERROR("Build failed. Aborting.")
   else:
      link()
      LOG_BUILD("Build complete.")

def clean():
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
   output = "{0}/{1}".format(_output_dir, _output_name)
   install_something = False

   if os.path.exists(output):
      if _output_install_dir:
         if not os.path.exists(_output_install_dir):
            LOG_ERROR("Install directory {0} does not exist!".format(_output_install_dir))
         else:
            LOG_INSTALL("Installing {0} to {1}...".format(output, _output_install_dir))
            shutil.copy(output, _output_install_dir)
            install_something = True

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
         LOG_ERROR("Nothing to install.")
      else:
         LOG_INSTALL("Done.")
   else:
      LOG_ERROR("Output file {0} does not exist! You must build without --install first.".format(output))

#</editor-fold>

#<editor-fold desc="Misc. Public Functions">
def call(s):
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
_overrides = subargs.overrides

args = subargs.remainder

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

if mainfile != "<makefile>":
   exec("from {0} import *".format(mainfile.split(".")[0]))

def none():
   exit(0)

try:
   exec "{0}()".format(target)
except NameError:
   LOG_ERROR("Invalid target: {0}".format(target))
else:
   if _overrides:
      exec _overrides
   if _automake:
      if CleanBuild:
         clean()
      elif do_install:
         install()
      else:
         make()
   if _warnings:
      LOG_WARN("Warnings encountered during build:")
      for warn in _warnings[0:-1]:
         LOG_WARN(warn)
   if _errors:
      LOG_ERROR("Errors encountered during build:")
      for error in _errors[0:-1]:
         LOG_ERROR(error)
#</editor-fold>

#<editor-fold desc="System Hooks">
#def clear_atexit_excepthook(exctype, value, traceback):
#   LOG_ERROR("Exception caught. Aborting build.")
#   atexit._exithandlers[:] = []
#   sys.__excepthook__(exctype, value, traceback)

#def _exit(i):
#   atexit._exithandlers[:] = []
#   __exit(i)

#sys.excepthook = clear_atexit_excepthook
#__exit = sys.exit
#sys.exit = _exit
#if target != "none":
#   atexit.register(_AutoMake)
#</editor-fold>
#</editor-fold>

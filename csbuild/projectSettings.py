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
B{ProjectSettings module}

Defines the projectSettings class.

@var currentProject: The current project being built. Note that if this is accessed outside of an @project
block, the project returned will only be a temporary variable that will not be valid for compilation
@type currentProject: projectSettings

@var rootProject: Actually a project group, this is poorly named. This is the top-level project group
that all projects and project groups fall under. It has no name and is NOT itself a valid or "real" group.
@type rootProject: ProjectGroup
@todo: Rename rootProject to rootProjectGroup

@var currentGroup: The current group that's being populated
@type currentGroup: ProjectGroup
"""

import csbuild

import fnmatch
import os
import re
import hashlib
import time
import sys
import math
import platform
import glob
import itertools
import threading

from csbuild import log
from csbuild import _shared_globals
from csbuild import _utils

class projectSettings( object ):
	"""
	Contains settings for the project

	@ivar name: The project's name
	@type name: str

	@ivar key: A unique key made by combining project name and target
	@type key: str

	@ivar workingDirectory: The directory containing all of the project's files
	@type workingDirectory: str

	@ivar linkDepends: The projects that this one depends on for linking
	@type linkDepends: list[str]

	@ivar srcDepends: The projects that this one depends on for compiling
	@type srcDepends: str

	@ivar func: The project's settings function - the function wrapped in the @project decorator
	@type func: function

	@ivar libraries: The libraries the project will link against
	@type libraries: list[str]

	@ivar static_libraries: The libraries the project will forcibly statically link against
	@type static_libraries: list[str]

	@ivar shared_libraries: The libraries the project will forcibly statically link against
	@type shared_libraries: list[str]

	@ivar include_dirs: Directories to search for included headers in
	@type include_dirs: list[str]

	@ivar library_dirs: Directories to search for libraries in
	@type library_dirs: list[str]

	@ivar opt_level: Optimization level for this project
	@type opt_level: int or str

	@ivar debug_level: Debug level for this project
	@type debug_level: int or str

	@ivar defines: #define declarations for this project
	@type defines: list[str]

	@ivar undefines: #undef declarations for this project
	@type undefines: list[str]

	@ivar cxx: C++ compiler executable for this project
	@type cxx: str

	@ivar cc: C compiler executable for this project
	@type cc: str

	@ivar hasCppFiles: Whether or not the project includes C++ files
	@type hasCppFiles: bool

	@ivar obj_dir: Output directory for intermediate object files
	@type obj_dir: str

	@ivar output_dir: Output directory for the final output file
	@type output_dir: str

	@ivar csbuild_dir: Output directory for csbuild internal data, subdir of obj_dir
	@type csbuild_dir: str

	@ivar output_name: Final filename to be generated for this project
	@type output_name: str

	@ivar output_install_dir: Directory in which to install the output
	@type output_install_dir: str

	@ivar header_install_dir: Directory in which to install the project's headers
	@type header_install_dir: str

	@ivar header_subdir: Subdirectory that headers live in for this project
	@type header_subdir: str

	@ivar sources: Source files within this project that are being compiled during this run
	@type sources: list[str]

	@ivar allsources: All source files within this project
	@type allsources: list[str]

	@ivar allheaders: Headers within this project
	@type allheaders: list[str]

	@ivar type: Project type
	@type type: L{csbuild.ProjectType}

	@ivar ext: Extension override for output
	@type ext: str or None

	@ivar profile: Whether or not to optimize for profiling
	@type profile: bool

	@ivar cpp_compiler_flags: Literal flags to pass to the C++ compiler
	@type cpp_compiler_flags: list[str]

	@ivar c_compiler_flags: Literal flags to pass to the C compiler
	@type c_compiler_flags: list[str]

	@ivar linker_flags: Literal flags to pass to the linker
	@type linker_flags: list[str]

	@ivar exclude_dirs: Directories excluded from source file discovery
	@type exclude_dirs: list[str]

	@ivar exclude_files: Files excluded from source file discovery
	@type exclude_files: list[str]

	@ivar output_dir_set: Whether or not the output directory has been set
	@type output_dir_set: bool

	@ivar obj_dir_set: Whether or not the object directory has been set
	@type obj_dir_set: bool

	@ivar debug_set: Whether or not debug settings have been set
	@type debug_set: bool

	@ivar opt_set: Whether or not optimization settings have been set
	@type opt_set: bool

	@ivar allpaths: All the paths used to contain all headers included by this project
	@type allpaths: list[str]

	@ivar chunks: Compiled list of chunks to be compiled in this project
	@type chunks: list[str]

	@ivar chunksByFile: Dictionary to get the list of files in a chunk from its filename
	@type chunksByFile: dict[str, list[str]]

	@ivar use_chunks: Whether or not to use chunks
	@type use_chunks: bool

	@ivar chunk_tolerance: minimum number of modified files needed to build a chunk as a chunk
	@type chunk_tolerance: int

	@ivar chunk_size: number of files per chunk
	@type chunk_size: int

	@ivar chunk_filesize: maximum file size of a built chunk, in bytes
	@type chunk_filesize: int

	@ivar chunk_size_tolerance: minimum total filesize of modified files needed to build a chunk as a chunk
	@type chunk_size_tolerance: int

	@ivar header_recursion: Depth to recurse when building header information
	@type header_recursion: int

	@ivar ignore_external_headers: Whether or not to ignore external headers when building header information
	@type ignore_external_headers: bool

	@ivar default_target: The target to be built when none is specified
	@type default_target: str

	@ivar chunk_precompile: Whether or not to precompile all headers in the project
	@type chunk_precompile: bool

	@ivar precompile: List of files to precompile
	@type precompile: list[str]

	@ivar precompile_exclude: List of files NOT to precompile
	@type precompile_exclude: list[str]

	@ivar cppheaderfile: The C++ precompiled header that's been built (if any)
	@type cppheaderfile: str

	@ivar cheaderfile: The C precompiled header that's been built (if any)
	@type cheaderfile: str

	@ivar needs_cpp_precompile: Whether or not the C++ precompiled header needs to be rebuilt during this compile
	@type needs_cpp_precompile: bool

	@ivar needs_c_precompile: Whether or not the C++ precompiled header needs to be rebuilt during this compile
	@type needs_c_precompile: bool

	@ivar unity: Whether or not to build in full unity mode (all files included in one translation unit)
	@type unity: bool

	@ivar precompile_done: Whether or not the project's precompile step has been completed
	@type precompile_done: bool

	@ivar no_warnings: Whether or not to disable all warnings for this project
	@type no_warnings: bool

	@ivar toolchains: All toolchains enabled for this project
	@type toolchains: dict[str, csbuild.toolchain.toolchainBase]

	@ivar cxxcmd: Base C++ compile command, returned from toolchain.get_base_cxx_command
	@type cxxcmd: str

	@ivar cccmd: Base C compile command, returned from toolchain.get_base_cc_command
	@type cccmd: str

	@ivar cxxpccmd: Base C++ precompile command, returned from toolchain.get_base_cxx_precompile_command
	@type cxxpccmd: str

	@ivar ccpccmd: Base C precompile command, returned from toolchain.get_base_cc_precompile_command
	@type ccpccmd: str

	@ivar recompile_all: Whether or not conditions have caused the entire project to need recompilation
	@type recompile_all: bool

	@ivar targets: List of targets in this project with their associated settings functions, decorated with @target
	@type targets: dict[str, list[function]]

	@ivar targetName: The target name for this project as it's currently being built
	@type targetName: str

	@ivar final_chunk_set: The list of chunks to be built after building all chunks, determining whether or not to build
	them as chunks, etc.
	@type final_chunk_set: list[str]

	@ivar compiles_completed: The number of files that have been compiled (successfully or not) at this point in the
	compile process. Note that this variable is modified in multiple threads and should be handled within project.mutex
	@type compiles_completed: int

	@ivar compile_failed: Whether or not ANY compilation unit has failed to successfully compile in this build
	@type compile_failed: bool

	@ivar static_runtime: Whether or not to link against a static runtime
	@type static_runtime: bool

	@ivar force_64_bit: Whether or not to force a 64-bit build
	@type force_64_bit: bool

	@ivar force_32_bit: Whether or not to force a 32-bit build
	@type force_32_bit: bool

	@ivar cheaders: List of headers designated as being C and not C++
	@type cheaders: bool

	@ivar activeToolchainName: The name of the currently active toolchain
	@type activeToolchainName: str

	@ivar activeToolchain: The actual currently active toolchain
	@type activeToolchain: csbuild.toolchain.toolchainBase

	@ivar warnings_as_errors: Whether all warnings should be treated as errors
	@type warnings_as_errors: bool

	@ivar built_something: Whether or not ANY file has been compiled in this build
	@type built_something: bool

	@ivar outputArchitecture: The architecture to build against
	@type outputArchitecture: csbuild.ArchitectureType

	@ivar library_mtimes: Last modified times of all the project's libraries, with no information about what library
	each timestamp belongs to
	@type library_mtimes: list[int]

	@ivar scriptPath: The location of the script file this project is defined in
	@type scriptPath: str

	@ivar mutex: A mutex used to control modification of project data across multiple threads
	@type mutex: threading.Lock

	@ivar preCompileStep: A function that will be executed before compile of this project begins
	@type preCompileStep: function

	@ivar postCompileStep: A function that will be executed after compile of this project ends
	@type postCompileStep: function

	@ivar parentGroup: The group this project is contained within
	@type parentGroup: ProjectGroup

	@ivar state: Current state of the project
	@type state: L{_shared_globals.ProjectState}

	@ivar startTime: The time the project build started
	@type startTime: float

	@ivar endTime: The time the project build ended
	@type endTime: float

	@undocumented: prepareBuild
	@undocumented: __getattribute__
	@undocumented: __setattr__
	@undocumented: get_files
	@undocumented: get_full_path
	@undocumented: get_included_files
	@undocumented: follow_headers
	@undocumented: follow_headers2
	@undocumented: should_recompile
	@undocumented: check_libraries
	@undocumented: make_chunks
	@undocumented: get_chunk
	@undocumented: save_md5
	@undocumented: save_md5s
	@undocumented: precompile_headers

	@note: Toolchains can define additional variables that will show up on this class's
	instance variable list when that toolchain is active. See toolchain documentation for
	more details on what additional instance variables are available.
	"""
	def __init__( self ):
		"""
		Default projectSettings constructor
		"""
		self.name = ""
		self.key = ""
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

		self.sources = []
		self.allsources = []
		self.allheaders = []

		self.type = csbuild.ProjectType.Application
		self.ext = None
		self.profile = False

		self.cpp_compiler_flags = []
		self.c_compiler_flags = []
		self.linker_flags = []

		self.exclude_dirs = []
		self.exclude_files = []

		self.output_dir_set = False
		self.obj_dir_set = False
		self.debug_set = False
		self.opt_set = False

		self.allpaths = []
		self.chunks = []
		self.chunksByFile = {}

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

		self.toolchains = { }

		self.cxxcmd = ""  # return value of get_base_cxx_command
		self.cccmd = ""  # return value of get_base_cc_command
		self.cxxpccmd = ""  # return value of get_base_cxx_precompile_command
		self.ccpccmd = ""  # return value of get_base_cc_precompile_command

		self.recompile_all = False

		self.targets = { }

		self.targetName = ""

		self.final_chunk_set = []

		self.compiles_completed = 0

		self.compile_failed = False

		self.static_runtime = False


		self.force_64_bit = False
		self.force_32_bit = False

		self.cheaders = []

		self.activeToolchainName = None
		self.activeToolchain = None

		self.warnings_as_errors = False

		self.built_something = False

		self.outputArchitecture = None

		self.library_mtimes = []

		self.scriptPath = ""

		self.mutex = threading.Lock( )

		self.postCompileStep = None
		self.preCompileStep = None

		self.parentGroup = currentGroup

		#GUI support
		self.state = _shared_globals.ProjectState.PENDING
		self.startTime = 0
		self.endTime = 0
		self.compileOutput = {}
		self.compileErrors = {}
		self.fileStatus = {}
		self.fileStart = {}
		self.fileEnd = {}
		self.cpchcontents = []
		self.cpppchcontents = []
		self.updated = False


	def prepareBuild( self ):
		wd = os.getcwd( )
		os.chdir( self.workingDirectory )

		self.activeToolchain = self.toolchains[self.activeToolchainName]
		self.obj_dir = os.path.abspath( self.obj_dir )
		self.output_dir = os.path.abspath( self.output_dir )
		self.csbuild_dir = os.path.join( self.obj_dir, ".csbuild" )

		self.exclude_dirs.append( self.csbuild_dir )

		projectSettings.currentProject = self

		if self.ext is None:
			self.ext = self.activeToolchain.get_default_extension( self.type )

		self.output_name += self.ext
		log.LOG_BUILD( "Preparing tasks for {} ({})...".format( self.output_name, self.targetName ) )

		if not os.path.exists( self.csbuild_dir ):
			os.makedirs( self.csbuild_dir )

		self.cccmd = self.activeToolchain.get_base_cc_command( self )
		self.cxxcmd = self.activeToolchain.get_base_cxx_command( self )
		self.ccpccmd = self.activeToolchain.get_base_cc_precompile_command( self )
		self.cxxpccmd = self.activeToolchain.get_base_cxx_precompile_command( self )

		cmdfile = "{0}/{1}.csbuild".format( self.csbuild_dir, self.targetName )
		cmd = ""
		if os.path.exists( cmdfile ):
			with open( cmdfile, "r" ) as f:
				cmd = f.read( )

		if self.cxxcmd + self.cccmd != cmd or _shared_globals.rebuild:
			self.recompile_all = True
			with open( cmdfile, "w" ) as f:
				f.write( self.cxxcmd + self.cccmd )

		if not self.chunks:
			self.get_files( self.allsources, self.allheaders )

			if not self.allsources:
				os.chdir( wd )
				return

			#We'll do this even if _use_chunks is false, because it simplifies the linker logic.
			self.chunks = self.make_chunks( self.allsources )
		else:
			self.allsources = list( itertools.chain( *self.chunks ) )

		if not _shared_globals.CleanBuild and not _shared_globals.do_install and csbuild.get_option(
				"generate_solution" ) is None:
			for source in self.allsources:
				if self.should_recompile( source ):
					self.sources.append( source )
		else:
			self.sources = list( self.allsources )

		_shared_globals.allfiles += self.sources

		if self.name not in self.parentGroup.projects:
			self.parentGroup.projects[self.name] = {}
		self.parentGroup.projects[self.name][self.targetName] = self

		os.chdir( wd )


	def __getattribute__( self, name ):
		activeToolchain = object.__getattribute__( self, "activeToolchain" )
		if activeToolchain and name in activeToolchain.settingsOverrides:
			ret = activeToolchain.settingsOverrides[name]

			if ret:
				if isinstance( ret, dict ):
					ret2 = object.__getattribute__( self, name )
					ret2.update( ret )
					return ret2
				elif isinstance( ret, list ):
					return ret + object.__getattribute__( self, name )

			return ret
		return object.__getattribute__( self, name )


	def __setattr__( self, name, value ):
		if name == "state":
			self.mutex.acquire()
			self.updated = True
			self.mutex.release()

		if hasattr( self, "activeToolchain" ):
			activeToolchain = object.__getattribute__( self, "activeToolchain" )
			if activeToolchain and name in activeToolchain.settingsOverrides:
				activeToolchain.settingsOverrides[name] = value
				return
		object.__setattr__( self, name, value )


	def copy( self ):
		ret = projectSettings( )
		toolchains = { }
		for kvp in self.toolchains.items( ):
			toolchains[kvp[0]] = kvp[1].copy( )

		ret.__dict__ = {
			"name": self.name,
			"key": self.key,
			"workingDirectory": self.workingDirectory,
			"linkDepends": list( self.linkDepends ),
			"srcDepends": list( self.srcDepends ),
			"func": self.func,
			"libraries": list( self.libraries ),
			"static_libraries": list( self.static_libraries ),
			"shared_libraries": list( self.shared_libraries ),
			"include_dirs": list( self.include_dirs ),
			"library_dirs": list( self.library_dirs ),
			"opt_level": self.opt_level,
			"debug_level": self.debug_level,
			"defines": list( self.defines ),
			"undefines": list( self.undefines ),
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
			"sources": list( self.sources ),
			"allsources": list( self.allsources ),
			"allheaders": list( self.allheaders ),
			"type": self.type,
			"ext": self.ext,
			"profile": self.profile,
			"cpp_compiler_flags": list( self.cpp_compiler_flags ),
			"c_compiler_flags": list( self.c_compiler_flags ),
			"linker_flags": list( self.linker_flags ),
			"exclude_dirs": list( self.exclude_dirs ),
			"exclude_files": list( self.exclude_files ),
			"output_dir_set": self.output_dir_set,
			"obj_dir_set": self.obj_dir_set,
			"debug_set": self.debug_set,
			"opt_set": self.opt_set,
			"allpaths": list( self.allpaths ),
			"chunks": list( self.chunks ),
			"chunksByFile" : dict( self.chunksByFile ),
			"use_chunks": self.use_chunks,
			"chunk_tolerance": self.chunk_tolerance,
			"chunk_size": self.chunk_size,
			"chunk_filesize": self.chunk_filesize,
			"chunk_size_tolerance": self.chunk_size_tolerance,
			"header_recursion": self.header_recursion,
			"ignore_external_headers": self.ignore_external_headers,
			"default_target": self.default_target,
			"chunk_precompile": self.chunk_precompile,
			"precompile": list( self.precompile ),
			"precompile_exclude": list( self.precompile_exclude ),
			"cppheaderfile": self.cppheaderfile,
			"cheaderfile": self.cheaderfile,
			"unity": self.unity,
			"precompile_done": self.precompile_done,
			"no_warnings": self.no_warnings,
			"toolchains": toolchains,
			"cxxcmd": self.cxxcmd,
			"cccmd": self.cccmd,
			"recompile_all": self.recompile_all,
			"targets": { },
			"targetName": self.targetName,
			"final_chunk_set": list( self.final_chunk_set ),
			"needs_c_precompile": self.needs_c_precompile,
			"needs_cpp_precompile": self.needs_cpp_precompile,
			"compiles_completed": self.compiles_completed,
			"compile_failed": self.compile_failed,
			"static_runtime": self.static_runtime,
			"force_64_bit": self.force_64_bit,
			"force_32_bit": self.force_32_bit,
			"cheaders": list( self.cheaders ),
			"activeToolchainName": self.activeToolchainName,
			"activeToolchain": None,
			"warnings_as_errors": self.warnings_as_errors,
			"built_something": self.built_something,
			"outputArchitecture": self.outputArchitecture,
			"library_mtimes": list( self.library_mtimes ),
			"scriptPath": self.scriptPath,
			"mutex": threading.Lock( ),
			"preCompileStep" : self.preCompileStep,
			"postCompileStep" : self.postCompileStep,
			"parentGroup" : self.parentGroup,
			"state" : self.state,
			"startTime" : self.startTime,
			"endTime" : self.endTime,
			"compileOutput" : dict(self.compileOutput),
			"compileErrors" : dict(self.compileErrors),
			"fileStatus" : dict(self.fileStatus),
			"fileStart" : dict(self.fileStart),
			"fileEnd" : dict(self.fileEnd),
			"cpchcontents" : list(self.cpchcontents),
			"cpppchcontents" : list(self.cpppchcontents),
			"updated" : self.updated,
		}

		for name in self.targets:
			ret.targets.update( { name: list( self.targets[name] ) } )

		return ret


	def get_files( self, sources = None, headers = None ):
		"""
		Steps through the current directory tree and finds all of the source and header files, and returns them as a list.
		Accepts two lists as arguments, which it populates. If sources or headers are excluded from the parameters, it will
		ignore files of the relevant types.
		"""

		exclude_files = set( )
		exclude_dirs = set( )

		for exclude in self.exclude_files:
			exclude_files |= set( glob.glob( exclude ) )

		for exclude in self.exclude_dirs:
			exclude_dirs |= set( glob.glob( exclude ) )

		for root, dirnames, filenames in os.walk( '.' ):
			absroot = os.path.abspath( root )
			if absroot in exclude_dirs:
				if absroot != self.csbuild_dir:
					log.LOG_INFO( "Skipping dir {0}".format( root ) )
				continue
			if ".csbuild" in root:
				continue
			if absroot == self.csbuild_dir or absroot.startswith( self.csbuild_dir ):
				continue
			bFound = False
			for testDir in exclude_dirs:
				if absroot.startswith( testDir ):
					bFound = True
					break
			if bFound:
				if not absroot.startswith( self.csbuild_dir ):
					log.LOG_INFO( "Skipping dir {0}".format( root ) )
				continue
			log.LOG_INFO( "Looking in directory {0}".format( root ) )
			if sources is not None:
				for filename in fnmatch.filter( filenames, '*.cpp' ):
					path = os.path.join( absroot, filename )
					if path not in exclude_files:
						sources.append( os.path.abspath( path ) )
						self.hasCppFiles = True
				for filename in fnmatch.filter( filenames, '*.c' ):
					path = os.path.join( absroot, filename )
					if path not in exclude_files:
						sources.append( os.path.abspath( path ) )

				sources.sort( key = str.lower )

			if headers is not None:
				for filename in fnmatch.filter( filenames, '*.hpp' ):
					path = os.path.join( absroot, filename )
					if path not in exclude_files:
						headers.append( os.path.abspath( path ) )
						self.hasCppFiles = True
				for filename in fnmatch.filter( filenames, '*.h' ):
					path = os.path.join( absroot, filename )
					if path not in exclude_files:
						headers.append( os.path.abspath( path ) )
				for filename in fnmatch.filter( filenames, '*.inl' ):
					path = os.path.join( absroot, filename )
					if path not in exclude_files:
						headers.append( os.path.abspath( path ) )

				headers.sort( key = str.lower )


	def get_full_path( self, headerFile, relativeDir ):
		if os.path.exists( headerFile ):
			path = headerFile
		else:
			path = "{0}/{1}".format( relativeDir, headerFile )
			if not os.path.exists( path ):
				for incDir in self.include_dirs:
					path = "{0}/{1}".format( incDir, headerFile )
					if os.path.exists( path ):
						break
						#A lot of standard C and C++ headers will be in a compiler-specific directory that we won't
						# check.
						#Just ignore them to speed things up.
			if not os.path.exists( path ):
				return ""

		return path


	def get_included_files( self, headerFile ):
		headers = []
		if sys.version_info >= (3, 0):
			f = open( headerFile, encoding = "latin-1" )
		else:
			f = open( headerFile )
		with f:
			for line in f:
				if line[0] != '#':
					continue

				RMatch = re.search( "#include\s*[<\"](.*?)[\">]", line )
				if RMatch is None:
					continue

				if "." not in RMatch.group( 1 ):
					continue

				headers.append( RMatch.group( 1 ) )

		return headers


	def follow_headers( self, headerFile, allheaders ):
		"""Follow the headers in a file.
		First, this will check to see if the given header has been followed already.
		If it has, it pulls the list from the allheaders global dictionary and returns it.
		If not, it populates a new allheaders list with follow_headers2, and then adds
		that to the allheaders dictionary
		"""
		headers = []

		if not headerFile:
			return

		path = self.get_full_path( headerFile, self.workingDirectory )

		if not path:
			return

		if path in _shared_globals.allheaders:
			allheaders += _shared_globals.allheaders[path]
			return

		headers = self.get_included_files( path )

		for header in headers:

			#Find the header in the listed includes.
			subpath = self.get_full_path( header, os.path.dirname( headerFile ) )

			if self.ignore_external_headers and not subpath.startswith( self.workingDirectory ):
				continue

			#If we've already looked at this header (i.e., it was included twice) just ignore it
			if subpath in allheaders:
				continue

			if subpath in _shared_globals.allheaders:
				allheaders += _shared_globals.allheaders[subpath]
				continue

			allheaders.append( subpath )

			theseheaders = set( )

			if self.header_recursion != 1:
				self.follow_headers2( subpath, theseheaders, 1, headerFile )

			_shared_globals.allheaders.update( { subpath: theseheaders } )
			allheaders += theseheaders

		_shared_globals.allheaders.update( { path: set( allheaders ) } )


	def follow_headers2( self, headerFile, allheaders, n, parent ):
		"""More intensive, recursive, and cpu-hogging function to follow a header.
		Only executed the first time we see a given header; after that the information is cached."""
		headers = []

		if not headerFile:
			return

		path = self.get_full_path( headerFile, os.path.dirname( parent ) )

		if not path:
			return

		if path in _shared_globals.allheaders:
			allheaders += _shared_globals.allheaders[path]
			return

		headers = self.get_included_files( path )

		for header in headers:
			subpath = self.get_full_path( header, os.path.dirname( headerFile ) )

			if self.ignore_external_headers and not subpath.startswith( self.workingDirectory ):
				continue

				#Check to see if we've already followed this header.
			#If we have, the list we created from it is already stored in _allheaders under this header's key.
			if subpath in allheaders:
				continue

			if subpath in _shared_globals.allheaders:
				allheaders |= _shared_globals.allheaders[subpath]
				continue

			allheaders.add( subpath )

			theseheaders = set( allheaders )

			if self.header_recursion == 0 or n < self.header_recursion:
				self.follow_headers2( subpath, theseheaders, n + 1, headerFile )

			_shared_globals.allheaders.update( { subpath: theseheaders } )
			allheaders |= theseheaders


	def should_recompile( self, srcFile, ofile = None, for_precompiled_header = False ):
		"""Checks various properties of a file to determine whether or not it needs to be recompiled."""

		log.LOG_INFO( "Checking whether to recompile {0}...".format( srcFile ) )

		if self.recompile_all:
			log.LOG_INFO(
				"Going to recompile {0} because settings have changed in the makefile that will impact output.".format(
					srcFile ) )
			return True

		basename = os.path.basename( srcFile ).split( '.' )[0]
		if not ofile:
			ofile = "{0}/{1}_{2}.o".format( self.obj_dir, basename,
				self.targetName )

		if self.use_chunks:
			chunk = self.get_chunk( srcFile )
			chunkfile = "{0}/{1}_{2}.o".format( self.obj_dir, chunk,
				self.targetName )

			#First check: If the object file doesn't exist, we obviously have to create it.
			if not os.path.exists( ofile ):
				ofile = chunkfile

		if not os.path.exists( ofile ):
			log.LOG_INFO(
				"Going to recompile {0} because the associated object file does not exist.".format( srcFile ) )
			return True

		#Third check: modified time.
		#If the source file is newer than the object file, we assume it's been changed and needs to recompile.
		mtime = os.path.getmtime( srcFile )
		omtime = os.path.getmtime( ofile )

		if mtime > omtime:
			if for_precompiled_header:
				log.LOG_INFO(
					"Going to recompile {0} because it has been modified since the last successful build.".format(
						srcFile ) )
				return True

			oldmd5 = 1
			newmd5 = 9

			try:
				newmd5 = _shared_globals.newmd5s[srcFile]
			except KeyError:
				with open( srcFile, "r" ) as f:
					newmd5 = _utils.get_md5( f )
				_shared_globals.newmd5s.update( { srcFile: newmd5 } )

			md5file = "{0}/md5s/{1}.md5".format( self.csbuild_dir,
				os.path.abspath( srcFile ) )

			if os.path.exists( md5file ):
				try:
					oldmd5 = _shared_globals.oldmd5s[md5file]
				except KeyError:
					with open( md5file, "rb" ) as f:
						oldmd5 = f.read( )
					_shared_globals.oldmd5s.update( { md5file: oldmd5 } )

			if oldmd5 != newmd5:
				log.LOG_INFO(
					"Going to recompile {0} because it has been modified since the last successful build.".format(

						srcFile ) )
				return True

		#Fourth check: Header files
		#If any included header file (recursive, to include headers included by headers) has been changed,
		#then we need to recompile every source that includes that header.
		#Follow the headers for this source file and find out if any have been changed o necessitate a recompile.
		headers = []

		self.follow_headers( srcFile, headers )

		updatedheaders = []

		for header in headers:
			if os.path.exists( header ):
				path = header
			else:
				continue

			header_mtime = os.path.getmtime( path )

			if header_mtime > omtime:
				if for_precompiled_header:
					updatedheaders.append( [header, path] )
					continue

				#newmd5 is 0, oldmd5 is 1, so that they won't report equal if we ignore them.
				newmd5 = 0
				oldmd5 = 1

				md5file = "{0}/md5s/{1}.md5".format( self.csbuild_dir,
					os.path.abspath( path ) )

				if os.path.exists( md5file ):
					try:
						newmd5 = _shared_globals.newmd5s[path]
					except KeyError:
						if sys.version_info >= (3, 0):
							f = open( path, encoding = "latin-1" )
						else:
							f = open( path )
						with f:
							newmd5 = _utils.get_md5( f )
						_shared_globals.newmd5s.update( { path: newmd5 } )
					if os.path.exists( md5file ):
						try:
							oldmd5 = _shared_globals.oldmd5s[md5file]
						except KeyError:
							with open( md5file, "rb" ) as f:
								oldmd5 = f.read( )
							_shared_globals.oldmd5s.update( { md5file: oldmd5 } )

				if oldmd5 != newmd5:
					updatedheaders.append( [header, path] )

		if updatedheaders:
			files = []
			for pair in updatedheaders:
				files.append( pair[0] )
				path = pair[1]
				if path not in self.allpaths:
					self.allpaths.append( os.path.abspath( path ) )
			log.LOG_INFO(
				"Going to recompile {0} because included headers {1} have been modified since the last successful build."
				.format(
					srcFile, files ) )
			return True

		#If we got here, we assume the object file's already up to date.
		log.LOG_INFO( "Skipping {0}: Already up to date".format( srcFile ) )
		return False


	def check_libraries( self ):
		"""Checks the libraries designated by the make script.
		Invokes ld to determine whether or not the library exists.1
		Uses the -t flag to get its location.
		And then stores the library's last modified time to a global list to be used by the linker later, to determine
		whether or not a project with up-to-date objects still needs to link against new libraries.
		"""
		log.LOG_INFO( "Checking required libraries..." )


		def check_libraries( libraries, force_static, force_shared ):
			libraries_ok = True
			for library in libraries:
				bFound = False
				for depend in self.linkDepends:
					if _shared_globals.projects[depend].output_name.startswith(library) or \
							_shared_globals.projects[depend].output_name.startswith(
									"lib{}.".format( library ) ):
						bFound = True
						break
				if bFound:
					continue

				log.LOG_INFO( "Looking for lib{0}...".format( library ) )
				lib = self.activeToolchain.find_library( self, library, self.library_dirs,
					force_static, force_shared )
				if lib:
					mtime = os.path.getmtime( lib )
					log.LOG_INFO( "Found library lib{0} at {1}".format( library, lib ) )
					self.library_mtimes.append( mtime )
				else:
					log.LOG_ERROR( "Could not locate library: {0}".format( library ) )
					libraries_ok = False
			return libraries_ok


		libraries_ok = check_libraries( self.libraries, False, False )
		libraries_ok = check_libraries( self.static_libraries, True, False ) and libraries_ok
		libraries_ok = check_libraries( self.shared_libraries, False, True ) and libraries_ok
		if not libraries_ok:
			log.LOG_ERROR( "Some dependencies are not met on your system." )
			log.LOG_ERROR( "Check that all required libraries are installed." )
			log.LOG_ERROR(
				"If they are installed, ensure that the path is included in the makefile (use csbuild.LibDirs() to set "
				"them)" )
			return False
		log.LOG_INFO( "Libraries OK!" )
		return True


	def make_chunks( self, l ):
		""" Converts the list into a list of lists - i.e., "chunks"
		Each chunk represents one compilation unit in the chunked build system.
		"""
		if _shared_globals.disable_chunks:
			return l

		sorted_list = sorted( l, key = os.path.getsize, reverse = True )
		if self.unity or not self.use_chunks:
			return [l]
		chunks = []
		if self.chunk_filesize > 0:
			chunksize = 0
			chunk = []
			while sorted_list:
				chunksize = 0
				chunk = [sorted_list[0]]
				chunksize += os.path.getsize( sorted_list[0] )
				sorted_list.pop( 0 )
				for srcFile in reversed( sorted_list ):
					filesize = os.path.getsize( srcFile )
					if chunksize + filesize > self.chunk_filesize:
						chunks.append( chunk )
						log.LOG_INFO( "Made chunk: {0}".format( chunk ) )
						log.LOG_INFO( "Chunk size: {0}".format( chunksize ) )
						break
					else:
						chunk.append( srcFile )
						chunksize += filesize
						sorted_list.pop( )
			chunks.append( chunk )
			log.LOG_INFO( "Made chunk: {0}".format( chunk ) )
			log.LOG_INFO( "Chunk size: {0}".format( chunksize ) )
		elif self.chunk_size > 0:
			for i in range( 0, len( l ), self.chunk_size ):
				chunks.append( l[i:i + self.chunk_size] )
		else:
			return [l]
		return chunks


	def get_chunk( self, srcFile ):
		"""Retrieves the chunk that a given file belongs to."""
		for chunk in self.chunks:
			if srcFile in chunk:
				return "{}_chunk_{}".format(
					self.output_name.split( '.' )[0],
					hashlib.md5("__".join( _utils.base_names( chunk ) ) ).hexdigest( )
				)


	def save_md5( self, inFile ):
		# If we're running on Windows, we need to remove the drive letter from the input file path.
		if platform.system( ) == "Windows":
			inFile = inFile[2:]

		md5file = "{}.md5".format( os.path.join( self.csbuild_dir, "md5s", inFile ) )

		md5dir = os.path.dirname( md5file )
		if not os.path.exists( md5dir ):
			os.makedirs( md5dir )
		newmd5 = ""
		try:
			newmd5 = _shared_globals.newmd5s[inFile]
		except KeyError:
			if sys.version_info >= (3, 0):
				f = open( inFile, encoding = "latin-1" )
			else:
				f = open( inFile )
			with f:
				newmd5 = _utils.get_md5( f )
		finally:
			with open( md5file, "wb" ) as f:
				f.write( newmd5 )


	def save_md5s( self, sources, headers ):
		for source in sources:
			self.save_md5( source )

		for header in headers:
			self.save_md5( header )

		for path in self.allpaths:
			self.save_md5( path )


	def precompile_headers( self ):
		if not self.needs_c_precompile and not self.needs_cpp_precompile:
			return True

		starttime = time.time( )
		log.LOG_BUILD( "Precompiling headers..." )

		self.built_something = True

		if not os.path.exists( self.obj_dir ):
			os.makedirs( self.obj_dir )

		thread = None
		cthread = None
		cppobj = ""
		cobj = ""
		if self.needs_cpp_precompile:
			if not _shared_globals.semaphore.acquire( False ):
				if _shared_globals.max_threads != 1:
					log.LOG_INFO( "Waiting for a build thread to become available..." )
				_shared_globals.semaphore.acquire( True )
			if _shared_globals.interrupted:
				sys.exit( 2 )

			log.LOG_BUILD(
				"Precompiling {0} ({1}/{2})...".format(
					self.cppheaderfile,
					_shared_globals.current_compile,
					_shared_globals.total_compiles ) )

			_shared_globals.current_compile += 1

			cppobj = self.activeToolchain.get_pch_file( self.cppheaderfile )

			#precompiled headers block on current thread - run runs on current thread rather than starting a new one
			thread = _utils.threaded_build( self.cppheaderfile, cppobj, self, True )
			thread.start( )

		if self.needs_c_precompile:
			if not _shared_globals.semaphore.acquire( False ):
				if _shared_globals.max_threads != 1:
					log.LOG_INFO( "Waiting for a build thread to become available..." )
				_shared_globals.semaphore.acquire( True )
			if _shared_globals.interrupted:
				sys.exit( 2 )

			log.LOG_BUILD(
				"Precompiling {0} ({1}/{2})...".format(
					self.cheaderfile,
					_shared_globals.current_compile,
					_shared_globals.total_compiles ) )

			_shared_globals.current_compile += 1

			cobj = self.activeToolchain.get_pch_file( self.cheaderfile )

			#precompiled headers block on current thread - run runs on current thread rather than starting a new one
			cthread = _utils.threaded_build( self.cheaderfile, cobj, self, True )
			cthread.start( )

		if thread:
			thread.join( )
			_shared_globals.precompiles_done += 1
		if cthread:
			cthread.join( )
			_shared_globals.precompiles_done += 1

		totaltime = time.time( ) - starttime
		totalmin = math.floor( totaltime / 60 )
		totalsec = round( totaltime % 60 )
		log.LOG_BUILD( "Precompile took {0}:{1:02}".format( int( totalmin ), int( totalsec ) ) )

		self.precompile_done = True

		return not self.compile_failed



class ProjectGroup( object ):
	"""
	Defines a group of projects, and also may contain subgroups.

	@ivar tempprojects: Temporary list of projects directly under this group
	@type tempprojects: dict[str, projectSettings]

	@ivar projects: Fully fleshed-out list of projects under this group
	Dict is { name : { target : project } }
	@type projects: dict[str, dict[str, projectSettings]]

	@ivar subgroups: List of child groups
	@type subgroups: dict[str, ProjectGroup]

	@ivar name: Group name
	@type name: str

	@ivar parentGroup: The group's parent group
	@type parentGroup: ProjectGroup
	"""
	def __init__( self, name, parentGroup ):
		"""
		Create a new ProjectGroup

		@param name: Group name
		@type name: str

		@param parentGroup: parent group
		@type parentGroup: ProjectGroup
		"""
		self.tempprojects = {}
		self.projects = {}
		self.subgroups = {}
		self.name = name
		self.parentGroup = parentGroup


rootProject = ProjectGroup( "", None )
currentGroup = rootProject
currentProject = projectSettings( )
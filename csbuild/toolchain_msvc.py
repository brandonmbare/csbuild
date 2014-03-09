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
Contains a plugin class for interfacing with MSVC

@undocumented: X64
@undocumented: X86
@undocumented: HAS_SET_VC_VARS
@undocumented: WINDOWS_SDK_DIR
"""

import os
import platform
import subprocess
import sys

from csbuild import toolchain
from csbuild import _shared_globals
import csbuild

### Reference: http://msdn.microsoft.com/en-us/library/f35ctcxw.aspx

X64 = "X64"
X86 = "X86"

HAS_SET_VC_VARS = False
WINDOWS_SDK_DIR = ""


class SubSystem:
	"""
	Enum to define the subsystem to compile against.
	"""
	DEFAULT = 0
	CONSOLE = 1
	WINDOWS = 2
	WINDOWS_CE = 3
	NATIVE = 4
	POSIX = 5
	BOOT_APPLICATION = 6
	EFI_APPLICATION = 7
	EFI_BOOT_SERVICE_DRIVER = 8
	EFI_ROM = 9
	EFI_RUNTIME_DRIVER = 10


class toolchain_msvc( toolchain.toolchainBase ):
	"""
	Toolchain to support compiling with msvc on windows.

	Values Added to projectSettings:
	================================

	This toolchain will add the following items to the L{csbuild.projectSettings.projectSettings}
	class when it is the active toolchain:
		- B{msvc_version}: int denoting the msvc version
		- B{debug_runtime}: bool denoting whether to link against a debug version of the runtime
		- B{debug_runtime_set}: bool denoting whether or not the debug runtime flag has been set

	@undocumented: __init__
	@undocumented: _get_compiler_exe
	@undocumented: _get_linker_exe
	@undocumented: _get_default_compiler_args
	@undocumented: _get_default_linker_args
	@undocumented: _get_compiler_args
	@undocumented: _get_non_static_library_linker_args
	@undocumented: _get_linker_args
	@undocumented: _get_preprocessor_definition_args
	@undocumented: _get_architecture_arg
	@undocumented: _get_runtime_linkage_arg
	@undocumented: _get_runtime_library_arg
	@undocumented: _get_subsystem_arg
	@undocumented: _get_library_args
	@undocumented: _get_warning_args
	@undocumented: _get_linker_warning_arg
	@undocumented: _get_include_directory_args
	@undocumented: _get_library_directory_args
	@undocumented: _get_linker_output_arg
	@undocumented: _get_linker_obj_file_args
	@undocumented: getCompilerCommand
	@undocumented: getExtendedCompilerArgs
	@undocumented: getExtendedPrecompilerArgs
	@undocumented: getLinkerCommand
	@undocumented: SetupForProject
	@undocumented: get_extended_command

	@undocumented: find_library
	@undocumented: get_base_cxx_command
	@undocumented: get_base_cc_command
	@undocumented: get_link_command
	@undocumented: get_base_cxx_precompile_command
	@undocumented: get_base_cc_precompile_command
	@undocumented: get_extended_precompile_command
	@undocumented: get_default_extension
	@undocumented: interrupt_exit_code
	@undocumented: get_pch_file
	"""

	def __init__( self ):
		toolchain.toolchainBase.__init__( self )

		self._project_settings = None
		self.settingsOverrides["msvc_version"] = 100
		self.settingsOverrides["debug_runtime"] = False
		self.settingsOverrides["debug_runtime_set"] = False
		self._subsystem = SubSystem.DEFAULT

		self._actual_library_names = { }


	def SetupForProject( self, project ):
		platform_architectures = {
			"amd64": X64,
			"x86_64": X64,
			"x86": X86,
			"i386": X86 }

		self._project_settings = project
		self._vc_env_var = r"VS{}COMNTOOLS".format( self.settingsOverrides["msvc_version"] )
		self._toolchain_path = os.path.normpath( os.path.join( os.environ[self._vc_env_var], "..", "..", "VC" ) )
		self._bin_path = os.path.join( self._toolchain_path, "bin" )
		self._include_path = [os.path.join( self._toolchain_path, "include" )]
		self._lib_path = [os.path.join( self._toolchain_path, "lib" )]
		self._platform_arch = platform_architectures.get( platform.machine( ).lower( ), X86 )
		self._build_64_bit = False

		# Determine if we need to build for 64-bit.
		if self._platform_arch == X64 and not self._project_settings.force_64_bit and not self._project_settings.force_32_bit:
			self._build_64_bit = True
		elif self._project_settings.force_64_bit:
			self._build_64_bit = True

		# If we're trying to build for 64-bit, determine the appropriate path for the 64-bit tools based on the machine's architecture.
		if self._build_64_bit:
			#TODO: Switch the assembler to ml64.exe when assemblers are supported.
			self._bin_path = os.path.join( self._bin_path, "amd64" if self._platform_arch == X64 else "x86_amd64" )
			self._lib_path[0] = os.path.join( self._lib_path[0], "amd64" )

		global HAS_SET_VC_VARS
		global WINDOWS_SDK_DIR
		if not HAS_SET_VC_VARS:

			batch_file_path = os.path.join( self._toolchain_path, "vcvarsall.bat" )
			fd = subprocess.Popen( '"{}" {} & set'.format( batch_file_path, "x64" if self._build_64_bit else "x86" ),
				stdout = subprocess.PIPE, stderr = subprocess.PIPE )

			if sys.version_info >= (3, 0):
				(output, errors) = fd.communicate( str.encode("utf-8") )
			else:
				(output, errors) = fd.communicate( )

			output_lines = output.splitlines( )

			for line in output_lines:
				if line.startswith( "WindowsSdkDir=" ):
					key_value_list = line.split( "=", 1 )
					WINDOWS_SDK_DIR = key_value_list[1]
					break

			HAS_SET_VC_VARS = True

		self._include_path.append( os.path.join( WINDOWS_SDK_DIR, "include" ) )
		self._lib_path.append( os.path.join( WINDOWS_SDK_DIR, "lib", "x64" if self._build_64_bit else "" ) )


	### Private methods ###

	def _get_compiler_exe( self ):
		return '"{}" '.format( os.path.join( self._bin_path, "cl" ) )


	def _get_linker_exe( self ):
		return '"{}" '.format( os.path.join( self._bin_path,
			"lib" if self._project_settings.type == csbuild.ProjectType.StaticLibrary else "link" ) )


	def _get_default_compiler_args( self ):
		return "/nologo /c /arch:AVX "


	def _get_default_linker_args( self ):
		default_args = "/NOLOGO "
		for lib_path in self._lib_path:
			default_args += '/LIBPATH:"{}" '.format( lib_path )
		return default_args


	def _get_compiler_args( self ):
		return "{}{}{}{}{}".format(
			self._get_default_compiler_args( ),
			self._get_preprocessor_definition_args( ),
			self._get_runtime_linkage_arg( ),
			self._get_warning_args( ),
			self._get_include_directory_args( ) )


	def _get_non_static_library_linker_args( self ):
		# The following arguments should only be specified for dynamic libraries and executables (being used with link.exe, not lib.exe).
		return "" if self._project_settings.type == csbuild.ProjectType.StaticLibrary else "{}{}{}{}".format(
			self._get_runtime_library_arg( ),
			"/PROFILE " if self._project_settings.profile else "",
			"/DEBUG " if self._project_settings.profile or self._project_settings.debug_level > 0 else "",
			"/DLL " if self._project_settings.type == csbuild.ProjectType.SharedLibrary else "" )


	def _get_linker_args( self, output_file, obj_list ):
		return "{}{}{}{}{}{}{}{}{}".format(
			self._get_default_linker_args( ),
			self._get_non_static_library_linker_args( ),
			self._get_subsystem_arg( ),
			self._get_architecture_arg( ),
			self._get_linker_warning_arg( ),
			self._get_library_directory_args( ),
			self._get_linker_output_arg( output_file ),
			self._get_library_args( ),
			self._get_linker_obj_file_args( obj_list ) )


	def _get_preprocessor_definition_args( self ):
		define_args = ""

		# Add the defines.
		for define_name in self._project_settings.defines:
			define_args += "/D{} ".format( define_name )

		# Add the undefines.
		for define_name in self._project_settings.undefines:
			define_args += "/U{} ".format( define_name )

		return define_args


	def _get_architecture_arg( self ):
		#TODO: This will need to change to support other machine architectures.
		return "/MACHINE:{} ".format( "X64" if self._build_64_bit else "X86" )


	def _get_runtime_linkage_arg( self ):
		return "/{}{} ".format(
			"MT" if self._project_settings.static_runtime else "MD",
			"d" if self.settingsOverrides["debug_runtime"] else "" )


	def _get_runtime_library_arg( self ):
		return '/DEFAULTLIB:{}{}.lib '.format(
			"libcmt" if self._project_settings.static_runtime else "msvcrt",
			"d" if self.settingsOverrides["debug_runtime"] else "" )


	def _get_subsystem_arg( self ):
		# The default subsystem is implied, so it has no explicit argument.
		# When no argument is specified, the linker will assume a default subsystem which depends on a number of factors:
		#   CONSOLE -> Either main or wmain are defined (or int main(array<String^>^) for managed code).
		#   WINDOWS -> Either WinMain or wWinMain are defined (or WinMain(HINSTANCE*, HINSTANCE*, char*, int) or wWinMain(HINSTANCE*, HINSTANCE*, wchar_t*, int) for managed code).
		#   NATIVE -> The /DRIVER:WDM argument is specified (currently unsupported).
		if self._subsystem == SubSystem.DEFAULT:
			return ''

		sub_system_type = {
			SubSystem.CONSOLE: "CONSOLE",
			SubSystem.WINDOWS: "WINDOWS",
			SubSystem.WINDOWS_CE: "WINDOWSCE",
			SubSystem.NATIVE: "NATIVE",
			SubSystem.POSIX: "POSIX",
			SubSystem.BOOT_APPLICATION: "BOOT_APPLICATION",
			SubSystem.EFI_APPLICATION: "EFI_APPLICATION",
			SubSystem.EFI_BOOT_SERVICE_DRIVER: "EFI_BOOT_SERVICE_DRIVER",
			SubSystem.EFI_ROM: "EFI_ROM",
			SubSystem.EFI_RUNTIME_DRIVER: "EFI_RUNTIME_DRIVER" }

		return "/SUBSYSTEM:{} ".format( sub_system_type[self._subsystem] )


	def _get_library_args( self ):
		args = ""
		for lib in (
			self._project_settings.libraries +
			self._project_settings.static_libraries +
			self._project_settings.shared_libraries
		):
			found = False
			for depend in self._project_settings.linkDepends:
				if (
					_shared_globals.projects[depend].output_name.startswith( lib ) or
					_shared_globals.projects[depend].output_name.startswith( "lib{}.".format( lib ) )
				):
					found = True
					args += "{} ".format( _shared_globals.projects[depend].output_name )
			if not found:
				args += '{} '.format( self._actual_library_names[lib] )

		return args


	def _get_warning_args( self ):
		#TODO: Support additional warning options.
		if self._project_settings.no_warnings:
			return "/w "
		elif self._project_settings.warnings_as_errors:
			return "/WX "

		return ""


	def _get_linker_warning_arg( self ):
		# When linking, the only warning argument supported is whether or not to treat warnings as errors.
		return "/WX{} ".format( "" if self._project_settings.warnings_as_errors else ":NO" )


	def _get_include_directory_args( self ):
		include_dir_args = ""

		for inc_dir in self._project_settings.include_dirs:
			include_dir_args += '/I"{}" '.format( os.path.normpath( inc_dir ) )

		# The default include paths should be added last so that any paths set by the user get searched first.
		for inc_dir in self._include_path:
			include_dir_args += '/I"{}" '.format( inc_dir )

		return include_dir_args


	def _get_library_directory_args( self ):
		library_dir_args = ""

		for lib_dir in self._project_settings.library_dirs:
			library_dir_args += '/LIBPATH:"{}" '.format( os.path.normpath( lib_dir ) )

		return library_dir_args


	def _get_linker_output_arg( self, output_file ):
		return '/OUT:"{}" '.format( output_file )


	def _get_linker_obj_file_args( self, obj_file_list ):
		args = ""
		for obj_file in obj_file_list:
			args += '"{}" '.format( obj_file )

		return args


	### Public methods ###

	def getCompilerCommand( self, isCpp ):
		return "{}{}{}".format(
			self._get_compiler_exe( ),
			self._get_compiler_args( ),
			" ".join( self._project_settings.cpp_compiler_flags ) if isCpp else " ".join(
				self._project_settings.c_compiler_flags ) )


	def getExtendedCompilerArgs( self, base_cmd, force_include_file, output_obj, input_file ):
		pch = self.get_pch_file( force_include_file )
		if os.path.exists( pch ):
			pch = '/Fp"{0}"'.format( pch )
		else:
			pch = ""

		return '{}/Fo"{}" "{}" {} {} {}'.format(
			base_cmd,
			output_obj,
			input_file,
			'/FI"{}"'.format( force_include_file ) if force_include_file else "",
			'/Yu"{}"'.format( force_include_file ) if force_include_file else "",
			pch )


	def getExtendedPrecompilerArgs( self, base_cmd, force_include_file, output_obj, input_file ):
		return '{}/Yc"{}" /Fp"{}" /FI"{}" "{}"'.format(
			base_cmd,
			input_file,
			output_obj,
			input_file,
			'" "'.join( self._project_settings.allsources ) )


	def getLinkerCommand( self, output_file, obj_list ):
		return "{}{}{}".format(
			self._get_linker_exe( ),
			self._get_linker_args( output_file, obj_list ),
			" ".join( self._project_settings.linker_flags ) )


	### Required functions ###

	def find_library( self, project, library, library_dirs, force_static, force_shared ):
		libfile = "{}.lib".format( library )

		for lib_dir in library_dirs:
			lib_file_path = os.path.join( lib_dir, libfile )
			# Do a simple check to see if the file exists.
			if os.path.exists( lib_file_path ):
				self._actual_library_names.update( { library, libfile } )
				return lib_file_path

			#Compatibility with Linux's way of adding lib- to the front of its libraries
			libfile = "lib{}".format( libfile )
			lib_file_path = os.path.join( lib_dir, libfile )
			if os.path.exists( lib_file_path ):
				self._actual_library_names.update( { library, libfile } )
				return lib_file_path

		# The library wasn't found.
		return None


	def get_base_cxx_command( self, project ):
		self.SetupForProject( project )
		return self.getCompilerCommand( True )


	def get_base_cc_command( self, project ):
		self.SetupForProject( project )
		return self.getCompilerCommand( False )


	def get_link_command( self, project, outputFile, objList ):
		self.SetupForProject( project )
		return self.getLinkerCommand( outputFile, objList )


	def get_extended_command( self, baseCmd, project, forceIncludeFile, outObj, inFile ):
		self.SetupForProject( project )
		return self.getExtendedCompilerArgs( baseCmd, forceIncludeFile, outObj, inFile )


	def get_base_cxx_precompile_command( self, project ):
		return self.get_base_cxx_command( project )


	def get_base_cc_precompile_command( self, project ):
		return self.get_base_cc_command( project )


	def get_extended_precompile_command( self, baseCmd, project, forceIncludeFile, outObj, inFile ):
		self.SetupForProject( project )
		return self.getExtendedPrecompilerArgs( baseCmd, forceIncludeFile, outObj, inFile )


	def get_default_extension( self, projectType ):
		if projectType == csbuild.ProjectType.Application:
			return ".exe"
		elif projectType == csbuild.ProjectType.StaticLibrary:
			return ".lib"
		elif projectType == csbuild.ProjectType.SharedLibrary:
			return ".dll"


	def interrupt_exit_code( self ):
		return -1


	def get_pch_file( self, fileName ):
		return fileName.rsplit( ".", 1 )[0] + ".pch"


	def SetMsvcVersion( self, msvc_version ):
		"""
		Set the MSVC version

		@param msvc_version: The version to compile with
		@type msvc_version: int
		"""
		self.settingsOverrides["msvc_version"] = msvc_version


	def DebugRuntime( self ):
		"""
		Link with debug runtime
		"""
		self.settingsOverrides["debug_runtime"] = True
		self.settingsOverrides["debug_runtime_set"] = True


	def ReleaseRuntime( self ):
		"""
		Link with release runtime
		"""
		self.settingsOverrides["debug_runtime"] = False
		self.settingsOverrides["debug_runtime_set"] = True


	def SetOutputSubSystem( self, subsystem ):
		"""
		Sets the subsystem to compile against

		@param subsystem: The subsystem to be used to compile
		@type subsystem: A SubSystem enum value
		"""
		self._subsystem = subsystem


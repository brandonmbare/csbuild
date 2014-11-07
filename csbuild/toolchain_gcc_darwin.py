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
Contains a plugin class for interfacing with GCC/Clang on MacOSX.
"""

import os
import platform
import csbuild

from . import _shared_globals
from . import toolchain_gcc
from . import log


class GccDarwinBase( object ):
	def __init__( self ):
		# Default the target SDK version to the version of OSX we're currently running on.
		macVersion = platform.mac_ver()[0]
		defaultSdkVersion = ".".join( macVersion.split( "." )[:2] )
		self.SetTargetMacVersion( defaultSdkVersion )


	def _copyTo( self, other ):
		other._targetMacVersion = self._targetMacVersion
		other._sysroot = self._sysroot


	def SetTargetMacVersion( self, version ):
		"""
		Set the version of MacOSX to target and the sysroot of the SDK for that version.

		:param version: Version of MacOSX to target. Possible values are "10.9", "10.10", etc.
		:type version: str
		"""
		self._targetMacVersion = version
		self._sysroot = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX{}.sdk".format( self._targetMacVersion )


	def GetTargetMacVersion( self ):
		"""
		Retrieve the target of MacOSX that is being targetted.

		:return: str
		"""
		return self._targetMacVersion


	def _getSysRoot( self ):
		return '-isysroot "{}" '.format( self._sysroot )


class GccCompilerDarwin( GccDarwinBase, toolchain_gcc.GccCompiler ):
	def __init__( self ):
		GccDarwinBase.__init__( self )
		toolchain_gcc.GccCompiler.__init__( self )

		# Force the use of clang for now since that's what is typically used on Mac.
		self._settingsOverrides["cxx"] = "clang++"
		self._settingsOverrides["cc"] = "clang"


	def copy(self):
		ret = toolchain_gcc.GccCompiler.copy( self )
		GccDarwinBase._copyTo( self, ret )
		return ret


	def _getNoCommonFlag( self, project ):
		if project.type == csbuild.ProjectType.SharedLibrary or project.type == csbuild.ProjectType.LoadableModule:
			return "-fno-common "
		else:
			return ""


	def _getBaseCommand( self, compiler, project, isCpp ):
		ret = toolchain_gcc.GccCompiler._getBaseCommand( self, compiler, project, isCpp )
		ret = "{}{}{} ".format(
			ret,
			self._getSysRoot(),
			self._getNoCommonFlag( project ),
		)
		return ret


class GccLinkerDarwin( GccDarwinBase, toolchain_gcc.GccLinker ):
	def __init__( self ):
		GccDarwinBase.__init__( self )
		toolchain_gcc.GccLinker.__init__( self )

		self._settingsOverrides["cxx"] = "clang++"
		self._settingsOverrides["cc"] = "clang"


	def copy( self ):
		ret = toolchain_gcc.GccLinker.copy( self )
		GccDarwinBase._copyTo( self, ret )
		return ret


	def InterruptExitCode( self ):
		return 2


	def _getFrameworkDirectories(self, project):
		ret = ""
		for directory in project.frameworkDirs:
			ret += "-F{} ".format(directory)
		return ret


	def _getFrameworks(self, project):
		ret = ""
		for framework in project.frameworks:
			ret += "-framework {} ".format(framework)
		return ret


	def _getSharedLibraryFlag( self, project ):
		flagMap = {
			csbuild.ProjectType.SharedLibrary: "-dynamiclib ",
			csbuild.ProjectType.LoadableModule: "-bundle ",
		}

		return flagMap[project.type] if project.type in flagMap else ""


	def _setupForProject( self, project ):
		self._include_lib64 = False
		self._project_settings = project

		# Only include lib64 if we're on a 64-bit platform and we haven't specified whether to build a 64bit or 32bit
		# binary or if we're explicitly told to build a 64bit binary.
		if project.outputArchitecture == "x64":
			self._include_lib64 = True


	def _getLibraryArg(self, lib):
		for depend in self._project_settings.reconciledLinkDepends:
			dependProj = _shared_globals.projects[depend]
			if dependProj.type == csbuild.ProjectType.Application:
				continue
			dependLibName = dependProj.outputName
			splitName = os.path.splitext(dependLibName)[0]
			if splitName == lib or splitName == "lib{}".format( lib ):
				return "{} ".format( os.path.join( dependProj.outputDir, dependLibName ) )
		return "{} ".format( self._actual_library_names[lib] )


	def _getLibraryDirs( self, libDirs, forLinker ):
		"""Libraries are linked with full paths on Mac, so library directories are unnecessary."""
		return ""


	def _getStartGroupFlags(self):
		# OSX doesn't support the start/end group flags.
		return ""


	def _getEndGroupFlags(self):
		# OSX doesn't support he start/end group flags.
		return ""

	def _getObjcAbiVersionArg(self):
		return "-Xlinker -objc_abi_version -Xlinker {} ".format( self._objcAbiVersion )


	def GetLinkCommand( self, project, outputFile, objList ):
		ret = toolchain_gcc.GccLinker.GetLinkCommand( self, project, outputFile, objList )
		if project.type != csbuild.ProjectType.StaticLibrary:
			ret = "{}{}{}{} -ObjC ".format(
				ret,
				self._getSysRoot(),
				self._getFrameworkDirectories( project ),
				self._getFrameworks( project ),
			)
		return ret


	def FindLibrary( self, project, library, libraryDirs, force_static, force_shared ):
		self._setupForProject(project)

		for lib_dir in libraryDirs:
			log.LOG_INFO("Looking for library {} in directory {}...".format(library, lib_dir))
			lib_file_path = os.path.join( lib_dir, library )
			libFileStatic = "{}.a".format( lib_file_path )
			libFileDynamic = "{}.dylib".format( lib_file_path )
			# Check for a static lib.
			if os.access(libFileStatic , os.F_OK):
				self._actual_library_names.update( { library : libFileStatic } )
				return libFileStatic
			# Check for a dynamic lib.
			if os.access(libFileDynamic , os.F_OK):
				self._actual_library_names.update( { library : libFileDynamic } )
				return libFileDynamic

		for lib_dir in libraryDirs:
			# Compatibility with Linux's way of adding lib- to the front of its libraries
			libfileCompat = "lib{}".format( library )
			log.LOG_INFO("Looking for library {} in directory {}...".format(libfileCompat, lib_dir))
			lib_file_path = os.path.join( lib_dir, libfileCompat )
			libFileStatic = "{}.a".format( lib_file_path )
			libFileDynamic = "{}.dylib".format( lib_file_path )
			# Check for a static lib.
			if os.access(libFileStatic , os.F_OK):
				self._actual_library_names.update( { library : libFileStatic } )
				return libFileStatic
			# Check for a dynamic lib.
			if os.access(libFileDynamic , os.F_OK):
				self._actual_library_names.update( { library : libFileDynamic } )
				return libFileDynamic

		# The library wasn't found.
		return None


	def GetDefaultOutputExtension( self, projectType ):
		if projectType == csbuild.ProjectType.Application:
			return ""
		elif projectType == csbuild.ProjectType.StaticLibrary:
			return ".a"
		elif projectType == csbuild.ProjectType.SharedLibrary:
			return ".dylib"
		elif projectType == csbuild.ProjectType.LoadableModule:
			return ".bundle"

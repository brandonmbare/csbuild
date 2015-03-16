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
Contains a plugin class for building iOS projects.
"""

import csbuild

from . import toolchain_gcc
from . import toolchain_gcc_darwin


class iOSArchitecture( object ):
	DEVICE_ARMV7 =   "device-armv7"
	DEVICE_ARM64 =   "device-arm64"
	SIMULATOR_I386 = "simulator-i386"
	SIMULATOR_X64 =  "simulator-x64"


class iOSBase( object ):
	def __init__( self ):
		self.shared._targetDeviceVersion = "8.1"
		self.shared._targetSimulatorVersion = "8.1"


	def _copyTo( self, other ):
		other.shared._targetDeviceVersion = self.shared._targetDeviceVersion
		other.shared._targetSimulatorVersin = self.shared._targetSimulatorVersion


	def GetDefaultArchitecture( self ) :
		return iOSArchitecture.SIMULATOR_X64


	def GetValidArchitectures( self ):
		return [iOSArchitecture.DEVICE_ARMV7, iOSArchitecture.DEVICE_ARM64, iOSArchitecture.SIMULATOR_I386, iOSArchitecture.SIMULATOR_X64]


	def SetTargetDeviceVersion( self, version ):
		"""
		Set the target device version to compile against.

		:param version: Target device version.
		:type version: str
		"""
		self.shared._targetDeviceVersion = version


	def SetTargetSimulatorVersion( self, version ):
		"""
		Set the target simulator version to compile against.

		:param version: Target simulator version.
		:type version: str
		"""
		self.shared._targetSimulatorVersion = version


	def GetTargetDeviceVersion( self ):
		return self.shared._targetDeviceVersion


	def GetTargetSimulatorVersion( self ):
		return self.shared._targetSimulatorVersion


	def _getMinVersionArg( self, arch ):
		argumentMap = {
			iOSArchitecture.DEVICE_ARMV7:   "-miphoneos-version-min={} ".format( self.shared._targetDeviceVersion ),
			iOSArchitecture.DEVICE_ARM64:   "-miphoneos-version-min={} ".format( self.shared._targetDeviceVersion ),
			iOSArchitecture.SIMULATOR_I386: "-mios-simulator-version-min={} ".format( self.shared._targetSimulatorVersion ),
			iOSArchitecture.SIMULATOR_X64:  "-mios-simulator-version-min={} ".format( self.shared._targetSimulatorVersion ),
		}
		return argumentMap[arch]


	def _getArchitectureArg( self, arch ):
		argumentMap = {
			iOSArchitecture.DEVICE_ARMV7:   "armv7",
			iOSArchitecture.DEVICE_ARM64:   "arm64",
			iOSArchitecture.SIMULATOR_I386: "i386",
			iOSArchitecture.SIMULATOR_X64:  "x86_64",
		}
		return "-arch {} ".format( argumentMap[arch] )


	def _getAugmentedCommand( self, originalCmd, project ):
		return "{} {}{}".format(
			originalCmd,
			self._getMinVersionArg( project.outputArchitecture ),
			self._getArchitectureArg( project.outputArchitecture ),
		)


	def _setSysRoot( self, arch ):
		sysRootMap = {
			iOSArchitecture.DEVICE_ARMV7:   "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS{}.sdk".format( self.shared._targetDeviceVersion ),
			iOSArchitecture.DEVICE_ARM64:   "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS{}.sdk".format( self.shared._targetDeviceVersion ),
			iOSArchitecture.SIMULATOR_I386: "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator{}.sdk".format( self.shared._targetSimulatorVersion ),
			iOSArchitecture.SIMULATOR_X64:  "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator{}.sdk".format( self.shared._targetSimulatorVersion ),
		}
		self.shared._sysroot = sysRootMap[arch]


class iOSCompiler( iOSBase, toolchain_gcc_darwin.GccCompilerDarwin ):
	def __init__( self, shared ):
		toolchain_gcc_darwin.GccCompilerDarwin.__init__( self, shared )
		iOSBase.__init__( self )


	def copy( self, shared ):
		ret = toolchain_gcc_darwin.GccCompilerDarwin.copy( self, shared )
		iOSBase._copyTo( self, ret )
		return ret


	def _getArchFlag( self, project ):
		# iOS builds should not receive the -m32 or -m64 flags when compiling for iOS.
		return ""


	def _getBaseCommand( self, compiler, project, isCpp ):
		return "{} ".format( toolchain_gcc_darwin.GccCompilerDarwin._getBaseCommand( self, compiler, project, isCpp ) )


	def GetBaseCcCommand( self, project ):
		self._setSysRoot( project.outputArchitecture )
		originalCmd = toolchain_gcc.GccCompiler.GetBaseCcCommand( self, project )
		return self._getAugmentedCommand( originalCmd, project )


	def GetBaseCxxCommand( self, project ):
		self._setSysRoot( project.outputArchitecture )
		originalCmd = toolchain_gcc.GccCompiler.GetBaseCxxCommand( self, project )
		return self._getAugmentedCommand( originalCmd, project )


class iOSLinker( iOSBase, toolchain_gcc_darwin.GccLinkerDarwin ):
	def __init__( self, shared ):
		toolchain_gcc_darwin.GccLinkerDarwin.__init__( self, shared )
		iOSBase.__init__( self )


	def copy( self, shared ):
		ret = toolchain_gcc_darwin.GccLinkerDarwin.copy( self, shared )
		iOSBase._copyTo( self, ret )
		return ret


	def _getArchFlag( self, project ):
		# iOS builds should not receive the -m32 or -m64 flags.
		return ""


	def GetLinkCommand( self, project, outputFile, objList ):
		self._setSysRoot( project.outputArchitecture )
		originalCmd = toolchain_gcc_darwin.GccLinkerDarwin.GetLinkCommand( self, project, outputFile, objList )
		if project.type != csbuild.ProjectType.StaticLibrary:
			ret =  "{} -Xlinker -no_implicit_dylibs ".format( self._getAugmentedCommand( originalCmd, project ) )
		else:
			ret = originalCmd
		return ret

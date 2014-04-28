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
Contains a plugin class for creating android NDK projects
"""
import glob
import platform

from csbuild import toolchain_gcc
import os

class AndroidBase( object ):
	def __init__(self):
		self._ndkHome = os.getenv("NDK_HOME")
		self._sdkHome = os.getenv("ANDROID_HOME")
		self._javaHome = os.getenv("JAVA_HOME")

	def NdkHome(self, pathToNdk):
		self._ndkHome = pathToNdk

	def SdkHome(self, pathToSdk):
		self._sdkHome = pathToSdk

	def JavaHome(self, pathToJava):
		self._javaHome = pathToJava


class compiler_android(AndroidBase, toolchain_gcc.compiler_gcc):
	def __init__(self):
		AndroidBase.__init__(self)
		toolchain_gcc.compiler_gcc.__init__(self)

		self._toolchainPath = ""
		self._setupCompleted = False

	def GetCompiler(self, project):
		#TODO: Let user choose which compiler version to use; for now, using the highest numbered version.
		toolchainsDir = os.path.join(self._ndkHome, "toolchains")
		dirs = glob.glob(os.path.join(toolchainsDir, "{}*".format(project.outputArchitecture)))

		bestClang = ""
		bestGcc = ""

		for dirname in dirs:
			prebuilt = os.path.join(toolchainsDir, dirname, "prebuilt")
			if not os.path.exists(prebuilt):
				continue

			if "llvm" in dirname:
				if dirname > bestClang:
					bestClang = dirname
			else:
				if dirname > bestGcc:
					bestGcc = dirname

		if platform.system() == "Windows":
			platformName = "windows-x86_64"
		else:
			platformName = "linux-x86_64"

		if self.isClang:
			compilerDir = bestClang
			ccName = "clang"
			cxxName = "clang++"
		else:
			compilerDir = bestGcc
			ccName = "gcc"
			cxxName = "g++"

		binDir = os.path.join(toolchainsDir, compilerDir, "prebuilt", platformName, "bin")
		self.settingsOverrides["cc"] = os.path.join(binDir, ccName)
		self.settingsOverrides["cxx"] = os.path.join(binDir, cxxName)

	def SetupForProject( self, project ):
		toolchain_gcc.compiler_gcc.SetupForProject(self, project)
		if not self._setupCompleted:
			self.GetCompiler(project)
			self._setupCompleted = True




class linker_android(AndroidBase, toolchain_gcc.linker_gcc):
	pass

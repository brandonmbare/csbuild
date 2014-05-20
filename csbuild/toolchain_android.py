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
import os
import shutil
import subprocess
import sys
import shlex
import re

from csbuild import toolchain_gcc
from csbuild import log
from csbuild import _shared_globals
import csbuild

class AndroidBase( object ):
	def __init__(self):
		self._ndkHome = os.getenv("NDK_HOME")
		self._sdkHome = os.getenv("ANDROID_HOME")
		self._antHome = os.getenv("ANT_HOME")
		self._adkVersion = 19

	def NdkHome(self, pathToNdk):
		self._ndkHome = pathToNdk

	def SdkHome(self, pathToSdk):
		self._sdkHome = pathToSdk

	def AntHome(self, pathToAnt):
		self._antHome = pathToAnt

	def AdkVersion(self, adkVersion):
		self._adkVersion = adkVersion

	def GetValidArchitectures(self):
		return ['x86', 'arm', 'armv7', 'mips']


class AndroidCompiler(AndroidBase, toolchain_gcc.compiler_gcc):
	def __init__(self):
		AndroidBase.__init__(self)
		toolchain_gcc.compiler_gcc.__init__(self)

		self._toolchainPath = ""
		self._setupCompleted = False

	def postPrepareBuildStep(self, project):
		appGlueDir = os.path.join( self._ndkHome, "sources", "android", "native_app_glue" )
		project.include_dirs.append(appGlueDir)
		project.extraDirs.append(appGlueDir)
		project.RediscoverFiles()

	def _SetupCompiler(self, project):
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

		if not bestGcc:
			log.LOG_ERROR("Architecture {} is not supported by the android toolchain.".format(project.outputArchitecture))
			csbuild.Exit(1)

		if platform.system() == "Windows":
			platformName = "windows-x86_64"
			ext = ".exe"
		else:
			platformName = "linux-x86_64"
			ext = ""

		if self.isClang:
			compilerDir = bestClang
			ccName = "clang" + ext
			cxxName = "clang++" + ext
		else:
			compilerDir = bestGcc
			ccName = "gcc" + ext
			cxxName = "g++" + ext

		binDir = os.path.join(toolchainsDir, compilerDir, "prebuilt", platformName, "bin")
		maybecc = os.path.join(binDir, ccName)

		if os.path.exists(maybecc):
			cc = maybecc
			cxx = os.path.join(binDir, cxxName)
		else:
			dirs = list(glob.glob(os.path.join(binDir, "*-{}".format(ccName))))
			prefix = dirs[0].rsplit('-', 1)[0]
			cc = dirs[0]
			cxx = "{}-{}".format(prefix, cxxName)

		print "CC IS ", cc
		self.settingsOverrides["cc"] = cc
		self.settingsOverrides["cxx"] = cxx

	def SetupForProject( self, project ):
		#toolchain_gcc.compiler_gcc.SetupForProject(self, project)
		if not self._setupCompleted:
			self._SetupCompiler(project)
			self._setupCompleted = True

	def prePrepareBuildStep(self, project):
		self.SetupForProject(project)

	def get_base_command( self, compiler, project, isCpp ):
		self.SetupForProject(project)

		exitcodes = "-pass-exit-codes"

		if isCpp:
			standard = self.cppStandard
		else:
			standard = self.cStandard

		return "\"{}\" {} -Winvalid-pch -c {}-g{} -O{} {}{}{} {} {} --sysroot \"{}\"".format(
			compiler,
			exitcodes,
			self.get_defines( project.defines, project.undefines ),
			project.debug_level,
			project.opt_level,
			"-fPIC " if project.type == csbuild.ProjectType.SharedLibrary else "",
			"-pg " if project.profile else "",
			"--std={0}".format( standard ) if standard != "" else "",
			" ".join( project.cpp_compiler_flags ) if isCpp else " ".join( project.c_compiler_flags ),
			"-isystem \"{}\"".format(os.path.join( self._ndkHome, "sources", "cxx-stl", "stlport", "stlport")) if isCpp else "",
			os.path.join( self._ndkHome, "platforms", "android-{}".format(self._adkVersion), "arch-{}".format(project.outputArchitecture))
		)


class AndroidLinker(AndroidBase, toolchain_gcc.linker_gcc):
	def __init__(self):
		AndroidBase.__init__(self)
		toolchain_gcc.linker_gcc.__init__(self)
		self._setupCompleted = False

	def _SetupLinker(self, project):
		#TODO: Let user choose which compiler version to use; for now, using the highest numbered version.
		toolchainsDir = os.path.join(self._ndkHome, "toolchains")
		dirs = glob.glob(os.path.join(toolchainsDir, "{}*".format(project.outputArchitecture)))

		compilerDir = ""

		for dirname in dirs:
			prebuilt = os.path.join(toolchainsDir, dirname, "prebuilt")
			if not os.path.exists(prebuilt):
				continue

			if "llvm" in dirname:
				continue

			if dirname > compilerDir:
				compilerDir = dirname

		if not compilerDir:
			log.LOG_ERROR("Architecture {} is not supported by the android toolchain.".format(project.outputArchitecture))

		if platform.system() == "Windows":
			platformName = "windows-x86_64"
			ext = ".exe"
		else:
			platformName = "linux-x86_64"
			ext = ""

		ldName = "ld" + ext
		arName = "ar" + ext

		binDir = os.path.join(toolchainsDir, compilerDir, "prebuilt", platformName, "bin")
		maybeld = os.path.join(binDir, ldName)

		if os.path.exists(maybeld):
			ld = maybeld
			ar = os.path.join(binDir, arName)
		else:
			dirs = list(glob.glob(os.path.join(binDir, "*-{}".format(ldName))))
			prefix = dirs[0].rsplit('-', 1)[0]
			ld = dirs[0]
			ar = "{}-{}".format(prefix, arName)

		self._ld = ld
		self._ar = ar

	def SetupForProject( self, project ):
		toolchain_gcc.linker_gcc.SetupForProject(self, project)
		if not self._setupCompleted:
			self._SetupLinker(project)
			self._setupCompleted = True


	def get_link_command( self, project, outputFile, objList ):
		self.SetupForProject( project )
		if project.type == csbuild.ProjectType.StaticLibrary:
			return "\"{}\" rcs {} {}".format( self._ar, outputFile, " ".join( objList ) )
		else:
			if project.hasCppFiles:
				cmd = project.activeToolchain.Compiler().settingsOverrides["cxx"]
			else:
				cmd = project.activeToolchain.Compiler().settingsOverrides["cc"]

			return "\"{}\" {}-o{} {} {} {} {}{}{} {} {}-g{} -O{} {} {} {} --sysroot \"{}\" -L \"{}\"".format(
				cmd,
				"-pg " if project.profile else "",
				outputFile,
				" ".join( objList ),
				"-static-libgcc -static-libstdc++ " if project.static_runtime else "",
				"-Wl,--no-as-needed -Wl,--start-group" if not self.strictOrdering else "",
				self.get_libraries( project.libraries ),
				self.get_static_libraries( project.static_libraries ),
				self.get_shared_libraries( project.shared_libraries ),
				"-Wl,--end-group" if not self.strictOrdering else "",
				self.get_library_dirs( project.library_dirs, True ),
				project.debug_level,
				project.opt_level,
				"-shared" if project.type == csbuild.ProjectType.SharedLibrary else "",
				" ".join( project.linker_flags ),
				"-L\"{}\" -lstlport_static".format(os.path.join( self._ndkHome, "sources", "cxx-stl", "stlport", "libs", "armeabi")) if project.hasCppFiles else "",
				os.path.join( self._ndkHome, "platforms", "android-{}".format(self._adkVersion), "arch-{}".format(project.outputArchitecture)),
				os.path.join( self._ndkHome, "platforms", "android-{}".format(self._adkVersion), "arch-{}".format(project.outputArchitecture), "usr", "lib")
			)

	def find_library( self, project, library, library_dirs, force_static, force_shared ):
		success = True
		out = ""
		self.SetupForProject( project )
		try:
			if _shared_globals.show_commands:
				print("{} -o /dev/null --verbose {} {} -l{}".format(
					self._ld,
					self.get_library_dirs( library_dirs, False ),
					"-static" if force_static else "-shared" if force_shared else "",
					library ))
			cmd = [self._ld, "-o", "/dev/null", "--verbose",
				   "-static" if force_static else "-shared" if force_shared else "", "-l{}".format( library ),
				   "--sysroot", os.path.join( self._ndkHome, "platforms", "android-{}".format(self._adkVersion), "arch-{}".format(project.outputArchitecture))]
			cmd += shlex.split( self.get_library_dirs( library_dirs, False ) )
			out = subprocess.check_output( cmd, stderr = subprocess.STDOUT )
		except subprocess.CalledProcessError as e:
			out = e.output
			success = False
		finally:
			if sys.version_info >= (3, 0):
				RMatch = re.search( "attempt to open (.*) succeeded".encode( 'utf-8' ), out, re.I )
			else:
				RMatch = re.search( "attempt to open (.*) succeeded", out, re.I )
				#Some libraries (such as -liberty) will return successful but don't have a file (internal to ld maybe?)
			#In those cases we can probably assume they haven't been modified.
			#Set the mtime to 0 and return success as long as ld didn't return an error code.
			if RMatch is not None:
				lib = RMatch.group( 1 )
				return lib
			elif not success:
				return None

	def prePrepareBuildStep(self, project):
		#Everything on Android has to build as a shared library
		project.metaType = project.type
		project.type = csbuild.ProjectType.SharedLibrary
		if not project.output_name.startswith("lib"):
			project.output_name = "lib{}".format(project.output_name)

	def postBuildStep(self, project):
		if project.metaType != csbuild.ProjectType.Application:
			return

		appDir = os.path.join(project.csbuild_dir, "apk", project.name)
		if os.path.exists(appDir):
			shutil.rmtree(appDir)

		androidTool = os.path.join(self._sdkHome, "tools", "android.bat" if platform.system() == "Windows" else "android.sh")
		fd = subprocess.Popen(
			[
				androidTool, "create", "project",
				"--path", appDir,
				"--target", "android-{}".format(self._adkVersion),
				"--name", project.name,
				"--package", "com.csbuild.autopackage.{}".format(project.name),
				"--activity", "CSBNativeAppActivity"
			]
		)
		ret = fd.communicate()
		libDir = ""
		if project.outputArchitecture == "x86":
			libDir = "x86"
		elif project.outputArchitecture == "mips":
			libDir = "mips"
		elif project.outputArchitecture == "arm":
			libDir = "armeabi-v7a"
		else:
			libDir = "armeabi"

		libDir = os.path.join(appDir, "libs", libDir)

		if not os.path.exists(libDir):
			os.makedirs(libDir)

		for library in project.library_locs:
			#don't copy android system libraries
			if library.startswith(self._ndkHome):
				continue
			shutil.copyfile(library, os.path.join(libDir, os.path.basename(library)))

		for dep in project.linkDepends:
			depProj = _shared_globals.projects[dep]
			libFile = os.path.join(depProj.output_dir, depProj.output_name)
			shutil.copyfile(libFile, os.path.join(libDir, os.path.basename(libFile)))

		shutil.copyfile(os.path.join(project.output_dir, project.output_name), os.path.join(libDir, os.path.basename(project.output_name)))

		with open(os.path.join(appDir, "AndroidManifest.xml"), "w") as f:
			f.write("<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\"\n")
			f.write("  package=\"com.csbuild.autopackage.{}\"\n".format(project.name))
			f.write("  android:versionCode=\"1\"\n")
			f.write("  android:versionName=\"1.0\">\n")
			f.write("  <uses-sdk android:minSdkVersion=\"{}\" android:targetSdkVersion=\"{}\"/>\n".format(self._adkVersion, self._adkVersion))
			#TODO: f.write("  <uses-feature android:glEsVersion=\"0x00020000\"></uses-feature>")
			f.write("  <application android:label=\"{}\" android:hasCode=\"false\">\n".format(project.name))
			f.write("    <activity android:name=\"android.app.NativeActivity\"\n")
			f.write("      android:label=\"{}\">\n".format(project.name))
			f.write("      android:configChanges=\"orientation|keyboardHidden\">\n")
			f.write("      <meta-data android:name=\"android.app.lib_name\" android:value=\"{}\"/>\n".format(project.output_name[3:-3]))
			f.write("      <intent-filter>\n")
			f.write("        <action android:name=\"android.intent.action.MAIN\"/>\n")
			f.write("        <category android:name=\"android.intent.category.LAUNCHER\"/>\n")
			f.write("      </intent-filter>\n")
			f.write("    </activity>\n")
			f.write("  </application>\n")
			f.write("</manifest>\n")

		if project.debug_level != csbuild.DebugLevel.Disabled:
			antBuildType = "debug"
		else:
			antBuildType = "release"

		fd = subprocess.Popen([os.path.join(self._antHome, "bin", "ant.bat" if platform.system() == "Windows" else "ant.sh"), antBuildType], cwd=appDir)
		ret = fd.communicate()


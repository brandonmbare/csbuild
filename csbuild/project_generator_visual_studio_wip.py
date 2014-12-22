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

import argparse
import codecs
import hashlib
import os
import tempfile
import uuid

import csbuild
from . import project_generator
from . import projectSettings
from . import log
from . import _shared_globals

from .vsgen.platform_windows import *
from .vsgen.platform_android import *


class VisualStudioVersion:
	v2010 = 2010
	v2012 = 2012
	v2013 = 2013
	All = [v2010, v2012, v2013]


class PlatformManager:
	def __init__( self ):
		self._availablePlatformMap = dict() # Maps the visual studio names to the classes (not class instances).
		self._toolchainLookupMap = dict() # Maps the toolchain names to the visual studio names.
		self._registeredPlatformMap = dict() # Maps the visual studio names to the class instances.

		self._makePlatformAvailable( PlatformWindowsX86 )
		self._makePlatformAvailable( PlatformWindowsX64 )
		self._makePlatformAvailable( PlatformTegraAndroid )


	@staticmethod
	def Get():
		if not hasattr(PlatformManager.Get, "instance"):
			PlatformManager.Get.instance = PlatformManager()
		return PlatformManager.Get.instance


	def _makePlatformAvailable(self, cls):
		self._availablePlatformMap.update( { cls.GetVisualStudioName(): cls } )
		self._toolchainLookupMap.update( { cls.GetToolchainName(): cls.GetVisualStudioName() } )


	def GetAvailableNameList( self ):
		return sorted( list( self._availablePlatformMap ) )


	def GetRegisteredNameList( self ):
		return sorted( list( self._registeredPlatformMap ) )


	def RegisterPlatform(self, name):
		if not name in self._availablePlatformMap:
			log.LOG_ERROR( "Unknown vsgen platform: {}".format( name ) )
			return
		platformClass = self._availablePlatformMap[name]
		self._registeredPlatformMap.update( { name: platformClass() } )


	def GetPlatformFromToolchainName( self, name ):
		if not name in self._toolchainLookupMap:
			return None
		visualStudioName = self._toolchainLookupMap[name]
		if not visualStudioName in self._registeredPlatformMap:
			return None
		return self._registeredPlatformMap[visualStudioName]


def GetImpliedVisualStudioVersion():
	msvcVersion = csbuild.Toolchain( "msvc" ).Compiler().GetMsvcVersion()
	msvcToVisualStudioMap = {
		100: VisualStudioVersion.v2010,
		110: VisualStudioVersion.v2012,
		120: VisualStudioVersion.v2013,
	}
	return msvcToVisualStudioMap[msvcVersion] if msvcVersion in msvcToVisualStudioMap else VisualStudioVersion.v2012


def GenerateNewUuid( uuidList, name ):
	nameIndex = 0
	nameToHash = name

	# Keep generating new UUIDs until we've found one that isn't already in use. This is only useful in cases where we have a pool of objects
	# and each one needs to be guaranteed to have a UUID that doesn't collide with any other object in the same pool.  Though, because of the
	# way UUIDs work, having a collision should be extremely rare anyway.
	while True:
		newUuid = uuid.uuid5( uuid.NAMESPACE_OID, nameToHash )
		if not newUuid in uuidList:
			uuidList.add( newUuid )
			return newUuid

		# Name collision!  The easy solution here is to slightly modify the name in a predictable way.
		nameToHash = "{}{}".format( name, nameIndex )
		nameIndex += 1


def CorrectConfigName( configName ):
	# Visual Studio can be exceptionally picky about configuration names.  For instance, if your build script has the "debug" target,
	# you may run into problems with Visual Studio showing that alongside it's own "Debug" configuration, which is may have decided
	# to just add alongside your own.  The solution is to just put the configurations in a format it expects (first letter upper case,
	# the rest lowercase).  That way, it will see "Debug" already there and won't try to silently 'fix' that up for you.
	return configName.capitalize()


class Project( object ):
	"""
	Container class for Visual Studio projects.
	"""

	def __init__( self, name, globalProjectUuidList ):
		self.name = name
		self.outputPath = ""
		self.dependencyList = set()
		self.id = "{{{}}}".format( str( GenerateNewUuid( globalProjectUuidList, name ) ).upper() )
		self.isFilter = False
		self.isBuildAllProject = False
		self.isRegenProject = False
		self.fullSourceFileList = set()
		self.fullHeaderFileList = set()
		self.fullIncludePathList = set()
		self.fileFilterMap = {}
		self.makefilePath = ""


class CachedFileData:

	def __init__( self, outputFilePath, fileData, isUserFile ):
		self._outputFilePath = outputFilePath
		self._fileData = fileData
		self._isUserFile = isUserFile
		self._md5FileDataHash = hashlib.md5()
		self._md5FileDataHash.update( self._fileData )
		self._md5FileDataHash = self._md5FileDataHash.hexdigest()


	def SaveFile( self ):
		canWriteOutputFile = True
		if os.access( self._outputFilePath, os.F_OK ):
			# Any user files that already exist will be ignored to preserve user debug settings.
			if self._isUserFile and csbuild.GetOption( "vs-gen-replace-user-files" ):
				log.LOG_BUILD( "Ignoring: {}".format( self._outputFilePath ) )
				return

			with open( self._outputFilePath, "rb" ) as fileHandle:
				fileData = fileHandle.read()
				fileDataHash = hashlib.md5()
				fileDataHash.update( fileData )
				fileDataHash = fileDataHash.hexdigest()
				canWriteOutputFile = ( fileDataHash != self._md5FileDataHash )

		if canWriteOutputFile:
			log.LOG_BUILD( "Writing file {}...".format( self._outputFilePath ) )
			with open( self._outputFilePath, "wb" ) as fileHandle:
				fileHandle.write( self._fileData )
		else:
			log.LOG_BUILD( "Up-to-date: {}".format( self._outputFilePath ) )


class project_generator_visual_studio( project_generator.project_generator ):
	"""Generator used to create Visual Studio project files."""

	def __init__( self, path, solutionName, extraArgs ):
		project_generator.project_generator.__init__( self, path, solutionName, extraArgs )

		versionNumber = csbuild.GetOption("vs-gen-version")
		platformList = csbuild.GetOption("vs-gen-platform")

		if not versionNumber:
			versionNumber = GetImpliedVisualStudioVersion()
			log.LOG_BUILD( "No Visual Studio version selected; defaulting to {}.".format( versionNumber ) )

		# If the user did not specify any target platforms, add a default.
		if not platformList:
			defaultName = PlatformWindowsX64.GetVisualStudioName()
			platformList.append( defaultName )
			log.LOG_BUILD( "No platforms selected; defaulting to {}.".format( defaultName ) )

		# Register the selected platforms.
		platformManager = PlatformManager.Get()
		for platform in platformList:
			platformManager.RegisterPlatform(platform)

		self._createNativeProject = False #TODO: Implement support for native projects.
		self._visualStudioVersion = versionNumber
		self._projectMap = {}
		self._configList = []
		self._reverseConfigMap = {} # A reverse look-up map for the configuration names.
		self._extraBuildArgs = self.extraargs.replace(",", " ")
		self._fullIncludePathList = set() # Should be a set starting out so duplicates are eliminated.
		self._projectUuidList = set()
		self._orderedProjectList = []

		# Compile a list of the targets and a reverse-lookup list.
		for configName in _shared_globals.alltargets:
			correctedConfigName = CorrectConfigName(configName)
			self._configList.append(correctedConfigName)
			self._reverseConfigMap[correctedConfigName] = configName


	@staticmethod
	def AdditionalArgs( parser ):
		class ListExtendAction(argparse.Action):
			def __call__(self, _parser, namespace, values, option_string = None):
				if getattr(namespace, self.dest, None) is None:
					setattr(namespace, self.dest, [])

				getattr(namespace, self.dest).extend(values)

		#parser.add_argument(
		#	"--vs-gen-native",
		#    help = "Generate native Visual Studio projects.",
		#    action = "store_true",
		#)
		parser.add_argument(
			"--vs-gen-version",
			help = "Select the version of Visual Studio the generated solution will be compatible with.",
			choices = VisualStudioVersion.All,
			default = None,
			type = int,
		)
		parser.add_argument(
			"--vs-gen-replace-user-files",
			help = "When generating project files, do not ignore existing .vcxproj.user files.",
			action = "store_true",
		)
		parser.add_argument(
			"--vs-gen-platform",
		    help = "Desired platform to include in the generated project files. May be specified multiple times, once per platform.",
		    action = ListExtendAction,
		    default = [],
		    type = str,
		    choices = PlatformManager.Get().GetAvailableNameList(),
		)


	def WriteProjectFiles( self ):
		self._collectProjects()
		self._WriteSolutionFile()


	def _collectProjects( self ):
		platformManager = PlatformManager.Get()

		def recurseGroups( projectMap_out, parentFilter_out, projectOutputPath, projectGroup ):
			# Setup the projects first.
			for projectName, projectSettingsMap in projectGroup.projects.items():

				# Fill in the project data.
				projectData = Project( projectName, self._projectUuidList ) # Create a new object to contain project data.
				projectData.outputPath = os.path.join( self.rootpath, projectOutputPath )

				# Add the current project to the parent filter dependency list. In the case of filters,
				# this isn't really a depencency list, it's just a list of nested projects.
				if parentFilter_out:
					parentFilter_out.dependencyList.add( projectName )

				# Because the list of sources and headers can differ between configurations and architectures,
				# we need to generate a complete list so the project can reference them all.
				for toolchainName, configMap in projectSettingsMap.items():
					for configName, archMap in configMap.items():
						for archName, settings in archMap.items():

							configName = CorrectConfigName( configName )
							toolchainArchName = "{}-{}".format( toolchainName, archName )
							generatorPlatform = platformManager.GetPlatformFromToolchainName( toolchainArchName )

							# Only add the defines if the current toolchain is associated with a registered platform.
							if generatorPlatform:
								generatorPlatform.AddDefines( configName, projectName, settings.defines )

							projectData.fullSourceFileList.update( set( settings.allsources ) )
							projectData.fullHeaderFileList.update( set( settings.allheaders ) )
							projectData.fullIncludePathList.update( set( settings.includeDirs ) )

							# Construct the path that the files will show under in the Solution Explorer.
							for source in projectData.fullSourceFileList:
								projectData.fileFilterMap[source] = os.path.join( "Source Files", os.path.dirname( os.path.relpath( source, settings.workingDirectory ) ).replace( ".." + os.path.sep, "" ) ).rstrip( os.path.sep )
							for header in projectData.fullHeaderFileList:
								projectData.fileFilterMap[header] = os.path.join( "Header Files", os.path.dirname( os.path.relpath( header, settings.workingDirectory ) ).replace( ".." + os.path.sep, "" ) ).rstrip( os.path.sep )

				projectData.fullSourceFileList = sorted( projectData.fullSourceFileList )
				projectData.fullHeaderFileList = sorted( projectData.fullHeaderFileList )

				# Grab the projectSettings for the first key in the config map and fill in a set of names for dependent projects.
				# We only need the names for now. We can handle resolving them after we have all of the projects mapped.

				configMap = list( projectSettingsMap.values() )[0]
				archMap = list( configMap.values() )[0]
				settings = list( archMap.values() )[0]
				for dependentProjectKey in settings.linkDepends:
					projectData.dependencyList.add( _shared_globals.projects[dependentProjectKey].name )

				# Grab the path to this project's makefile.
				projectData.makefilePath = settings.scriptFile

				projectData.dependencyList = set( sorted( projectData.dependencyList ) ) # Sort the dependency list.
				projectMap_out[projectData.name] = projectData

			# Sort the parent filter dependency list.
			if parentFilter_out:
				parentFilter_out.dependencyList = set( sorted( parentFilter_out.dependencyList ) )

			# Next, iterate through each subgroup and handle each one recursively.
			for subGroupName, subGroup in projectGroup.subgroups.items():
				groupPath = os.path.join( projectOutputPath, subGroupName )

				groupPathFinal = os.path.join( self.rootpath, groupPath )

				filterData = Project( subGroupName, self._projectUuidList ) # Subgroups should be treated as project filters in the solution.
				filterData.isFilter = True

				# Explicitly map the filter names with a different name to help avoid possible naming collisions.
				projectMap_out["{}.Filter".format( filterData.name )] = filterData

				# Create the group path if it doesn't exist.
				if not os.access( groupPathFinal, os.F_OK ):
					os.makedirs( groupPathFinal )

				recurseGroups( projectMap_out, filterData, groupPath, subGroup )


		def resolveDependencies( projectMap ):
			for projectId, projectData in projectMap.items():
				resolvedDependencyList = []

				# Sort the dependency name list before parsing it.
				projectData.dependencyList = sorted( projectData.dependencyList)

				# Resolve each project name to their associated project objects.
				for dependentProjectName in projectData.dependencyList:
					resolvedDependencyList.append( projectMap[dependentProjectName] )

				# Replace the old name list with the new resolved list.
				projectData.dependencyList = resolvedDependencyList


		# Create the base output directory if necessary.
		if not os.access( self.rootpath, os.F_OK ):
			os.makedirs( self.rootpath )

		# When not creating a native project, a custom project must be injected in order to achieve full solution builds
		# since Visual Studio doesn't give us a way to override the behavior of the "Build Solution" command.
		if not self._createNativeProject:
			# Fill in the project data.
			buildAllProjectData = Project( "(BUILD_ALL)", self._projectUuidList ) # Create a new object to contain project data.
			buildAllProjectData.outputPath = self.rootpath
			buildAllProjectData.isBuildAllProject = True
			buildAllProjectData.makefilePath = csbuild.scriptFiles[0] # Reference the main makefile.

			regenProjectData = Project( "(REGENERATE_SOLUTION)", self._projectUuidList ) # Create a new object to contain project data.
			regenProjectData.outputPath = self.rootpath
			regenProjectData.isRegenProject = True
			regenProjectData.makefilePath = csbuild.scriptFiles[0] # Reference the main makefile.

			# Add the Build All and Regen projects to the project map.
			self._projectMap[buildAllProjectData.name] = buildAllProjectData
			self._projectMap[regenProjectData.name] = regenProjectData

		recurseGroups( self._projectMap, None, "", projectSettings.rootGroup )
		resolveDependencies( self._projectMap )

		# Copy the project names into a list.
		#for projectName, projectData in self._projectMap.items():
		#	self._orderedProjectList.append( projectName )

		# Sort the list of project names.
		self._orderedProjectList = sorted( list( self._projectMap ) )

		# Replace the list of names in the project list with the actual project data.
		for i in range( 0, len( self._orderedProjectList ) ):
			projectName = self._orderedProjectList[i]
			self._orderedProjectList[i] = self._projectMap[projectName]

		# Create a single list of every include search path.
		for projectName, projectData in self._projectMap.items():
			self._fullIncludePathList.update( projectData.fullIncludePathList )

		self._fullIncludePathList = sorted( self._fullIncludePathList )


	def _WriteSolutionFile( self ):

		def writeLineToFile( indentLevel, fileHandle, stringToWrite ):
			fileHandle.write( "{}{}\r\n".format( "\t" * indentLevel, stringToWrite ) )

		platformManager = PlatformManager.Get()
		registeredPlatformList = platformManager.GetRegisteredNameList()

		fileFormatVersionNumber = {
			2010: "11.00",
			2012: "12.00",
			2013: "12.00",
		}

		tempRootPath = tempfile.mkdtemp()
		finalSolutionPath = "{}.sln".format( os.path.join( self.rootpath, self.solutionname ) )
		tempSolutionPath = "{}.sln".format( tempRootPath, self.solutionname )

		# Create the temporary root path.
		if not os.access( tempRootPath, os.F_OK ):
			os.makedirs( tempRootPath )

		# Visual Studio solution files need to be UTF-8 with the byte order marker because Visual Studio is VERY picky about these files.
		# If ANYTHING is missing or not formatted properly, the Visual Studio version selector may not open the right version or Visual
		# Studio itself may refuse to even attempt to load the file.
		with codecs.open( tempSolutionPath, "w", "utf-8-sig" ) as fileHandle:
			writeLineToFile( 0, fileHandle, "" ) # Required empty line.
			writeLineToFile( 0, fileHandle, "Microsoft Visual Studio Solution File, Format Version {}".format( fileFormatVersionNumber[self._visualStudioVersion] ) )
			writeLineToFile( 0, fileHandle, "# Visual Studio {}".format( self._visualStudioVersion ) )

			projectFilterList = []

			for projectData in self._orderedProjectList:
				if not projectData.isFilter:
					relativeProjectPath = os.path.relpath( projectData.outputPath, self.rootpath )
					projectFilePath = os.path.join( relativeProjectPath, "{}.vcxproj".format( projectData.name ) )
					nodeId = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"
				else:
					projectFilePath = projectData.name
					nodeId = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"

					# Keep track of the filters because we need to record those after the projects.
					projectFilterList.append( projectData )

				beginProject = 'Project("{}") = "{}", "{}", "{}"'.format( nodeId, projectData.name, projectFilePath, projectData.id )

				writeLineToFile( 0, fileHandle, beginProject )

				# Only write out project dependency information if the current project has any dependencies and if we're creating a native project.
				# If we're not creating a native project, it doesn't matter since csbuild will take care of all that for us behind the scenes.
				# Also, don't list any dependencies for filters. Those will be written out under NestedProjects.
				if self._createNativeProject and not projectData.isFilter and len( projectData.dependencyList ) > 0:
					writeLineToFile( 1, fileHandle, "ProjectSection(ProjectDependencies) = postProject" )

					# Write out the IDs for each dependent project.
					for dependentProjectData in projectData.dependencyList:
						writeLineToFile( 2, fileHandle, "{0} = {0}".format( dependentProjectData.id ) )

					writeLineToFile( 1, fileHandle, "EndProjectSection" )

				writeLineToFile( 0, fileHandle, "EndProject" )

			writeLineToFile( 0, fileHandle, "Global" )

			# Write all of the supported configurations and platforms.
			writeLineToFile( 1, fileHandle, "GlobalSection(SolutionConfigurationPlatforms) = preSolution" )
			for buildTarget in self._configList:
				for platformName in registeredPlatformList:
					writeLineToFile( 2, fileHandle, "{0}|{1} = {0}|{1}".format(buildTarget, platformName ) )
			writeLineToFile( 1, fileHandle, "EndGlobalSection" )

			writeLineToFile( 1, fileHandle, "GlobalSection(ProjectConfigurationPlatforms) = postSolution" )
			for projectData in self._orderedProjectList:
				if not projectData.isFilter:
					for buildTarget in self._configList:
						for platformName in registeredPlatformList:
							writeLineToFile( 2, fileHandle, "{0}.{1}|{2}.ActiveCfg = {1}|{2}".format( projectData.id, buildTarget, platformName ) )
							# A project is only enabled for a given platform if it's the Build All project (only applies to non-native solutions)
							# or if the project is listed under the current configuration and platform.
							if projectData.isBuildAllProject or ( self._createNativeProject and projectData.HasConfigAndPlatform( buildTarget, platformName ) ):
								writeLineToFile( 2, fileHandle, "{0}.{1}|{2}.Build.0 = {1}|{2}".format( projectData.id, buildTarget, platformName ) )
			writeLineToFile( 1, fileHandle, "EndGlobalSection" )

			writeLineToFile( 1, fileHandle, "GlobalSection(SolutionProperties) = preSolution" )
			writeLineToFile( 2, fileHandle, "HideSolutionNode = FALSE" )
			writeLineToFile( 1, fileHandle, "EndGlobalSection" )

			# Write out any information about nested projects.
			if len( projectFilterList ) > 0:
				writeLineToFile( 1, fileHandle, "GlobalSection(NestedProjects) = preSolution" )
				for filterData in projectFilterList:
					for nestedProjectData in filterData.dependencyList:
						writeLineToFile( 2, fileHandle, "{} = {}".format( nestedProjectData.id, filterData.id ) )
				writeLineToFile( 1, fileHandle, "EndGlobalSection" )

			writeLineToFile( 0, fileHandle, "EndGlobal" )

		with open( tempSolutionPath, "rb" ) as fileHandle:
			fileData = fileHandle.read()
			cachedFile = CachedFileData( finalSolutionPath, fileData, False )
			cachedFile.SaveFile()

		if os.access( tempSolutionPath, os.F_OK ):
			os.remove( tempSolutionPath )
			try:
				# Attempt to remove the temp directory.  This will only fail if the directory already existed with files in it.
				# In that case, just catch the exception and move on.
				os.rmdir( tempRootPath )
			except:
				pass
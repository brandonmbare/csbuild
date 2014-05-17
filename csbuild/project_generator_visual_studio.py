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

import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import os
import sys
import uuid
import codecs

from csbuild import project_generator
from csbuild import projectSettings
from csbuild import log
from csbuild import _shared_globals

import csbuild


PROJECT_UUID_LIST = set()


def GenerateNewUuid(uuidList):
	# Keep generating new UUIDs until we've found one that isn't already in use. This is only useful in cases where we have a pool of objects
	# and each one needs to be guaranteed to have a UUID that doesn't collide with any other object in the same pool.  Though, because of the
	# way UUIDs work, having a collision should be extremely rare anyway.
	while True:
		newUuid = uuid.uuid4()
		if not newUuid in uuidList:
			uuidList.add(newUuid)
			return newUuid

def GetPlatformName(architecture):
	# The mapped architectures have special names in Visual Studio.
	platformNameMap = {
		"x86": "Win32",
		"arm": "ARM",
	}

	# If the given architecture is mapped to a name, use that name.
	if architecture in platformNameMap:
		return platformNameMap[architecture]

	# Otherwise, use the architecture itself as a fallback.
	return architecture


def IsMicrosoftPlatform(platformName):
	microsoftPlatforms = set(["Win32", "x64", "ARM"])
	return platformName in microsoftPlatforms


def GetPlatformToolsetString(versionNumber):
	platformToolsetMap = {
		2010: "vc100",
		2012: "vc110",
		2013: "vc120",
	}
	return platformToolsetMap[versionNumber]


def CorrectConfigName(configName):
	# Visual Studio can be exceptionally picky about configuration names.  For instance, if your build script has the "debug" target,
	# you may run into problems with Visual Studio showing that alongside it's own "Debug" configuration, which is may have decided
	# to just add alongside your own.  The solution is to just put the configurations in a format it expects (first letter upper case,
	# the rest lowercase).  That way, it will see "Debug" already there and won't try to silently 'fix' that up for you.
	return configName[0].upper() + configName[1:].lower()


class Project:
	"""
	Container class for Visual Studio projects.
	"""

	def __init__(self):
		global PROJECT_UUID_LIST

		self.name = ""
		self.outputPath = ""
		self.dependencyList = set()
		self.id = "{{{}}}".format(str(GenerateNewUuid(PROJECT_UUID_LIST)).upper())
		self.isFilter = False
		self.isBuildAllProject = False
		self.platformConfigList = [] # Needs to be a list so it can be sorted.
		self.fullSourceFileList = set()
		self.fullHeaderFileList = set()


	def HasConfigAndPlatform(self, config, platform):
		for configName, platformName, _ in self.platformConfigList:
			if configName == config and platformName == platform:
				return True

		return False


class ProjectFileType:
	Unknown = None
	VCPROJ = "vcproj"
	VCXPROJ = "vcxproj"


class project_generator_visual_studio(project_generator.project_generator):
	"""
	Generator used to create Visual Studio project files.
	"""

	def __init__(self, path, solutionName, extraArgs):
		project_generator.project_generator.__init__(self, path, solutionName, extraArgs)

		versionNumber = csbuild.get_option("visual-studio-version")

		self._createNativeProject = False # csbuild.get_option("create-native-project")
		self._visualStudioVersion = versionNumber
		self._projectMap = {}
		self._configList = []
		self._platformList = []
		self._archMap = {}
		self._projectFileType = ProjectFileType.Unknown
		self._extraBuildArgs = self.extraargs.replace(",", " ")

		for configName in _shared_globals.alltargets:
			self._configList.append(CorrectConfigName(configName))

		# Compile a list of the platforms for the solution.
		for archName in _shared_globals.allarchitectures:
			platformName = GetPlatformName(archName)
			self._archMap[platformName] = archName
			self._platformList.append(platformName)

		self._configList = sorted(self._configList)
		self._platformList = sorted(self._platformList)

		# Try to convert the version provided by the user into a string.  If that fails, do nothing because we want to keep the original value for error reporting.
		try:
			self._visualStudioVersion = int(self._visualStudioVersion)
		except:
			pass


	@staticmethod
	def additional_args(parser):
		parser.add_argument("--visual-studio-version",
			help = "Select the version of Visual Studio the generated solution will be compatible with (i.e, --visualStudioVersion=2012).",
			default = 2012)
		#parser.add_argument("--create-native-project",
		#	help = "Create a native solution that calls into MSBuild and NOT the makefiles.",
		#	default = False)


	def write_solution(self):

		def recurseGroups(projectMap_out, parentFilter_out, projectOutputPath, projectGroup):
			# Setup the projects first.
			for projectName, projectSettingsMap in projectGroup.projects.items():

				# Fill in the project data.
				projectData = Project() # Create a new object to contain project data.
				projectData.name = projectName
				projectData.outputPath = projectOutputPath

				# Add the current project to the parent filter dependency list. In the case of filters,
				# this isn't really a depencency list, it's just a list of nested projects.
				if parentFilter_out:
					parentFilter_out.dependencyList.add(projectName)

				# Because the list of sources and headers can differ between configurations and architectures,
				# we need to generate a complete list so the project can reference them all. Also, keep track
				# of the project settings per configuration and supported architecture.
				for configName, archMap in projectSettingsMap.items():
					for archName, settings in archMap.items():
						platformName = GetPlatformName(archName)
						configName = CorrectConfigName(configName)
						projectData.platformConfigList.append((configName, platformName, settings))
						projectData.fullSourceFileList.update(set(settings.allsources))
						projectData.fullHeaderFileList.update(set(settings.allheaders))

				projectData.platformConfigList = sorted(projectData.platformConfigList)

				# Grab the projectSettings for the first key in the config map and fill in a set of names for dependent projects.
				# We only need the names for now. We can handle resolving them after we have all of the projects mapped.
				archMap = list(projectSettingsMap.values())[0]
				settings = list(archMap.values())[0]
				for dependentProjectKey in settings.linkDepends:
					projectData.dependencyList.add(_shared_globals.projects[dependentProjectKey].name)

				projectData.dependencyList = set(sorted(projectData.dependencyList)) # Sort the dependency list.
				projectMap_out[projectData.name] = projectData

			# Sort the parent filter dependency list.
			if parentFilter_out:
				parentFilter_out.dependencyList = set(sorted(parentFilter_out.dependencyList))

			# Next, iterate through each subgroup and handle each one recursively.
			for subGroupName, subGroup in projectGroup.subgroups.items():
				groupPath = os.path.join(projectOutputPath, subGroupName)

				filterData = Project() # Subgroups should be treated as project filters in the solution.

				filterData.name = subGroupName
				filterData.isFilter = True

				# Explicitly map the filter names with a different name to help avoid possible naming collisions.
				projectMap_out["{}.Filter".format(filterData.name)] = filterData

				# Create the group path if it doesn't exist.
				if not os.path.exists(groupPath):
					os.makedirs(groupPath)

				recurseGroups(projectMap_out, filterData, groupPath, subGroup)


		def resolveDependencies(projectMap):
			for projectId, projectData in projectMap.items():
				resolvedDependencyList = []

				# Resolve each project name to their associated project objects.
				for dependentProjectName in projectData.dependencyList:
					resolvedDependencyList.append(projectMap[dependentProjectName])

				# Replace the old name list with the new resolved list.
				projectData.dependencyList = resolvedDependencyList


		# Create the base output directory if necessary.
		if not os.path.exists(self.rootpath):
			os.makedirs(self.rootpath)

		# When not creating a native project, a custom project must be injected in order to achieve full solution builds
		# since Visual Studio doesn't give us a way to override the behavior of the "Build Solution" command.
		if not self._createNativeProject:
			# Fill in the project data.
			buildAllProjectData = Project() # Create a new object to contain project data.
			buildAllProjectData.name = "(BUILD_ALL)"
			buildAllProjectData.outputPath = self.rootpath
			buildAllProjectData.isBuildAllProject = True

			# The Build All project doesn't have any project settings, but it still needs all of the platforms and configurations.
			for platformName in self._platformList:
				for configName in self._configList:
					buildAllProjectData.platformConfigList.append((configName, platformName, None))

			# Add the Build All project to the project map.
			self._projectMap[buildAllProjectData.name] = buildAllProjectData

		recurseGroups(self._projectMap, None, self.rootpath, projectSettings.rootGroup)
		resolveDependencies(self._projectMap)

		is2005 = (self._visualStudioVersion == 2005)
		is2008 = (self._visualStudioVersion == 2008)
		is2010 = (self._visualStudioVersion == 2010)
		is2012 = (self._visualStudioVersion == 2012)
		is2013 = (self._visualStudioVersion == 2013)

		if is2005:
			self._GenerateFilesForVs2005()
		elif is2008:
			self._GenerateFilesForVs2008()
		elif is2010:
			self._GenerateFilesForVs2010()
		elif is2012:
			self._GenerateFilesForVs2012()
		elif is2013:
			self._GenerateFilesForVs2013()
		else:
			log.LOG_ERROR("Invalid Visual Studio version: {}".format(self._visualStudioVersion));


	def _GenerateFilesForVs2005(self):
		self._projectFileType = ProjectFileType.VCPROJ
		self._WriteSolutionFile()


	def _GenerateFilesForVs2008(self):
		self._projectFileType = ProjectFileType.VCPROJ
		self._WriteSolutionFile()


	def _GenerateFilesForVs2010(self):
		self._projectFileType = ProjectFileType.VCXPROJ
		self._WriteSolutionFile()
		self._WriteVcxprojFiles()
		self._WriteVcxprojFiltersFiles()
		self._WriteVcxprojUserFiles()


	def _GenerateFilesForVs2012(self):
		self._projectFileType = ProjectFileType.VCXPROJ
		self._WriteSolutionFile()
		self._WriteVcxprojFiles()
		self._WriteVcxprojFiltersFiles()
		self._WriteVcxprojUserFiles()


	def _GenerateFilesForVs2013(self):
		self._projectFileType = ProjectFileType.VCXPROJ
		self._WriteSolutionFile()
		self._WriteVcxprojFiles()
		self._WriteVcxprojFiltersFiles()
		self._WriteVcxprojUserFiles()


	def _WriteSolutionFile(self):

		def writeLineToFile(indentLevel, fileHandle, stringToWrite):
			fileHandle.write("{}{}\r\n".format("\t" * indentLevel, stringToWrite))

		fileFormatVersionNumber = {
			2005: "9.00",
			2008: "10.00",
			2010: "11.00",
			2012: "12.00",
			2013: "12.00",
		}

		solutionPath = "{}.sln".format(os.path.join(self.rootpath, self.solutionname))

		# Visual Studio solution files need to be UTF-8 with the byte order marker because Visual Studio is VERY picky about these files.
		# If ANYTHING is missing or not formatted properly, the Visual Studio version selector may not open the right version or Visual
		# Studio itself may refuse to even attempt to load the file.
		with codecs.open(solutionPath, "w", "utf-8-sig") as fileHandle:
			writeLineToFile(0, fileHandle, "") # Required empty line.
			writeLineToFile(0, fileHandle, "Microsoft Visual Studio Solution File, Format Version {}".format(fileFormatVersionNumber[self._visualStudioVersion]))
			writeLineToFile(0, fileHandle, "# Visual Studio {}".format(self._visualStudioVersion))

			projectFilterList = []

			for projectName, projectData in self._projectMap.items():
				if not projectData.isFilter:
					relativeProjectPath = os.path.relpath(projectData.outputPath, self.rootpath)
					projectFilePath = os.path.join(relativeProjectPath, "{}.{}".format(projectData.name, self._projectFileType))
					nodeId = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"
				else:
					projectFilePath = projectData.name
					nodeId = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"

					# Keep track of the filters because we need to record those after the projects.
					projectFilterList.append(projectData)

				beginProject = 'Project("{}") = "{}", "{}", "{}"'.format(nodeId, projectData.name, projectFilePath, projectData.id)

				writeLineToFile(0, fileHandle, beginProject)

				# Only write out project dependency information if the current project has any dependencies and if we're creating a native project.
				# If we're not creating a native project, it doesn't matter since csbuild will take care of all that for us behind the scenes.
				# Also, don't list any dependencies for filters. Those will be written out under NestedProjects.
				if self._createNativeProject and not projectData.isFilter and len(projectData.dependencyList) > 0:
					writeLineToFile(1, fileHandle, "ProjectSection(ProjectDependencies) = postProject")

					# Write out the IDs for each dependent project.
					for dependentProjectData in projectData.dependencyList:
						writeLineToFile(2, fileHandle, "{0} = {0}".format(dependentProjectData.id))

					writeLineToFile(1, fileHandle, "EndProjectSection")

				writeLineToFile(0, fileHandle, "EndProject")

			writeLineToFile(0, fileHandle, "Global")

			# Write all of the supported configurations and platforms.
			writeLineToFile(1, fileHandle, "GlobalSection(SolutionConfigurationPlatforms) = preSolution")
			for buildTarget in self._configList:
				for platformName in self._platformList:
					writeLineToFile(2, fileHandle, "{0}|{1} = {0}|{1}".format(buildTarget, platformName))
			writeLineToFile(1, fileHandle, "EndGlobalSection")

			writeLineToFile(1, fileHandle, "GlobalSection(ProjectConfigurationPlatforms) = postSolution")
			for projectName, projectData in self._projectMap.items():
				if not projectData.isFilter:
					for buildTarget in self._configList:
						for platformName in self._platformList:
							writeLineToFile(2, fileHandle, "{0}.{1}|{2}.ActiveCfg = {1}|{2}".format(projectData.id, buildTarget, platformName))
							# A project is only enabled for a given platform if it's the Build All project (only applies to non-native solutions)
							# or if the project is listed under the current configuration and platform.
							if projectData.isBuildAllProject or (self._createNativeProject and projectData.HasConfigAndPlatform(buildTarget, platformName)):
								writeLineToFile(2, fileHandle, "{0}.{1}|{2}.Build.0 = {1}|{2}".format(projectData.id, buildTarget, platformName))
			writeLineToFile(1, fileHandle, "EndGlobalSection")

			writeLineToFile(1, fileHandle, "GlobalSection(SolutionProperties) = preSolution")
			writeLineToFile(2, fileHandle, "HideSolutionNode = FALSE")
			writeLineToFile(1, fileHandle, "EndGlobalSection")

			# Write out any information about nested projects.
			if len(projectFilterList) > 0:
				writeLineToFile(1, fileHandle, "GlobalSection(NestedProjects) = preSolution")
				for filterData in projectFilterList:
					for nestedProjectData in filterData.dependencyList:
						writeLineToFile(2, fileHandle, "{} = {}".format(nestedProjectData.id, filterData.id))
				writeLineToFile(1, fileHandle, "EndGlobalSection")

			writeLineToFile(0, fileHandle, "EndGlobal")


	def _WriteVcxprojFiles(self):
		CreateRootNode = ET.Element
		AddNode = ET.SubElement

		for projectName, projectData in self._projectMap.items():
			if not projectData.isFilter:
				rootNode = CreateRootNode("Project")
				rootNode.set("DefaultTargets", "Build")
				rootNode.set("ToolsVersion", "4.0")
				rootNode.set("xmlns", "http://schemas.microsoft.com/developer/msbuild/2003")

				itemGroupNode = AddNode(rootNode, "ItemGroup")
				itemGroupNode.set("Label", "ProjectConfigurations")

				# Add the project configurations
				for configName, platformName, _ in projectData.platformConfigList:
					projectConfigNode = AddNode(itemGroupNode, "ProjectConfiguration")
					configNode = AddNode(projectConfigNode, "Configuration")
					platformNode = AddNode(projectConfigNode, "Platform")

					projectConfigNode.set("Include", "{}|{}".format(configName, platformName))
					configNode.text = configName
					platformNode.text = platformName

				# Add the project's source files.
				if len(projectData.fullSourceFileList) > 0:
					itemGroupNode = AddNode(rootNode, "ItemGroup")
					for sourceFilePath in projectData.fullSourceFileList:
						sourceFileNode = AddNode(itemGroupNode, "ClCompile")
						sourceFileNode.set("Include", os.path.relpath(sourceFilePath, projectData.outputPath))

						# Handle any configuration or platform excludes for the current file.
						for configName, platformName, settings in projectData.platformConfigList:
							if not sourceFilePath in settings.allsources:
								excludeNode = AddNode(sourceFileNode, "ExcludedFromBuild")
								excludeNode.text = "true"
								excludeNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format(configName, platformName))

				# Add the project's header files.
				if len(projectData.fullHeaderFileList) > 0:
					itemGroupNode = AddNode(rootNode, "ItemGroup")
					for sourceFilePath in projectData.fullHeaderFileList:
						sourceFileNode = AddNode(itemGroupNode, "ClInclude")
						sourceFileNode.set("Include", os.path.relpath(sourceFilePath, projectData.outputPath))

						# Handle any configuration or platform excludes for the current file.
						for configName, platformName, settings in projectData.platformConfigList:
							if not sourceFilePath in settings.allheaders:
								excludeNode = AddNode(sourceFileNode, "ExcludedFromBuild")
								excludeNode.text = "true"
								excludeNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format(configName, platformName))

				propertyGroupNode = AddNode(rootNode, "PropertyGroup")
				importNode = AddNode(rootNode, "Import")
				projectGuidNode = AddNode(propertyGroupNode, "ProjectGuid")
				namespaceNode = AddNode(propertyGroupNode, "RootNamespace")

				propertyGroupNode.set("Label", "Globals")
				importNode.set("Project", r"$(VCTargetsPath)\Microsoft.Cpp.Default.props")
				projectGuidNode.text = projectData.id
				namespaceNode.text = projectData.name

				# If we're not creating a native project, Visual Studio needs to know this is a makefile project.
				if not self._createNativeProject:
					keywordNode = AddNode(propertyGroupNode, "Keyword")
					keywordNode.text = "MakeFileProj"

				for configName, platformName, _ in projectData.platformConfigList:
					propertyGroupNode = AddNode(rootNode, "PropertyGroup")
					propertyGroupNode.set("Label", "Configuration")
					propertyGroupNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format(configName, platformName))

					if IsMicrosoftPlatform(platformName):
						platformToolsetNode = AddNode(propertyGroupNode, "PlatformToolset")
						platformToolsetNode.text = GetPlatformToolsetString(self._visualStudioVersion)

					if self._createNativeProject:
						# TODO: Add properties for native projects.
						pass
					else:
						configTypeNode = AddNode(propertyGroupNode, "ConfigurationType")
						configTypeNode.text = "Makefile"

				importNode = AddNode(rootNode, "Import")
				importNode.set("Project", r"$(VCTargetsPath)\Microsoft.Cpp.props")

				for configName, platformName, _ in projectData.platformConfigList:
					importGroupNode = AddNode(rootNode, "ImportGroup")
					importGroupNode.set("Label", "PropertySheets")
					importGroupNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format(configName, platformName))

					# Microsoft platforms import special property sheets.
					if IsMicrosoftPlatform(platformName):
						importNode = AddNode(importGroupNode, "Import")
						importNode.set("Label", "LocalAppDataPlatform")
						importNode.set("Project", r"$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props")
						importNode.set("Condition", "exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')")

				for configName, platformName, settings in projectData.platformConfigList:
					propertyGroupNode = AddNode(rootNode, "PropertyGroup")
					propertyGroupNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format(configName, platformName))

					if self._createNativeProject:
						# TODO: Add properties for non-native projects.
						pass
					else:
						buildCommandNode = AddNode(propertyGroupNode, "NMakeBuildCommandLine")
						cleanCommandNode = AddNode(propertyGroupNode, "NMakeCleanCommandLine")
						rebuildCommandNode = AddNode(propertyGroupNode, "NMakeReBuildCommandLine")
						outDirNode = AddNode(propertyGroupNode, "OutDir")
						intDirNode = AddNode(propertyGroupNode, "IntDir")

						archName = self._archMap[platformName]
						projectArg = " --project={}".format(projectData.name) if not projectData.isBuildAllProject else ""
						mainMakefile = os.path.relpath(os.path.join(os.getcwd(), csbuild.mainfile), projectData.outputPath)

						buildCommandNode.text = "{} {} --target={} --architecture={}{}".format(sys.executable, mainMakefile, configName, archName, projectArg)
						cleanCommandNode.text = "{} {} --clean --target={} --architecture={}{}".format(sys.executable, mainMakefile, configName, archName, projectArg)
						rebuildCommandNode.text = "{} {} --rebuild --target={} --architecture={}{}".format(sys.executable, mainMakefile, configName, archName, projectArg)

						if not projectData.isBuildAllProject:
							outputNode = AddNode(propertyGroupNode, "NMakeOutput")
							includePathNode = AddNode(propertyGroupNode, "NMakeIncludeSearchPath")

							outDirNode.text = os.path.relpath(settings.output_dir, projectData.outputPath)
							intDirNode.text = os.path.relpath(settings.obj_dir, projectData.outputPath)
							outputNode.text = os.path.relpath(os.path.join(settings.output_dir, settings.output_name), projectData.outputPath)
							includePathNode.text = ";".join(settings.include_dirs)
						else:
							# Gotta put this stuff somewhere for the Build All project.
							outDirNode.text = projectData.name + "_log"
							intDirNode.text = outDirNode.text

				importNode = AddNode(rootNode, "Import")
				importNode.set("Project", r"$(VCTargetsPath)\Microsoft.Cpp.targets")

				self._SaveXmlFile(rootNode, os.path.join(projectData.outputPath, "{}.{}".format(projectData.name, self._projectFileType)))


	def _WriteVcxprojFiltersFiles(self):
		CreateRootNode = ET.Element
		AddNode = ET.SubElement

		for projectName, projectData in self._projectMap.items():
			if not projectData.isFilter:
				rootNode = CreateRootNode("Project")
				rootNode.set("ToolsVersion", "4.0")
				rootNode.set("xmlns", "http://schemas.microsoft.com/developer/msbuild/2003")

				if not projectData.isBuildAllProject:
					itemGroupNode = AddNode(rootNode, "ItemGroup")

					# TODO: Add better source file filters.
					sourceFileFilterNode = AddNode(itemGroupNode, "Filter")
					headerFileFilterNode = AddNode(itemGroupNode, "Filter")

					filterGuidList = set()

					sourceFileFilterNode.set("Include", "Source Files")
					headerFileFilterNode.set("Include", "Header Files")

					uniqueIdNode = AddNode(sourceFileFilterNode, "UniqueIdentifier")
					uniqueIdNode.text = "{{{}}}".format(GenerateNewUuid(filterGuidList))

					uniqueIdNode = AddNode(headerFileFilterNode, "UniqueIdentifier")
					uniqueIdNode.text = "{{{}}}".format(GenerateNewUuid(filterGuidList))

					# Add the project's source files.
					if len(projectData.fullSourceFileList) > 0:
						itemGroupNode = AddNode(rootNode, "ItemGroup")
						for sourceFilePath in projectData.fullSourceFileList:
							sourceFileNode = AddNode(itemGroupNode, "ClCompile")
							filterNode = AddNode(sourceFileNode, "Filter")
							sourceFileNode.set("Include", os.path.relpath(sourceFilePath, projectData.outputPath))
							filterNode.text = "Source Files"


					# Add the project's header files.
					if len(projectData.fullHeaderFileList) > 0:
						itemGroupNode = AddNode(rootNode, "ItemGroup")
						for headerFilePath in projectData.fullHeaderFileList:
							headerFileNode = AddNode(itemGroupNode, "ClInclude")
							filterNode = AddNode(headerFileNode, "Filter")
							headerFileNode.set("Include", os.path.relpath(headerFilePath, projectData.outputPath))
							filterNode.text = "Header Files"

				self._SaveXmlFile(rootNode, os.path.join(projectData.outputPath, "{}.{}.filters".format(projectData.name, self._projectFileType)))


	def _WriteVcxprojUserFiles(self):
		CreateRootNode = ET.Element
		AddNode = ET.SubElement

		for projectName, projectData in self._projectMap.items():
			if not projectData.isFilter:
				rootNode = CreateRootNode("Project")
				rootNode.set("ToolsVersion", "4.0")
				rootNode.set("xmlns", "http://schemas.microsoft.com/developer/msbuild/2003")

				if not projectData.isBuildAllProject:
					for configName, platformName, _ in projectData.platformConfigList:
						if IsMicrosoftPlatform(platformName):
							propertyGroupNode = AddNode(rootNode, "PropertyGroup")
							workingDirNode = AddNode(propertyGroupNode, "LocalDebuggerWorkingDirectory")
							debuggerTypeNode = AddNode(propertyGroupNode, "LocalDebuggerDebuggerType")
							debuggerFlavorNode = AddNode(propertyGroupNode, "DebuggerFlavor")

							propertyGroupNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format(configName, platformName))
							workingDirNode.text = "$(OutDir)"
							debuggerTypeNode.text = "NativeOnly"
							debuggerFlavorNode.text = "WindowsLocalDebugger"


				self._SaveXmlFile(rootNode, os.path.join(projectData.outputPath, "{}.{}.user".format(projectData.name, self._projectFileType)))


	def _SaveXmlFile(self, rootNode, xmlFilename):
		# Grab a string of the XML document we've created and save it.
		xmlString = ET.tostring(rootNode)

		# Convert to the original XML to a string on Python3.
		if sys.version_info >= (3, 0):
			xmlString = xmlString.decode("utf-8")

		# Use minidom to reformat the XML since ElementTree doesn't do it for us.
		formattedXmlString = minidom.parseString(xmlString).toprettyxml("\t", "\n", encoding = "utf-8")
		if sys.version_info >= (3, 0):
			formattedXmlString = formattedXmlString.decode("utf-8")

		inputLines = formattedXmlString.split("\n")
		outputLines = []

		# Copy each line of the XML to a list of strings.
		for line in inputLines:
			outputLines.append(line)

		# Concatenate each string with a newline.
		finalXmlString = "\n".join(outputLines)

		# Open the output file and write the new XML string to it.
		with open(xmlFilename, "w") as f:
			f.write(finalXmlString)

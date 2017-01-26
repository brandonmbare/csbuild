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

"""Contains the vsgen platform for PS4."""

import os
import csbuild
import xml.etree.ElementTree as ET

from ...vsgen.platform_base import PlatformBase


_addNode = ET.SubElement


class PlatformPs4( PlatformBase ):
	def __init__( self ):
		PlatformBase.__init__( self )


	@staticmethod
	def GetToolchainName():
		return "ps4-x64"


	@staticmethod
	def GetVisualStudioName():
		return "ORBIS"


	def WriteGlobalHeader( self, parentXmlNode ):
		# Nothing to do for PS4.
		pass


	def WriteGlobalFooter( self, parentXmlNode ):
		# Extension settings
		importGroupNode = _addNode( parentXmlNode, "ImportGroup" )

		importGroupNode.set( "Label", "ExtensionSettings" )

		_addNode( importGroupNode, "Import" ).set( "Project", r"$(VCTargetsPath)\BuildCustomizations\OrbisWavePsslc.props" )
		_addNode( importGroupNode, "Import" ).set( "Project", r"$(VCTargetsPath)\BuildCustomizations\SCU.props" )


		# Extension targets
		importGroupNode = _addNode( parentXmlNode, "ImportGroup" )

		importGroupNode.set( "Label", "ExtensionTargets" )

		_addNode( importGroupNode, "Import" ).set( "Project", r"$(VCTargetsPath)\BuildCustomizations\OrbisWavePsslc.targets" )
		_addNode( importGroupNode, "Import" ).set( "Project", r"$(VCTargetsPath)\BuildCustomizations\SCU.targets" )


	def WriteProjectConfiguration( self, parentXmlNode, vsConfigName ):
		platformName = self.GetVisualStudioName()
		includeString = "{}|{}".format( vsConfigName, platformName )

		projectConfigNode = _addNode( parentXmlNode, "ProjectConfiguration" )
		configNode = _addNode( projectConfigNode, "Configuration" )
		platformNode = _addNode( projectConfigNode, "Platform" )

		projectConfigNode.set( "Include", includeString )
		configNode.text = vsConfigName
		platformNode.text = platformName


	def WriteConfigPropertyGroup( self, parentXmlNode, vsConfigName, vsPlatformToolsetName, isNative ):
		platformName = self.GetVisualStudioName()

		propertyGroupNode = _addNode( parentXmlNode, "PropertyGroup" )
		propertyGroupNode.set( "Label", "Configuration")
		propertyGroupNode.set( "Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format( vsConfigName, platformName ) )

		if isNative:
			#TODO: Add properties for native projects.
			pass
		else:
			configTypeNode = _addNode( propertyGroupNode, "ConfigurationType" )
			configTypeNode.text = "Makefile"


	def WriteImportProperties( self, parentXmlNode, vsConfigName, isNative ):
		platformName = self.GetVisualStudioName()

		importGroupNode = _addNode( parentXmlNode, "ImportGroup" )
		importGroupNode.set( "Label", "PropertySheets")
		importGroupNode.set( "Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format( vsConfigName, platformName ) )

		importNode = _addNode( importGroupNode, "Import" )
		importNode.set( "Label", "LocalAppDataPlatform" )
		importNode.set( "Project", r"$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" )
		importNode.set( "Condition", "exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" )


	def WriteUserDebugPropertyGroup( self, parentXmlNode, vsConfigName, projectData ):
		platformName = self.GetVisualStudioName()

		propertyGroupNode = _addNode( parentXmlNode, "PropertyGroup" )

		propertyGroupNode.set( "Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format( vsConfigName, platformName ) )

		_addNode( propertyGroupNode, "LocalDebuggerWorkingDirectory" ).text = "$(OutDir)"
		_addNode( propertyGroupNode, "DebuggerFlavor" ).text = "ORBISDebugger"


	def WriteExtraPropertyGroupBuildNodes( self, parentXmlNode, vsConfigName, projectData ):
		# Nothing to do for PS4.
		pass


	def WriteGlobalImportTargets( self, parentXmlNode, isNative ):
		if isNative:
			#TODO: Add properties for native projects.
			pass
		else:
			importNode = _addNode( parentXmlNode, "Import" )

			importNode.set( "Condition", r"'$(ConfigurationType)' == 'Makefile' and Exists('$(VCTargetsPath)\Platforms\$(Platform)\SCE.Makefile.$(Platform).targets')" )
			importNode.set( "Project", r"$(VCTargetsPath)\Platforms\$(Platform)\SCE.Makefile.$(Platform).targets" )


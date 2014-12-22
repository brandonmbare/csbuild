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

"""Contains the vsgen platform for Tegra-Android."""

import xml.etree.ElementTree as ET

from .platform_base import PlatformBase


class PlatformTegraAndroid( PlatformBase ):
	def __init__( self ):
		PlatformBase.__init__( self )


	@staticmethod
	def GetToolchainName():
		"""
		Retrieve the toolchain-architecture name combination that this platform will apply to.

		:return: str
		"""
		return "android-armeabi-v7a"


	@staticmethod
	def GetVisualStudioName():
		"""
		Retrieve the name value that will show up in Visual Studio as a buildable platform for a generated project.
		Must be a name that Visual Studio recognizes.

		:return: str
		"""
		return "Tegra-Android"


	def WriteProjectConfiguration( self, parentXmlNode, vsConfigName ):
		"""
		Write the project configuration nodes for this platform.

		:param parentXmlNode: Parent XML node.
		:type parentXmlNode: class`xml.etree.ElementTree.SubElement`

		:param vsConfigName: Visual Studio configuration name.
		:type vsConfigName: str
		"""
		AddNode = ET.SubElement

		platformName = self.GetVisualStudioName()
		includeString = "{}|{}".format( vsConfigName, platformName )

		projectConfigNode = AddNode(parentXmlNode, "ProjectConfiguration")
		configNode = AddNode(projectConfigNode, "Configuration")
		platformNode = AddNode(projectConfigNode, "Platform")

		projectConfigNode.set( "Include", includeString )
		configNode.text = vsConfigName
		platformNode.text = platformName


	def WritePropertyGroup( self, parentXmlNode, vsConfigName, vsPlatformToolsetName, isNative ):
		"""
		Write the project's property group nodes for this platform.

		:param parentXmlNode: Parent XML node.
		:type parentXmlNode: class`xml.etree.ElementTree.SubElement`

		:param vsConfigName: Visual Studio configuration name.
		:type vsConfigName: str

		:param vsPlatformToolsetName: Name of the platform toolset for the selected version of Visual Studio.
		:type vsPlatformToolsetName: str

		:param isNative: Is this a native project?
		:type isNative: bool
		"""
		AddNode = ET.SubElement

		platformName = self.GetVisualStudioName()

		propertyGroupNode = AddNode( parentXmlNode, "PropertyGroup" )
		propertyGroupNode.set( "Label", "Configuration")
		propertyGroupNode.set( "Condition", "'$(Configuration)|$(Platform)'=='{}|{}'".format( vsConfigName, platformName ) )

		if isNative:
			#TODO: Add properties for native projects.
			assert False
		else:
			configTypeNode = AddNode(propertyGroupNode, "ConfigurationType")
			configTypeNode.text = "ExternalBuildSystem"


	def WriteImportProperties( self, parentXmlNode, vsConfigName, isNative ):
		"""
		Write any special import properties for this platform.

		:param parentXmlNode: Parent XML node.
		:type parentXmlNode: class`xml.etree.ElementTree.SubElement'

		:param vsConfigName: Visual Studio configuration name.
		:type vsConfigName: str

		:param isNative: Is this a native project?
		:type isNative: bool
		"""
		# Nothing to do for Tegra.
		pass

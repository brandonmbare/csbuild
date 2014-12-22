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

"""Contains the interface for all vsgen platforms."""


class PlatformBase( object ):
	def __init__( self ):
		self._definesMap = {}


	@staticmethod
	def GetToolchainName():
		"""
		Retrieve the toolchain-architecture name combination that this platform will apply to.

		:return: str
		"""
		pass


	@staticmethod
	def GetVisualStudioName():
		"""
		Retrieve the name value that will be show up in Visual Studio for a platform.  Must be a name that Visual Studio recognizes.

		:return: str
		"""
		pass


	def AddDefines( self, targetName, projectName, defines ):
		"""
		Map a list of preprocessor defines to a project and target.

		:param targetName: Output target.
		:type targetName: str

		:param projectName: Name of the project associated with the defines.
		:type projectName: str

		:param defines: Defines to add.
		:type defines: list
		"""
		assert isinstance( defines, list )

		mapKey = ( targetName, projectName )

		if not projectName in self._definesMap:
			self._definesMap.update( { mapKey: defines } )
		else:
			self._definesMap[mapKey].append( defines )

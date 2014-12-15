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

"""Contains the the vsgen platforms for x64 and Win32."""

from .platform_base import PlatformBase


class PlatformWindowsX86( PlatformBase ):
	def __init__( self ):
		PlatformBase.__init__( self )


	def GetEntryName( self ):
		"""
		Retrieve the name value that will show up in Visual Studio as a buildable platform for a generated project.  Must be a name that Visual Studio recognizes.

		:return: str
		"""
		return "Win32"


class PlatformWindowsX64( PlatformBase ):
	def __init__( self ):
		PlatformBase.__init__( self )
	
	
	def GetEntryName( self ):
		"""
		Retrieve the name value that will show up in Visual Studio as a buildable platform for a generated project.  Must be a name that Visual Studio recognizes.
		
		:return: str
		"""
		return "x64"

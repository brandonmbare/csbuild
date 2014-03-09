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
B{Project Generator Module}

Defines the base class for project generation.
"""

from abc import abstractmethod
import os
import csbuild


class project_generator( object ):
	"""
	Base class used for project generation.
	To create a new project generator, inherit from this class, and then use
	L{csbuild.RegisterProjectGenerator()<csbuild.RegisterProjectGenerator>}
	"""
	def __init__( self, path, solutionname ):
		"""
		@param path: The output path for the solution
		@type path: str
		@param solutionname: The name for the output solution file
		@type solutionname: str
		"""
		self.rootpath = os.path.abspath( path )
		self.solutionname = solutionname

		args = csbuild.get_args( )

		self.args = { }
		for arg in args.items( ):
			if "generate_solution" in arg[0]:
				continue
			if "solution_name" in arg[0]:
				continue
			if "solution_path" in arg[0]:
				continue
			if "fakearg" in arg[0]:
				continue
			if arg[0] == "target":
				continue
			if arg[0] == "project":
				continue

			if arg[1] == csbuild.get_default_arg( arg[0] ):
				continue

			self.args.update( { arg[0].replace( "_", "-" ): arg[1] } )


	def get_formatted_args( self, excludes ):
		"""
		Retrieves the list of arguments to append to the csbuild execution command when generating project files.

		@param excludes: List of options NOT to return, usually project generator-specific arguments
		@type excludes: list[str]
		"""
		outstr = ""
		for arg in self.args.items( ):
			if arg[0] in excludes:
				continue

			outstr += "--{}={} ".format( arg[0], arg[1] )
		return outstr


	@staticmethod
	def additional_args( parser ):
		"""
		Asks for additional command-line arguments to be added by the generator.

		@param parser: A parser for these arguments to be added to
		@type parser: argparse.argument_parser
		"""
		pass


	@abstractmethod
	def write_solution( self ):
		"""
		Actually performs the work of writing the solution
		"""
		pass
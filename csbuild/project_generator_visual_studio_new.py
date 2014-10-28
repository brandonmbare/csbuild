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

from . import project_generator
from . import projectSettings
from . import log
from . import _shared_globals

import csbuild

class VisualStudioVersion:
	v2010 = 2010
	v2012 = 2012
	v2013 = 2013
	All = [v2010, v2012, v2013]

class project_generator_visual_studio(project_generator.project_generator):
	"""
	Generator used to create Visual Studio project files.
	"""

	def __init__(self, path, solutionName, extraArgs):
		project_generator.project_generator.__init__(self, path, solutionName, extraArgs)


	@staticmethod
	def AdditionalArgs(parser):
		parser.add_argument("--vs-gen-version",
			help = "Select the version of Visual Studio the generated solution will be compatible with.",
			choices = VisualStudioVersion.All,
			default = VisualStudioVersion.v2012,
			type = int,
		)
		parser.add_argument("--vs-gen-replace-user-files",
			help = "When generating project files, do not ignore existing .vcxproj.user files.",
			action = "store_true",
		)


	def WriteProjectFiles(self):
		pass
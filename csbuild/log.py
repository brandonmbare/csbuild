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
B{Logging Module}

@undocumented: LOG_MSG
@undocumented: bar_writer
"""

import threading
import time
import math
import sys
from csbuild import _shared_globals
from csbuild import terminfo

#<editor-fold desc="Logging">

def LOG_MSG( color, level, msg ):
	"""Print a message to stdout"""
	with _shared_globals.printmutex:
		if _shared_globals.color_supported:
			terminfo.TermInfo.SetColor( color )
			sys.stdout.write( "{}: ".format( level ) )
			terminfo.TermInfo.ResetColor( )
			sys.stdout.write( msg )
			sys.stdout.write( "\n" )
		else:
			print(" {0}: {1}".format( level, msg ))
		sys.stdout.flush( )


def LOG_ERROR( msg ):
	"""
	Log an error message

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 3:
		return
	LOG_MSG( terminfo.TermColor.RED, "ERROR", msg )
	_shared_globals.errors.append( msg )


def LOG_WARN( msg ):
	"""
	Log a warning

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 3:
		return
	LOG_WARN_NOPUSH( msg )
	_shared_globals.warnings.append( msg )


def LOG_WARN_NOPUSH( msg ):
	"""
	Log a warning, don't push it to the list of warnings to be echoed at the end of compilation.

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 3:
		return
	LOG_MSG( terminfo.TermColor.YELLOW, "WARN", msg )


def LOG_INFO( msg ):
	"""
	Log general info. This info only appears with -v specified.

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 1:
		return
	LOG_MSG( terminfo.TermColor.CYAN, "INFO", msg )


def LOG_BUILD( msg ):
	"""
	Log info related to building

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 2:
		return
	LOG_MSG( terminfo.TermColor.MAGENTA, "BUILD", msg )


def LOG_LINKER( msg ):
	"""
	Log info related to linking

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 2:
		return
	LOG_MSG( terminfo.TermColor.GREEN, "LINKER", msg )


def LOG_THREAD( msg ):
	"""
	Log info related to threads, particularly stalls caused by waiting on another thread to finish

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 2:
		return
	LOG_MSG( terminfo.TermColor.BLUE, "THREAD", msg )


def LOG_INSTALL( msg ):
	"""
	Log info related to the installer

	@param msg: Text to log
	@type msg: str
	"""
	if _shared_globals.quiet >= 2:
		return
	LOG_MSG( terminfo.TermColor.WHITE, "INSTALL", msg )


#</editor-fold>


class bar_writer( threading.Thread ):
	def __init__( self ):
		"""Initialize the object. Also handles above-mentioned bug with dummy threads."""
		threading.Thread.__init__( self )
		self._stopWriting = False
		#Prevent certain versions of python from choking on dummy threads.
		if not hasattr( threading.Thread, "_Thread__block" ):
			threading.Thread._Thread__block = _shared_globals.dummy_block( )


	def stop( self ):
		self._stopWriting = True


	def run( self ):
		highperc = 0
		highnum = 0

		if _shared_globals.columns <= 0:
			return

		while _shared_globals.buildtime == -1 and not _shared_globals.interrupted and not self._stopWriting:
			curtime = time.time( ) - _shared_globals.starttime
			cur = 0
			top = len( _shared_globals.allfiles )

			top += _shared_globals.total_precompiles
			cur += _shared_globals.precompiles_done

			_shared_globals.columns = terminfo.TermInfo.GetNumColumns( )

			if _shared_globals.columns > 0 and top > 0:
				minutes = math.floor( curtime / 60 )
				seconds = math.floor( curtime % 60 )
				estmin = 0
				estsec = 0
				if _shared_globals.times and _shared_globals.lastupdate >= 0:
					cur = curtime
					avgtime = sum( _shared_globals.times ) / (len( _shared_globals.times ))
					top = _shared_globals.lastupdate + ((avgtime * (_shared_globals.total_compiles -
																	len(
																		_shared_globals.times ))) / _shared_globals
														.max_threads)
					if top < cur:
						top = cur
					estmin = math.floor( top / 60 )
					estsec = math.floor( top % 60 )

				frac = float( cur ) / float( top )
				num = int( math.floor( frac * (_shared_globals.columns - 16) ) )
				if num >= _shared_globals.columns - 15:
					num = _shared_globals.columns - 16
				perc = int( frac * 100 )
				if perc >= 100:
					perc = 99

				if perc < highperc:
					perc = highperc
				else:
					highperc = perc

				if num < highnum:
					num = highnum
				else:
					highnum = num

				totalCompletedCompiles = 0
				for project in _shared_globals.sortedProjects:
					totalCompletedCompiles += project.compiles_completed

				perc = 1 if _shared_globals.total_compiles == 0 else float(totalCompletedCompiles)/float(_shared_globals.total_compiles)
				num = int( math.floor( perc * (_shared_globals.columns - 16) ) )
				if num >= _shared_globals.columns - 15:
					num = _shared_globals.columns - 16

				perc = int(round(perc * 100))
				if perc == 100:
					perc = 99

				with _shared_globals.printmutex:
					if _shared_globals.times:
						sys.stdout.write( "[" + "=" * num + " " * (
							(_shared_globals.columns - 20) - num) + "]{0: 2}:{1:02}/{2: 2}:{3:02} ({4: 3}%)".format(
							int( minutes ),
							int( seconds ),
							int( estmin ),
							int( estsec ), perc
						)
						)
					else:
						sys.stdout.write(
							"[" + "=" * num + " " * (
								(_shared_globals.columns - 15) - num) + "]{0: 2}:{1:02} (~{2: 3}%)".format(
								int( minutes ), int( seconds ), perc ) )
					sys.stdout.flush( )
					sys.stdout.write( "\r" + " " * _shared_globals.columns + "\r" )
			time.sleep( 0.05 )

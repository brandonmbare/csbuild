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

import threading
import multiprocessing

columns = 0
color_supported = False

try:
    import curses
except:
    pass
else:
    try:
        curses.setupterm()
    except:
        pass
    else:
        columns = curses.tigetnum('cols')
        color_supported = (curses.tigetnum("colors") >= 8)

printmutex = threading.Lock()

max_threads = multiprocessing.cpu_count()

semaphore = threading.BoundedSemaphore(value=max_threads)
lock = threading.Lock()

built_something = False
build_success = True
called_something = False
overrides = ""

library_mtimes = []

quiet = 1

interrupted = False

show_commands = False

oldmd5s = {}
newmd5s = {}

times = []

starttime = 0
esttime = 0
lastupdate = -1

buildtime = -1

target = ""
CleanBuild = False
do_install = False

projects = {}
finished_projects = set()
built_files = set()

allfiles = []
total_precompiles = 0
precompiles_done = 0
total_compiles = 0

install_prefix="/usr/local/"

makefile_dict = {}

allheaders = {}

current_compile = 1

project_build_list = set()

sortedProjects = []

class dummy_block(object):
    """Some versions of python have a bug in threading where a dummy thread will try and use a value that it deleted.
    To keep that from erroring on systems with those versions of python, this is a dummy object with the required
    methods in it, which can be recreated in __init__ for the thread object to prevent this bug from happening.
    """

    def __init__(self):
        """Dummy __init__ method"""
        return

    def acquire(self):
        """Dummy acquire method"""
        return

    def release(self):
        """Dummy release method"""
        return

    def notify_all(self):
        """Dummy notify_all method"""
        return

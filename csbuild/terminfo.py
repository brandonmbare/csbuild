import platform
import sys

if platform.system() == "Windows":
    import ctypes
    import struct
else:
    import curses
    
class TermColor(object):
    if platform.system() == "Windows":
        DGREY = 0 | 8
        RED = 4 | 8
        GREEN = 2 | 8
        YELLOW = 2 | 4 | 8
        BLUE = 1 | 8
        MAGENTA = 1 | 4 | 8
        CYAN = 1 | 2 | 8
        WHITE = 1 | 2 | 4 | 8
        BLACK = 0
        DRED = 4
        DGREEN = 2
        DYELLOW = 2 | 4
        DBLUE = 1
        DMAGENTA = 1 | 4
        DCYAN = 1 | 2
        LGREY = 1 | 2 | 4
    else:
        DGREY = "1;30"
        RED = "1;31"
        GREEN = "1;32"
        YELLOW = "1;33"
        BLUE = "1;34"
        MAGENTA = "1;35"
        CYAN = "1;36"
        WHITE = "1;37"
        BLACK = "22;30"
        DRED = "22;31"
        DGREEN = "22;32"
        DYELLOW = "22;33"
        DBLUE = "22;34"
        DMAGENTA = "22;35"
        DCYAN = "22;36"
        LGREY = "22;37"
    
class TermInfo(object):
    @staticmethod
    def ResetColor():
        if platform.system() == "Windows":
            ctypes.windll.kernel32.SetConsoleTextAttribute(TermInfo._handle, TermInfo._reset)
        else:
            sys.stdout.write("\033[0m")
            
    @staticmethod
    def SetColor(color):
        if platform.system() == "Windows":
            ctypes.windll.kernel32.SetConsoleTextAttribute(TermInfo._handle, color)
        else:
            sys.stdout.write("\033[{}m".format(color))
            
    @staticmethod
    def GetNumColumns():
        if platform.system() == "Windows":
            csbi = ctypes.create_string_buffer(22)
            res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(TermInfo._handle, csbi)
            assert res

            (bufx, bufy, curx, cury, wattr,
            left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            
            return right - left
        else:
            if TermInfo.cursesValid:
                return curses.tigetnum('cols')
            else:
                return 0
            
    @staticmethod
    def SupportsColor():
        if platform.system() == "Windows":
            return TermInfo._color_supported
        else:
            if TermInfo.cursesValid:
                return (curses.tigetnum("colors") >= 8)
            else:
                return False
    
    @staticmethod
    def GetDefaultColor():
        if platform.system() == "Windows":
            # Based on IPython's winconsole.py, written by Alexander Belchenko
            import struct
            csbi = ctypes.create_string_buffer(22)
            res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(TermInfo._handle, csbi)
            assert res

            (bufx, bufy, curx, cury, wattr,
            left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            return wattr
        else:
            return "0"


if platform.system() == "Windows":
    # -11 = STD_OUTPUT_HANDLE
    try:
        TermInfo._handle = ctypes.windll.kernel32.GetStdHandle(-11)
        TermInfo._reset = TermInfo.GetDefaultColor()
    except:
        TermInfo._color_supported = False
    else:
        TermInfo._color_supported = True
else:
    try:
        curses.setupterm()
    except:
        TermInfo.cursesValid = False
    else:
        TermInfo.cursesValid = True

JMake
======

JMake is a python makefile program that's written to be both efficient and easy to use. Unlike GNU make, the syntax for JMake is very simple and easy to approach, while still being powerful. No deep understanding of g++'s hundreds of flags is required.

Additionally, JMake is designed to prevent doing more work than necessary whenever possible. Rather than specifying every file you want to compile, you specify files and directories you DON'T want to compile, so adding a new file to your project is as easy as creating it. And when compiling, JMake checks the header files in each of your source files, recompiling every necessary source file when an included header changes, but leaving alone the files that the header can't affect.

JMake is also intelligently multi-threaded and will use threads for compilation to enable maximum efficiency based on the hardware of your machine.

Finally, JMake combines "./configure" and "make" into one call, checking dependencies as part of its build process and alerting at the very start of the build if it can't find a required library.

Contents
======

[Usage](#usage) 

[Default command line arguments](#default-command-line-arguments) 

[Adding targets](#adding-targets) 

[Parsing command line arguments](#parsing-command-line-targets)

[The options](#the-options)

[Example script](#example-script)

Usage
======

Using jmake is easy: simply make a script in the top directory of your project named "make.py" (or any other name you'd like to use). Inside the script, you can set various options to control the build.

Because the build script is written in python, there's no limit to how you can control your build.

When you run jmake, it will automatically scan your current directory and all subdirectories for files to compile, following the philosophy that the files you DO want to compile are usually the norm, and the files you DON'T tend to be the exception - thus you should only need to specify the exceptions, not the full list of files in your project. It will also scan your computer for any required libraries (dictated by the make script) and will scan each c or cpp file for included headers. It then uses the information collected from this to intelligently determine which files need to be recompiled and which files don't - unlike other systems, which require you to specify what files to recompile when headers are changed, and often end up recompiling entire projects when you change a header used in only one source file, or do not detect at all that external headers or libraries have been modified.

Once jmake starts building your project, it will also intelligently determine the optimal number of threads to use for your hardware to minimize build time.

The result is that jmake creates a quick and efficient build environment that maximized turnaround and iteration time for your project.

Default command line arguments
======

By default, jmake supports the following targets with the following default targets:

"debug": Debug level 3, optimization level 0, object directory ./Debug/obj, output file directory ./Debug
"release": Debug level 0, optimization level 3, object directory ./Release/obj, output file directory ./Release

Additionally, the following switches can be used by default to impact the behavior of the build:

python make.py --clean <target>: Deletes all generated files for the target build
python make.py --install <target>: Install the target build. (This does nothing unless the make script has used one or both of InstallOutput() or InstallHeaders())
python make.py <target> --overrides="list;of;python;calls": The string passed to --overrides will be executed as python code, enabling the user to override any settings in the make script. For example, to customize the install directory, one method would be to use --overrides="InstallOutput('/path/to/output')"

Adding targets
======

To add a target to your build, simply create a function with the name of your target (in all lower case). For example, if you want to add a target named "all," simply create a function named "all" with your desired configuration in it.

Parsing command line arguments
======

You can parse command line arguments in your script using the python argparse module, with one notable change to its functionality: because JMake parses some arguments itself, you need to pass the value "jmake.args" to your parse_args function. I.e.:

The options
======

To control the build, use the following options:

jmake.InstallOutput( s = "/usr/local/lib" ) #Enables installation of the compiled output file. Default target is /usr/local/lib.
jmake.InstallHeaders( s = "/usr/local/include" ) #Enables installation of the project's headers. Default target is /usr/local/include.
jmake.ExcludeDirs( *args ) #Excludes the given subdirectories from the build. Accepts multiple string arguments.
jmake.ExcludeFiles( *args ) #Excludes the given files from the build. Accepts multiple string arguments.
jmake.Libraries( *args ) #List of libraries to link against. Multiple string arguments. gcc/g++ -l.
jmake.IncludeDirs( *args ) #List of directories to search for included headers. Multiple string arguments. gcc/g++ -I
                           #By default, this list contains /usr/include and /usr/local/include.
                           #Using this function will add to the existing list, not replace it.
jmake.LibDirs( *args ) #List of directories to search for libraries. Multiple string arguments. gcc/g++ -L 
                       #By default, this list contains /usr/lib and /usr/local/lib
                       #Using this function will add to the existing list, not replace it
jmake.ClearLibraries( ) #Clears the list of libraries
jmake.ClearIncludeDirs( ) #Clears the include directories, including the defaults.
jmake.ClearLibDirs( ) #Clears the library directories, including the defaults
jmake.Opt(i) #Sets the optimization level. gcc/g++ -O
jmake.Debug(i) #Sets the debug level. gcc/g++ -g
jmake.Define( *args ) #Sets defines for the project. Accepts multiple arguments. gcc/g++ -D
jmake.ClearDefines( *args ) #clears the list of defines
jmake.Undefine( *args ) #Sets undefines for the project. Multiple arguments. gcc/g++ -U
jmake.ClearUndefines( ) #clears the list of undefines
jmake.Compiler(s) #Sets the compiler to use for the project. Default is g++.
jmake.Output(s) #Sets the output file for the project. If unset, the project will be compiled as "JMade"
jmake.OutDir(s) #Sets the directory to place the compiled result
jmake.ObjDir(s) #Sets the directory to place pre-link objects
jmake.WarnFlags( *args ) #Sets warn flags for the project. Multiple arguments. gcc/g++ -W
jmake.ClearWarnFlags( ) #Clears the list of warning flags
jmake.Flags( *args ) #Sets miscellaneous flags for the project. Multiple arguments. gcc/g++ -f
jmake.ClearFlags( ) #Clears the list of misc flags
jmake.DisableAutoMake() #Disables the automatic build of the project at conclusion of the script
                        #If you turn this off, you will need to explicitly call either make() to build and link,
                        #or build() and link() to take each step individually
jmake.EnableAutoMake() #Turns the automatic build back on after disabling it
jmake.Shared() #Builds the project as a shared library. Enables -shared in the linker and -fPIC in the compiler.
jmake.NotShared() #Turns shared object mode back off after it was enabled.
jmake.Profile() #Enables profiling optimizations. gcc/g++ -pg
jmake.Unprofile() #Turns profiling back off.
jmake.ExtraFlags(s) #Literal string of extra flags to be passed directly to the compiler
jmake.ClearExtraFlags() #Clears the extra flags string
jmake.Standard(s) #The C/C++ standard to be used when compiling. gcc/g++ --std

Note that options that correlate to gcc/g++ flags do NOT need the flag passed with them. For example, if you're linking (i.e.) to the boost_thread library, you would simply call:

jmake.Libraries("boost_thread")

Example script
======

This script is used to compile the htt++ project, for which JMake was initially developed:

```python
#!/usr/bin/python

import jmake

#Project's required libraries
jmake.Libraries(
   "jnet",
   "jformat",
   "jhash",
   "boost_thread"
)

#Output file
jmake.Output("libhttpp.so")

#htt++ uses c++11, so we need to specify the standard
jmake.Standard("gnu++0x")

#htt++'s use of c++11 necessitates g++-4.7 or higher, so we need to specify that as well
jmake.Compiler("g++-4.7")

#Compile as a shared library
jmake.Shared()

#Let's be extra strict on the warning flags.
jmake.WarnFlags("all", "extra", "ctor-dtor-privacy", "old-style-cast", "overloaded-virtual", "init-self", "missing-include-dirs", "switch-default", "switch-enum", "undef")

#And set our project to install both the output file and the headers
jmake.InstallHeaders()
jmake.InstallOutput()
```
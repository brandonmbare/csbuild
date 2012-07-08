from distutils.core import setup
setup(name='JMake',
      version='0.9.02.2',
      py_modules=['jmake'],
      author="Jaedyn K. Draper",
      author_email="jaedyn.pypi@jaedyn.co",
      url="https://github.com/ShadauxCat/JMake",
      description="C/C++ build tool",
      long_description="""JMake is a python makefile program that's written to be both efficient and easy to use. Unlike GNU make, the syntax for JMake is very simple and easy to approach, while still being powerful. No deep understanding of g++'s hundreds of flags is required.
        
Additionally, JMake is designed to prevent doing more work than necessary whenever possible. Rather than specifying every file you want to compile, you specify files and directories you DON'T want to compile, so adding a new file to your project is as easy as creating it. And when compiling, JMake checks the header files in each of your source files, recompiling every necessary source file when an included header changes, but leaving alone the files that the header can't affect.
        
JMake is also intelligently multi-threaded and will use threads for compilation to enable maximum efficiency based on the hardware of your machine.
        
Finally, JMake combines \"./configure\" and \"make\" into one call, checking dependencies as part of its build process and alerting at the very start of the build if it can't find a required library.""",
      classifiers=[
         "Development Status :: 4 - Beta",
         "Environment :: Console",
         "Intended Audience :: Developers",
         "License :: OSI Approved :: GNU General Public License (GPL)",
         "Natural Language :: English",
         "Operating System :: POSIX :: Linux",
         "Programming Language :: C",
         "Programming Language :: C++",
         "Programming Language :: Python :: 2.7",
         "Topic :: Software Development :: Build Tools"
      ]
      )
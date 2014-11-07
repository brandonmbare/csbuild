#!/usr/bin/python

import csbuild

csbuild.Toolchain("gcc", "ios").Compiler().SetCppStandard("c++11")
csbuild.Toolchain("gcc", "ios").SetCppStandardLibrary("libc++")

csbuild.DisablePrecompile()
csbuild.DisableChunkedBuild()

OUT_DIR = "out/{project.activeToolchainName}-{project.outputArchitecture}/{project.targetName}"
INT_DIR = "obj/{project.activeToolchainName}-{project.outputArchitecture}/{project.targetName}/{project.name}"

csbuild.SetOutputDirectory(OUT_DIR)
csbuild.SetIntermediateDirectory(INT_DIR)

csbuild.AddIncludeDirectories("src")
csbuild.AddLibraryDirectories(OUT_DIR)


@csbuild.project("sharedLibrary", "src/sharedLibrary")
def sharedLibrary():
	csbuild.SetOutput("sharedLibrary", csbuild.ProjectType.SharedLibrary)


@csbuild.project("staticLibrary", "src/staticLibrary")
def sharedLibrary():
	csbuild.SetOutput("staticLibrary", csbuild.ProjectType.StaticLibrary)


@csbuild.project("loadableModule", "src/loadableModule")
def loadableModule():
	csbuild.SetOutput("loadableModule", csbuild.ProjectType.LoadableModule)


@csbuild.project("mainApp", "src/mainApp", ["sharedLibrary", "staticLibrary"])
def mainApp():
	csbuild.AddLibraries("sharedLibrary", "staticLibrary")
	csbuild.SetOutput("mainApp", csbuild.ProjectType.Application)

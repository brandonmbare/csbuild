import csbuild

#csbuild.SetActiveToolchain("android")

@csbuild.project("AndroidTest_Basic", "AndroidTest_Basic")
def AndroidTest_Basic():
	csbuild.Toolchain("android").CCompiler("clang")
	csbuild.Toolchain("android").CppCompiler("clang++")
	csbuild.Toolchain("android").PackageName("csbuild.UnitTest.AndroidBasic")
	csbuild.Toolchain("android").ActivityName("CSBUnitTestAndroidBasic")
	csbuild.NoPrecompile()
	csbuild.Output("AndroidTest_Basic", csbuild.ProjectType.Application)
	csbuild.Toolchain("android").Libraries("android", "m", "log", "dl", "c")
	csbuild.SupportedToolchains("msvc", "android")

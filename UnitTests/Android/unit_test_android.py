import csbuild

csbuild.SetActiveToolchain("android")

@csbuild.project("AndroidTest_Basic", "AndroidTest_Basic")
def AndroidTest_Basic():
	csbuild.Toolchain("android").CCompiler("clang")
	csbuild.Toolchain("android").CppCompiler("clang++")
	csbuild.NoPrecompile()
	csbuild.Output("AndroidTest_Basic", csbuild.ProjectType.Application)
	csbuild.Libraries("android", "m", "log", "dl", "c")

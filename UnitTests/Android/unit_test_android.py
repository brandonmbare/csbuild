import csbuild

csbuild.SetActiveToolchain("android")

@csbuild.project("AndroidTest_Basic", "AndroidTest_Basic")
def AndroidTest_Basic():
	csbuild.NoPrecompile()
	csbuild.Output("AndroidTest_Basic", csbuild.ProjectType.Application)
	csbuild.Libraries("android", "m", "log", "dl", "c")

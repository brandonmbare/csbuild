import csbuild

csbuild.SetActiveToolchain("android")

@csbuild.project("AndroidTest_Basic", "AndroidTest_Basic")
def AndroidTest_Basic():
    csbuild.Output("AndroidTest_Basic", csbuild.ProjectType.SharedLibrary)
    csbuild.Libraries("android")

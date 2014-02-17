import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import os
import sys

from csbuild import project_generator
from csbuild import _shared_globals
from csbuild import projectSettings
import csbuild

class project_generator_qtcreator(project_generator.project_generator):
    def __init__(self, path, solutionname):
        project_generator.project_generator.__init__(self, path, solutionname)

        self.qtpath = os.path.expanduser(csbuild.get_option("qtpath"))
        self.formatted_args = self.get_formatted_args(["qtpath"])

        self.update_qtcreator_config()

    @staticmethod
    def additional_args(parser):
        parser.add_argument("--qtpath", help="Path to QtCreator configuration (default ~/.config, should contain QtProject directory)",
                            default="~/.config")

    def _writeProject(self, project, parentNames):
        depth = len(parentNames)
        if depth == 0:
            parentPath = ""
        elif depth == 1:
            parentPath = parentNames[0]
        else:
            parentPath = os.path.join(*parentNames)

        projectpath = os.path.join(self.rootpath, parentPath, project.name)
        if not os.path.exists(projectpath):
            os.makedirs(projectpath)

        with open(os.path.join(projectpath, "{}.pro".format(project.name)), "w") as f:
            f.write("SOURCES += \\\n")
            for source in project.allsources:
                f.write("\t{} \\\n".format(os.path.abspath(source)))

            f.write("\nHEADERS += \\\n")
            for header in project.allheaders:
                f.write("\t{} \\\n".format(os.path.abspath(header)))

            f.write("\nDESTDIR = {}\n\n".format(project.output_dir))

            f.write("TARGET = {}\n\n".format(project.output_name))

            if project.type == csbuild.ProjectType.Application:
                f.write("TEMPLATE = app\n\n")
            else:
                f.write("TEMPLATE = lib\n\n")

            f.write("INCLUDEPATH += \\\n")

            for incdir in project.include_dirs:
                f.write("\t{} \\\n".format(incdir))

            if project.cpp_compiler_flags:
                f.write("\nQMAKE_CXXFLAGS += {}\n".format(" ".join(project.cpp_compiler_flags)))

            try:
                if project.cppstandard:
                    f.write("\nQMAKE_CXXFLAGS += -std={}\n".format(project.cppstandard))
            except:
                pass

            if project.c_compiler_flags:
                f.write("\nQMAKE_CFLAGS += {}\n".format(" ".join(project.c_compiler_flags)))

            try:
                if project.cstandard:
                    f.write("\nQMAKE_CXXFLAGS += -std={}\n".format(project.cstandard))
            except:
                pass

        with open(os.path.join(projectpath, "Makefile"), "w") as f:
            projstr =" --project {}".format(project.name)
            make_dir = os.getcwd()

            f.write("all:\n\t@cd {} && {} ./{}{} ${{ARGS}}\n\n".format(make_dir, sys.executable, csbuild.mainfile, projstr))
            f.write("clean:\n\t@cd {} && {} ./{}{} ${{ARGS}} --clean\n\n".format(make_dir, sys.executable, csbuild.mainfile, projstr))
            f.write("install:\n\t@cd {} && {} ./{}{} ${{ARGS}} --install\n\n".format(make_dir, sys.executable, csbuild.mainfile, projstr))

    def _writeSubdirsProject(self, projectGroup, parentNames, projlist):
        depth = len(parentNames)
        if depth == 0:
            parentPath = ""
        elif depth == 1:
            parentPath = parentNames[0]
        else:
            parentPath = os.path.join(*parentNames)

        parentNames.append(projectGroup.name)

        solutionname = projectGroup.name
        if not solutionname:
            solutionname = self.solutionname

        grouppath = os.path.join(self.rootpath, parentPath, projectGroup.name)
        if not os.path.exists(grouppath):
            os.makedirs(grouppath)

        allsubprojects = set()

        with open(os.path.join(grouppath, "{}.pro".format(solutionname)), "w") as f:
            f.write("TEMPLATE = subdirs\n\n")
            f.write("SUBDIRS += \\\n")

            for group in projectGroup.subgroups.items():
                f.write("\t{} \\\n".format(group[0]))
                subprojects = set()
                self._writeSubdirsProject(group[1], parentNames, subprojects)
                allsubprojects |= subprojects

            for proj in projectGroup.projects.items():
                f.write("\t{} \\\n".format(proj[0]))
                self._writeProject(proj[1], parentNames)
                allsubprojects.add(proj[0])

        projlist |= allsubprojects

        projstr = ""
        if depth != 0:
            for proj in allsubprojects:
                projstr += " --project {}".format(proj)

        with open(os.path.join(grouppath, "Makefile"), "w") as f:
            make_dir = os.getcwd()

            f.write("all:\n\t@cd {} && {} ./{}{} ${{ARGS}}\n\n".format(make_dir, sys.executable, csbuild.mainfile, projstr))
            f.write("clean:\n\t@cd {} && {} ./{}{} ${{ARGS}} --clean\n\n".format(make_dir, sys.executable, csbuild.mainfile, projstr))
            f.write("install:\n\t@cd {} && {} ./{}{} ${{ARGS}} --install\n\n".format(make_dir, sys.executable, csbuild.mainfile, projstr))

        del parentNames[-1]


    def _writeSharedFile(self):
        add = ET.SubElement

        root = ET.Element("qtcreator")
        data = add(root, "data")

        add(data, "variable").text = "ProjectExplorer.Project.ActiveTarget"
        add(data, "value", type="int").text="0"

        data = add(root, "data")

        add(data, "variable").text = "ProjectExplorer.Project.Target.0"

        vm = add(data, "valuemap", type="QVariantMap")

        add(vm, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DefaultDisplayName").text="CSBuild-AutoGenerated"
        add(vm, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DisplayName").text="CSBuild-AutoGenerated"
        add(vm, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.Id").text="{csbuild-default-profile}"
        add(vm, "value", type="int", key="ProjectExplorer.Target.ActiveBuildConfiguration").text="0"
        add(vm, "value", type="int", key="ProjectExplorer.Target.ActiveDeployConfiguration").text="0"
        add(vm, "value", type="int", key="ProjectExplorer.Target.ActiveRunConfiguration").text="0"

        stepcount = 0
        for target in _shared_globals.alltargets:
            vm2 = add(vm, "valuemap", type="QVariantMap", key="ProjectExplorer.Target.BuildConfiguration.{}".format(stepcount))
            stepcount += 1

            add(vm2, "value", type="QString", key="ProjectExplorer.BuildConfiguration.BuildDirectory").text=self.rootpath

            def addTarget(clean):
                vm3 = add(vm2, "valuemap", type="QVariantMap", key="ProjectExplorer.BuildConfiguration.BuildStepList.{}".format("1" if clean else "0"))

                vm4 = add(vm3, "valuemap", type="QVariantMap", key="ProjectExplorer.BuildStepList.Step.0")

                add(vm4, "value", type="bool", key="ProjectExplorer.BuildStep.Enabled").text="true"
                add(vm4, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DefaultDisplayName").text="Make"
                add(vm4, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DisplayName")
                add(vm4, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.Id").text="Qt4ProjectManager.MakeStep"

                vl = add(vm4, "valuelist", type="QVariantList", key="Qt4ProjectManager.MakeStep.AutomaticallyAddedMakeArguments")
                add(vl, "value", type="QString").text = "-w"
                add(vl, "value", type="QString").text = "-r"

                add(vm4, "value", type="bool", key="Qt4ProjectManager.MakeStep.Clean").text="true" if clean else "false"
                add(vm4, "value", type="QString", key="Qt4ProjectManager.MakeStep.MakeArguments").text="{}ARGS='{}{}'".format("clean " if clean else "", self.formatted_args, target)
                add(vm4, "value", type="QString", key="Qt4ProjectManager.MakeStep.MakeCommand")

                add(vm3, "value", type="int", key="ProjectExplorer.BuildStepList.StepsCount").text="1"
                add(vm3, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DefaultDisplayName").text="Clean" if clean else "Build"
                add(vm3, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DisplayName")
                add(vm3, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.Id").text="ProjectExplorer.BuildSteps.{}".format("Clean" if clean else "Build")

            addTarget(False)
            addTarget(True)

            add(vm2, "value", type="int", key="ProjectExplorer.BuildConfiguration.BuildStepListCount").text="2"
            add(vm2, "value", type="bool", key="ProjectExplorer.BuildConfiguration.ClearSystemEnvironment").text="false"
            add(vm2, "valuelist", type="QVariantList", key="ProjectExplorer.BuildConfiguration.UserEnvironmentChanges")

            add(vm2, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DefaultDisplayName").text=target
            add(vm2, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.DisplayName").text=target
            add(vm2, "value", type="QString", key="ProjectExplorer.ProjectConfiguration.Id").text="Qt4ProjectManager.Qt4BuildConfiguration"
            add(vm2, "value", type="QString", key="Qt4ProjectManager.Qt4BuildConfiguration.BuildConfiguration").text="2"
            add(vm2, "value", type="bool", key="Qt4ProjectManager.Qt4BuildConfiguration.UseShadowBuild").text="true"

        add(vm, "value", type="int", key="ProjectExplorer.Target.BuildConfigurationCount").text=str(stepcount)

        data = add(root, "data")
        add(data, "variable").text="ProjectExplorer.Project.TargetCount"
        add(data, "value", type="int").text="1"

        data = add(root, "data")
        add(data, "variable").text="ProjectExplorer.Project.Updater.FileVersion"
        add(data, "value", type="int").text="15"

        outxml = ET.tostring(root)
        self._printXml(outxml, os.path.join(self.rootpath, "{}.pro.shared".format(self.solutionname)), "QtCreatorProject")





    def write_solution(self):
        parentNames = []
        projlist = set()
        self._writeSubdirsProject(projectSettings.rootProject, parentNames, projlist)
        self._writeSharedFile()


    def update_qtcreator_config(self,):
        profilespath = os.path.join(self.qtpath, "QtProject", "qtcreator", "profiles.xml")
        tree = ET.parse(profilespath)

        root = tree.getroot()

        profilenum = 0
        needsadd = True
        metaindex = 0

        randomDebuggerInformation = ""
        randomToolchain = ""
        randomQtInformation = ""
        randomProfileIcon = ""

        index = 0
        for data in root.findall("data"):
            variable = data.find("variable")
            if variable.text == "Profile.Count":
                value = data.find("value")
                profilenum = int(value.text)+1
                value.text = str(profilenum)
                metaindex = index
            else:
                valuemap = data.find("valuemap")
                if valuemap is not None:
                    for value in valuemap.findall("value"):
                        if value.get("key") == "PE.Profile.Id":
                            if value.text == "{csbuild-default-profile}":
                                needsadd = False
                        elif value.get("key") == "PE.Profile.Icon":
                            randomProfileIcon = value.text
                    vm2 = valuemap.find("valuemap")
                    for value in vm2.findall("value"):
                        if value.get("key") == "Debugger.Information":
                            randomDebuggerInformation = value.text
                        elif value.get("key") == "PE.Profile.ToolChain":
                            randomToolchain = value.text
                        elif value.get("key") == "QtSupport.QtInformation":
                            randomQtInformation = value.text
            index += 1

        if not needsadd:
            return

        data = ET.Element("data")

        ET.SubElement(data, "variable").text = "Profile.{}".format(profilenum-1)

        valuemap = ET.SubElement(data, "valuemap", type="QVariantMap")
        ET.SubElement(valuemap, "value", type="bool", key="PE.Profile.AutoDetected").text = "false"

        vm2 = ET.SubElement(valuemap, "valuemap", type="QVariantMap", key="PE.Profile.Data")

        ET.SubElement(vm2, "value", type="QString", key="Android.GdbServer.Information")
        ET.SubElement(vm2, "value", type="QString", key="Debugger.Information").text = randomDebuggerInformation
        ET.SubElement(vm2, "value", type="QString", key="PE.Profile.Device").text = "Desktop Device"
        ET.SubElement(vm2, "value", type="QByteArray", key="PE.Profile.DeviceType").text = "Desktop"
        ET.SubElement(vm2, "value", type="QString", key="PE.Profile.SysRoot")
        ET.SubElement(vm2, "value", type="QString", key="PE.Profile.ToolChain").text = randomToolchain
        ET.SubElement(vm2, "value", type="QString", key="QtPM4.mkSpecInformation")
        ET.SubElement(vm2, "value", type="int", key="QtSupport.QtInformation").text = randomQtInformation
        ET.SubElement(valuemap, "value", type="QString", key="PE.Profile.Icon").text = randomProfileIcon
        ET.SubElement(valuemap, "value", type="QString", key="PE.Profile.Id").text = "{csbuild-default-profile}"
        ET.SubElement(valuemap, "valuelist", type="QVariantList", key="PE.Profile.MutableInfo")
        ET.SubElement(valuemap, "value", type="QString", key="PE.Profile.Name").text = "CSBuild-AutoGenerated"
        ET.SubElement(valuemap, "value", type="bool", key="PE.Profile.SDK")

        root.insert(metaindex, data)

        outxml = ET.tostring(root)

        self._printXml(outxml, profilespath, "QtCreatorProfiles")

    def _printXml(self, inxml, outfile, doctype):
        outxml = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE {}>\n<!-- Written by CSBuild using input from QTCreator -->\n{}'.format(doctype, inxml)

        formatted = minidom.parseString(outxml).toprettyxml(" ", "\n")
        inlist = formatted.split("\n")
        outlist = []

        for line in inlist:
            if line.strip():
                outlist.append(line)

        final = "\n".join(outlist)

        with open(outfile, "w") as f:
            f.write(final)

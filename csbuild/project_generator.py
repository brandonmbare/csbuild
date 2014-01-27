
from abc import abstractmethod
import os
import csbuild

class project_generator(object):
    def __init__(self, path, solutionname):
        self.rootpath = os.path.abspath(path)
        self.solutionname = solutionname

        args = csbuild.get_args()

        self.args={}
        for arg in args.items():
            if "generate_solution" in arg[0]:
                continue
            if "solution_name" in arg[0]:
                continue
            if "solution_path" in arg[0]:
                continue
            if "fakearg" in arg[0]:
                continue
            if arg[0] == "target":
                continue
            if arg[0] == "project":
                continue

            if arg[1] == csbuild.get_default_arg(arg[0]):
                continue

            self.args.update({arg[0].replace("_", "-"): arg[1]})

    def get_formatted_args(self, excludes):
        outstr = ""
        for arg in self.args.items():
            if arg[0] in excludes:
                continue

            outstr += "--{}={} ".format(arg[0], arg[1])
        return outstr

    @staticmethod
    def additional_args(parser):
        pass

    @abstractmethod
    def write_solution(self):
        pass
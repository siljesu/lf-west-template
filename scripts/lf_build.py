from west.commands import WestCommand  # your extension must subclass this
from west import log                   # use this for user output

import os
import subprocess
import re
import fnmatch

class LfBuild(WestCommand):
    def __init__(self):
        super().__init__(
            'lf-build',               # gets stored as self.name
            'Compile LF program and then run west build',  # self.help
            ""
        )
        # To use a specific lfc binary the following variable can be modified
        # or the path to the desired binary can be passed to `--lfc`
        self.lfcPath = "lfc"

    def do_add_parser(self, parser_adder):
        # This is a bit of boilerplate, which allows you full control over the
        # type of argparse handling you want. The "parser_adder" argument is
        # the return value of an argparse.ArgumentParser.add_subparsers() call.
        parser = parser_adder.add_parser(self.name,
                                         help=self.help,
                                         description=self.description)

        # Add some example options using the standard argparse module API.
        # parser.add_argument('-o', '--optional', help='an optional argument')
        # parser.add_argument('project_root', help='Path to root of project')
        parser.add_argument('main_lf', help='Name of main LF file')
        parser.add_argument('-w', '--west-commands', help='Arguments to forward to west')
        parser.add_argument('-c', '--conf-overlays', help='Additional configuration overlays')
        parser.add_argument('--lfc', help='Path to LFC binary')

        return parser           # gets stored as self.parser

    def do_run(self, args, unknown_args):
        
        if "src" not in args.main_lf.split("/"):
            print("ERROR: West lf-build must be invoked outside `src` folder")

        srcGenPath = args.main_lf.split(".")[0].replace("src", "src-gen")
        appPath = args.main_lf.split("src")[0]
        if appPath == "":
            appPath = "."

        # 1. Invoke lfc with clean flag `-c` and without invoking target
        #    compiler `n`.
        if args.lfc:
            self.lfcPath = args.lfc
        
        lfcCmd = f"{self.lfcPath} -c -n {args.main_lf}"
        print(f"Executing lfc command: `{lfcCmd}`")
        res = subprocess.Popen(lfcCmd, shell=True)
        ret = res.wait()
        if ret != 0:
            exit(1)

        if not args.west_commands:
            args.west_commands = ""
        
        # FIXME: This is a not-intuitive limitation from the users prespective.
        # But we use `-DOVERLAY_CONFIG` to mix in the prj.conf from the app
        # directory with the prj_lf.conf in the `src-gen`
        if "-DOVERLAY_CONFIG" in args.west_commands:
            print("Error: Use `--conf-overlays` option to pass config overlays to west")

        # Copy project configurations into src-gen 
        userConfigPaths="prj.conf"
        res = subprocess.Popen(f"cp {appPath}/prj.conf {srcGenPath}/", shell=True)
        if args.conf_overlays:
            res = subprocess.Popen(f"cp {appPath}/{args.conf_overlays} {srcGenPath}/", shell=True)
            userConfigPaths += f";{args.conf_overlays}"

        # Copy the Kconfig file into the src-gen directory
        res = subprocess.Popen(f"cp {appPath}/Kconfig {srcGenPath}/", shell=True)
        ret = res.wait()
        if ret != 0:
            exit(1)
        
        # Parse the generated CompileDefinitions.txt which should be 
        # forwarded to west
        compileDefs = ""
        with open(f"{srcGenPath}/CompileDefinitions.txt") as f:
            for line in f:
                    line = line.replace("\n", "")
                    compileDefs += f"-D{line} "

        print(compileDefs)
        # Invoke west in the `src-gen` directory. Pass in 
        westCmd = f"west build {srcGenPath} {args.west_commands} -- -DOVERLAY_CONFIG=\"{userConfigPaths}\" {compileDefs}"
        print(f"Executing west command: `{westCmd}`")
        res = subprocess.Popen(westCmd, shell=True)
        ret = res.wait()
        if ret != 0:
            exit(1)
            
class LfFedBuild(WestCommand):
    def __init__(self):
        super().__init__(
            'lf-fed-build',               # gets stored as self.name
            'Compile LF program and then run west build, tweaked for federated',  # self.help
            ""
        )
        # To use a specific lfc binary the following variable can be modified
        # or the path to the desired binary can be passed to `--lfc`
        self.lfcPath = "lfc"

    def do_add_parser(self, parser_adder):
        # This is a bit of boilerplate, which allows you full control over the
        # type of argparse handling you want. The "parser_adder" argument is
        # the return value of an argparse.ArgumentParser.add_subparsers() call.
        parser = parser_adder.add_parser(self.name,
                                         help=self.help,
                                         description=self.description)

        # Add some example options using the standard argparse module API.
        # parser.add_argument('-o', '--optional', help='an optional argument')
        # parser.add_argument('project_root', help='Path to root of project')
        parser.add_argument('main_lf', help='Name of main LF file')
        parser.add_argument('-w', '--west-commands', help='Arguments to forward to west')
        parser.add_argument('-c', '--conf-overlays', help='Additional configuration overlays')
        parser.add_argument('-n', '--no-lfc', action='store_true', help='Do not generate new code using lfc')
        parser.add_argument('--lfc', help='Path to LFC binary')

        return parser           # gets stored as self.parser

    def do_run(self, args, unknown_args):
        
        if "src" not in args.main_lf.split("/"):
            print("ERROR: West lf-fed-build must be invoked outside `src` folder")
            
        srcGenPath = args.main_lf.split(".")[0].replace("src", "fed-gen")+"/src-gen"

        appPath = args.main_lf.split("src")[0]
        if appPath == "":
            appPath = "."

        # 1. Invoke lfc with clean flag `-c` and without invoking target
        #    compiler `n`.
        if args.lfc:
            self.lfcPath = args.lfc
            
        if args.no_lfc:
            print("Not executing lfc command for this build.")
        else:
            lfcCmd = f"{self.lfcPath} -c -n {args.main_lf}"
            print(f"Executing lfc command: `{lfcCmd}`")
            res = subprocess.Popen(lfcCmd, shell=True)
            ret = res.wait()
            if ret != 0:
                exit(1)

        if not args.west_commands:
            args.west_commands = ""
        
        # FIXME: This is a not-intuitive limitation from the users prespective.
        # But we use `-DOVERLAY_CONFIG` to mix in the prj.conf from the app
        # directory with the prj_lf.conf in the `src-gen`
        if "-DOVERLAY_CONFIG" in args.west_commands:
            print("Error: Use `--conf-overlays` option to pass config overlays to west")

        federateNames = [name for name in os.listdir("./"+srcGenPath)]

        for fedName in federateNames:
            # Copy project configurations into src-gen 
            userConfigPaths=f"prj_{fedName}.conf"
            res = subprocess.Popen(f"cp {appPath}/prj_{fedName}.conf {srcGenPath}/{fedName}/", shell=True)
            ret = res.wait()
            if ret != 0:
                print(f"Warning: Could not find federate config file {userConfigPaths}, using default config file only.")
                userConfigPaths=""
                
            res = subprocess.Popen(f"cp {appPath}/mimxrt1170_evk_cm7_{fedName}.overlay {srcGenPath}/{fedName}/boards/mimxrt1170_evk_cm7.overlay", shell=True)
            ret = res.wait()
            if ret != 0:
                print(f"Warning: Could not find federate dts overlay file.")
                
            if args.conf_overlays:
                res = subprocess.Popen(f"cp {appPath}/{args.conf_overlays} {srcGenPath}/{fedName}/", shell=True)
                userConfigPaths += f";{args.conf_overlays}"

            # Copy the Kconfig file into the src-gen directory
            res = subprocess.Popen(f"cp {appPath}/Kconfig {srcGenPath}/{fedName}/", shell=True)
            ret = res.wait()
            if ret != 0:
                exit(1)

            # Parse the generated CompileDefinitions.txt which should be 
            # forwarded to west
            compileDefs = ""
            with open(f"{srcGenPath}/{fedName}/CompileDefinitions.txt") as f:
                for line in f:
                    line = line.replace("\n", "")
                    compileDefs += f"-D{line} "
                        
        for fedName in federateNames:
            # Let file copying finish before attempting to build one federate            
            print(compileDefs)
            # Invoke west in the `src-gen` directory. Pass in 
            westCmd = f"west build {srcGenPath}/{fedName} --build-dir ./zephyr-{fedName}-build {args.west_commands} -- -DCMAKE_BUILD_TYPE=Test -DOVERLAY_CONFIG=\"prj_{fedName}.conf\" {compileDefs}"
            print(f"Executing west command: `{westCmd}`")
            res = subprocess.Popen(westCmd, shell=True)
            ret = res.wait()
            if ret != 0:
                exit(1)

class LfFedFlash(WestCommand):
    def __init__(self):
        super().__init__(
            'lf-fed-flash',               # gets stored as self.name
            'Flash LF program binaries for different federation topology modes',  # self.help
            ""
        )

    def do_add_parser(self, parser_adder):
        # This is a bit of boilerplate, which allows you full control over the
        # type of argparse handling you want. The "parser_adder" argument is
        # the return value of an argparse.ArgumentParser.add_subparsers() call.
        parser = parser_adder.add_parser(self.name,
                                         help=self.help,
                                         description=self.description)

        # Add some example options using the standard argparse module API.
        # parser.add_argument('-o', '--optional', help='an optional argument')
        # parser.add_argument('project_root', help='Path to root of project')
        parser.add_argument('-m', '--mode', help='Federate topology mode. \n1: One federate on one board. The other federates and the RTI are launched on linux. \n2: One federate for each connected board. RTI is launched on linux. \n3: One federate and the RTI is launched on one board. The rest of the federates are launched on linux. \n4: One federate for each connected board. RTI will be launched aloongside one of them.')
        parser.add_argument('-n', '--num-boards', help='Number of connected boards.')

        return parser           # gets stored as self.parser

    def do_run(self, args, unknown_args):        

        matching_dirs = [elem for elem in os.listdir(os.getcwd()) if "build" in elem]

        if not matching_dirs:
            print("\nERROR: West lf-fed-flash must be invoked outside the build folder(s)\n")
        else:
            print(f"\nFound {len(matching_dirs)} build directories:")
            print(*matching_dirs, sep=", ")

        output = subprocess.getoutput("pyocd list")

        # String manipulation to extract board info
        outputList = output.split("\n")[2:]
        boardEntries = []

        for entry in outputList:
            refinedEntry = ' '.join(entry.split(" ")).split()
            if len(refinedEntry)==7:    # Board entry length
                boardEntries.append(refinedEntry)
        
        if len(boardEntries) == 0:
            print("\nError: No boards found. Check your connection or the board's debug setup. Exiting.\n")
            exit(1)
        # Print human readable board info
        print(f"\nFound {len(boardEntries)} board(s): ")
        for boardEntry in boardEntries:
            print(f"{boardEntry[6]} with unique ID {boardEntry[4]}")
        
        if args.mode == "1":
            if len(matching_dirs) != 1:
                print(f"\nWarning: Mode {args.mode} chosen with {len(matching_dirs)} federate build directories. Using only one.")
            if len(boardEntries) != 1:
                print(f"\nWarning: Mode {args.mode} chosen with {len(boardEntries)} connected boards. Using only one.")

            westCmd = f"west flash -r pyocd --build-dir {matching_dirs[0]} -i {boardEntries[0][4]}"
            print(f"\nExecuting west command: `{westCmd}`")

            res = subprocess.Popen(westCmd, shell=True)
            ret = res.wait()
            if ret != 0:
                exit(1)

            lfcCmd = f"lfc src/CompositionThreaded_linux.lf"
            res = subprocess.Popen(lfcCmd, shell=True)
            ret = res.wait()
            if ret != 0:
                exit(1)

            runCmd = f"fed-gen/CompositionThreaded_linux/bin/s -i \"Unidentified Federation\""
            res = subprocess.Popen(runCmd, shell=True)

            rtiCmd = f"RTI -n 2 -p 15047 -i \"Unidentified Federation\""
            res = subprocess.Popen(rtiCmd, shell=True)
            ret = res.wait()
            if ret != 0:
                exit(1)


        elif args.mode == "2":
            if len(matching_dirs) < 2:
                print(f"\nError: Mode {args.mode} chosen with only {len(matching_dirs)} federate build directories. Not enough. Exiting.")
                exit(1)
            if len(boardEntries) < 2:
                print(f"\nError: Mode {args.mode} chosen with only {len(boardEntries)} connected boards. Not enough. Exiting.")
                exit(1)
            if len(matching_dirs) > len(boardEntries):
                print(f"\nError: Mode {args.mode} chosen with {len(matching_dirs)} federate build directories, but only {len(boardEntries)} connected boards. Not enough. Exiting.")
                exit(1)
            elif len(matching_dirs) < len(boardEntries):
                print(f"\nWarning: Mode {args.mode} chosen with {len(matching_dirs)} federate build directories, but with {len(boardEntries)} connected boards. Using only {len(matching_dirs)} boards.")

            for fedBuildNum in range(0, len(matching_dirs)):
                westCmd = f"west flash -r pyocd --build-dir {matching_dirs[fedBuildNum]} -i {boardEntries[fedBuildNum][4]}"
                print(f"\nExecuting west command [{fedBuildNum+1}/{len(matching_dirs)}]: `{westCmd}`")

                res = subprocess.run(westCmd, shell=True)
                if res.returncode != 0:
                    print(f"\nError: flash failed")
                    exit(1)
                            
            #rtiCmd = f"RTI -n 2 -p 15047 -i \"Unidentified Federation\""
            #res = subprocess.Popen(rtiCmd, shell=True)
            #ret = res.wait()
            #if ret != 0:
            #    exit(1)
                
        # elif args.mode == "3":
        # elif args.mode == "4":
        
        else:
            print(f"\nError: {args.mode} is not a valid option. Try modes 1, 2, 3 or 4. Exiting.")
            exit(1)



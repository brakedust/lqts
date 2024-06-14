import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

# PYTHON_EXE = sys.executable
# py_version = "3.12.4"
# py_short_version_string = "".join(py_version.split(".")[:2])

SCRIPT_ROOT = Path(__file__).parent
print(SCRIPT_ROOT)

pyproj = tomllib.loads(Path(SCRIPT_ROOT / "pyproject.toml").read_text())

try:
    scripts = pyproj["tool"]["poetry"]["scripts"]
except KeyError:
    scripts = {}

package_name = pyproj["tool"]["poetry"]["name"]

depends = pyproj["tool"]["poetry"]["dependencies"]


setupenv = (False,)

install = (False,)
make_exes = (False,)
all = (False,)
makedist = (False,)
packages = []

wheel_dir = SCRIPT_ROOT / "dist"
build_dir = SCRIPT_ROOT / "dist_exe" / f"{package_name}-bin"

# if (all) {
#     setupenv = True
#     build = True
#     collect = True
#     install_wheels = True
# }


# repos = [ordered]@{ };
# (Get-Content .\git_repos.txt | ConvertFrom-Json).psobject.properties | ForEach-Object { repos[_.name] = _.Value }


# if the user specified any packages on the command line, then remove
# projects that were not specified.
# projects_all = repos.keys
projects = packages
# if (packages.Count -gt 0) {
#     foreach (proj in projects_all) {
#         if (packages -contains proj) {
#             projects.Add(proj) | out-null
#         }
#     }
# }
# else {
#     # if no projects were specified, process them all
#     projects = projects_all
# }

# echo projects

# src_dir = "C:\Users\CampbellBL\work\src\python_src"


# src_dir = "D:\src\python\build_local"
# wheel_dir = "D:\src\python\build_local\wheels2"

# today = "((get-date).Year)-((get-date).Month)-((get-date).Day)"

deps_dir = f"{SCRIPT_ROOT}\deps"
# build_dir = "wheel_dir\build"

# if ((Test-Path wheel_dir) -eq False) {
#     mkdir wheel_dir
# }

if not build_dir.exists():
    os.makedirs(build_dir, exist_ok=True)

# if ((Test-Path build_dir) -eq False) {
#     mkdir build_dir
# }


#########################################################################################
python_dir = build_dir / "python"
python_exe = python_dir / "python.exe"
py_version = "3.12.4"
py_short_version_string = "".join(py_version.split(".")[:2])
py_zip = Path(f"python-{py_version}-embed-amd64.zip")
py_zip_file = wheel_dir / py_zip
getpip = wheel_dir / "get-pip.py"
# python_exe_dist =


def info():
    print(f"{python_dir=}")
    print(f"{python_exe=}")
    print(f"{py_version=}")
    print(f"{py_zip=}")
    print(f"{py_zip_file=}")
    print(f"{getpip=}")

    print("scripts:")
    for script_name in scripts:
        print(f"    {script_name} = {scripts[script_name]}")


def setupenv():
    import urllib.request

    cwd = Path.cwd()

    os.chdir(wheel_dir)
    # Set-Location wheel_dir

    # Download Python
    if not py_zip.exists():
        # if ((Test-Path py_zip) -eq False) {
        # [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        # Invoke-WebRequest -Uri "https://www.python.org/ftp/python/py_version/py_zip" -OutFile wheel_dir\py_zip
        urllib.request.urlretrieve(
            f"https://www.python.org/ftp/python/{py_version}/{py_zip}", py_zip_file
        )
    # }
    if not getpip.exists():
        # [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        # Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile wheel_dir\get-pip.py
        result = urllib.request.urlretrieve(
            f"https://bootstrap.pypa.io/get-pip.py", getpip
        )
        print("++", result)
    # }

    # if ((Test-Path build_dir) -eq False) {
    #     mkdir build_dir
    # }
    # cd build_dir

    zipfile.PyZipFile(py_zip_file).extractall(python_dir)
    # Expand-Archive -Path wheel_dir\py_zip -DestinationPath python_dir

    # cd python_dir
    Path(python_dir / f"python{py_short_version_string}._pth").write_text(
        f"""
python{py_short_version_string}.zip
.
import site
"""
    )

    subprocess.call(f'"{python_exe}" "{getpip}"')

    subprocess.call(f'"{python_exe}" -m pip install --upgrade pip')
    # .python_exe wheel_dir\get-pip.py
    # Pop-Location


def install_with_pip(package_to_install, force=False):
    import shlex

    command = [str(python_exe), "-m", "pip", "install"]
    command.extend(shlex.split(package_to_install))
    if force:
        command.append("--force-reinstall")

    print("--> " + " ".join(command))

    subprocess.call(command)


def install_deps(local_only=False):
    """
    Install dependendencies defined in pyproject.toml
    """

    dep_constraints = ""

    for dep in depends:

        if dep.lower() == "python":
            continue

        if isinstance(depends[dep], dict):
            dep_constraints += " " + f'"{str(Path(depends[dep]["path"]).resolve())}"'
        else:
            if not local_only:
                dep_constraints += " " + f"{dep}=={depends[dep]}"

    print("~" * 40)
    install_with_pip(dep_constraints)


def install():
    """
    Install the latest built wheel from from the ./dist directory
    """
    wheel_files = [
        f
        for f in sorted(Path(wheel_dir).glob("*.whl"), key=lambda f: f.stat().st_mtime)
        if f.name.startswith(package_name)
    ]

    package_to_install = wheel_files[-1]

    install_with_pip(f'"{package_to_install}"')  # --no-deps')


def make_exes():
    """
    Creates an exe file and writes a line in entry_points.txt
    for each script defined in pyproject.toml
    """
    import shutil

    entry_points_file = build_dir / "entry_points.txt"
    output = ["[console_scripts]"]
    for script_name in scripts:
        exe_name = script_name
        func_call = scripts[script_name]
        output.append(f"{exe_name} = {func_call}")

        print(f"  Creating {exe_name}")
        shutil.copyfile("python_stub.exe", build_dir / f"{exe_name}.exe")

    entry_points_file.write_text("\n".join(output))

    #         Copy-Item ..\..\python_stub.exe "(exe_name).exe"
    #     }
    #     else {
    #         write-host line -ForegroundColor Red
    #     }
    # }
    # cd SCRIPT_ROOT


def zip_directory(path, zip_file_name):
    """
    Zips up a directory into a zip file
    Parameters
    ----------
    path
    zip_file_name
    """
    import os
    import zipfile

    zip_file_path = os.path.dirname(zip_file_name)
    os.makedirs(zip_file_path, exist_ok=True)

    with zipfile.ZipFile(zip_file_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(path):
            for file in files:
                zf.write(os.path.join(root, file))


import sys

info()

if "-setup" in sys.argv:
    setupenv()

if "-deps" in sys.argv:
    install_deps()

if "-install" in sys.argv:
    install()

if "-make_exes" in sys.argv:
    make_exes()

if "-package" in sys.argv:
    os.chdir(build_dir)
    package_file = f"{package_name}"
    zip_directory

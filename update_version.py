"""
This version scheme is predicated on having tags in the git repo
that define the major.minor version.  For instance, if we have
a tag named 'Version1.0', git describe might look like this:

$ git describe
Version1.0-39-g5a70505

The poetry version would be 1.0.39

The version embedded in the code would be 1.0.39+5a70505
(the 'g' character is not part of the git commit hash)

"""

from pathlib import Path
import subprocess

vstring = subprocess.check_output(["git", "describe"]).decode().strip()
vstring = vstring.replace("Version", "")
parts = vstring.split("-")

parts[2] = parts[2][1:]

vstring = f"{parts[0]}.{parts[1]}"
# print(vstring)
print("----------------\nPoetry")
subprocess.call(["poetry", "version", vstring])
print("----------------")

vstring2 = f"{parts[0]}.{parts[1]}+{parts[2]}"
# Path('version.py').write_text(f'VERSION = "{vstring2}"\n')
Path('lqts/version.py').write_text(f'VERSION = "{vstring2}"\n')
print(f'VERSION = "{vstring2}"\n')

"""
version
-------

Contains classes representing a version numbers.

The GitVersionInfo class is used for versioning python modules that are revision controlled with git.
Using GitVersion Info assumes that repository has a git tag that is a direct ancestor of the current
commit.  The tag should be of the form 'VersionX.Y' where X is the major revision and Y is the
minor revision.  GitVersionInfo uses the 'git describe' command
to get the version information.  The output of  'git describe' looks like 'VersionX.Y-s-#######', where *s*
is the number of commits made since the tag and ####### is the shortened commitish of the current tag.

The output of git describe looks like:

    1.0-2-g463e11c

When the version information is successfully pulled using 'git describe' the output of 'git describe' is
 written to the _version.py file.  When the source code is bundled and distributed, this becomes the source
 of the version information.

"""
import re
import os
import subprocess
from enum import Enum

# from .traits import CeresObject, Trait


class BuildType(Enum):

    dev = 0
    a = 1
    b = 2
    rc = 3
    c = 3
    post = 2


def _get_date():
    """
    Gets the dat in %Y-%m-%d format
    """
    from datetime import datetime

    return datetime.strftime(datetime.now(), "%Y-%m-%d")


class NotAGitRepoException(Exception):
    pass


class SmallVersionInfo:

    # Major = Trait(0, converter=int)
    # Minor = Trait(0, converter=int)

    def __init__(self, major=1, minor=0):
        """Initializes a new instance of this object"""

        self.Major = int(major)
        self.Minor = int(minor)

    def __str__(self):
        return "{0}.{1}".format(self.Major, self.Minor)

    @staticmethod
    def parse(value):
        vers = SmallVersionInfo()
        vers.Major, vers.Minor = [int(x) for x in value.split(".")]
        return vers

    def __repr__(self):
        return "SmallVersionInfo(major={0}, minor]{1})".format(self.Major, self.Minor)

    def __lt__(self, other):

        if self.Major < other.Major:
            return True
        elif self.Major > other.Major:
            return False
        elif self.Minor < other.Minor:
            return True
        else:
            return False

    def __eq__(self, other):

        if isinstance(other, str):
            return str(self) == other
        else:
            return (self.Major == other.Major) and (self.Minor == other.Minor)

    def __gt__(self, other):

        return not (self < other) and not (self == other)


class GitVersionInfo:
    """
    A Version number for a Python module based on the Git repository.

    This assumes that there is a tag in the ancestors for the current commit named something
    like "Version1.0", with only a major and minor number.  The "release" number is the number of
    commits since the tag plus the current committish.

    """

    re_pattern_full = re.compile(r"(\d+)\.(\d+)\-(\d+)\-(.+)")
    re_pattern_short = re.compile(r"(\d+)\.(\d+)")

    # major = Trait(1, converter=int)
    # minor = Trait(0, converter=int)
    # release = Trait(0, converter=int)
    # committish = Trait('', converter=str)

    def __init__(self, major=1, minor=0, release=0, committish=""):

        self.major = int(major)
        self.minor = int(minor)
        self.release = int(release)
        self.committish = committish

    def __str__(self):
        return "{0}.{1}.{2}+{3}".format(
            self.major, self.minor, self.release, self.committish
        )

    @classmethod
    def get(cls, repo_path=None):
        """
        Gets the version of a project by attempting to run the
        git describe command.  This relies on having tags with names
        like 'Version1.1'.  If successful then the file _version.py
        is written containing the version string.
        """

        try:
            try:
                pwd = os.getcwd()

                if repo_path:
                    os.chdir(repo_path)
                else:
                    repo_path = os.path.split(os.path.abspath(__file__))[0]
                    # os.chdir(repo_path)
                git_version_string = subprocess.check_output(
                    "git describe --match Version* --long",
                    stderr=subprocess.STDOUT,
                    shell=True,
                ).decode()
                if "fatal" in git_version_string:
                    raise NotAGitRepoException()

                # cls.save(git_version_string)

            except:
                from . import _version

                git_version_string = _version.version_string

            my_version = GitVersionInfo.parse(git_version_string)
            # cls.save(my_version.raw_version_string)
            os.chdir(pwd)
            return my_version

        except Exception as my_exception:
            os.chdir(pwd)
            raise my_exception

    @classmethod
    def parse(cls, value):
        """
        Parses a version from a string
        """

        try:
            vers_parts = cls.re_pattern_full.findall(value)[0]
        except IndexError:
            # The current commit is a tag so one the tag name
            # is included in value.  If this is the case we
            # will only get the major and minor version parts from
            # the tag name.  Set the release # to 0 and then
            # pull the commitish from the git repo.  This is wha the git rev-parse command does
            vers_parts = cls.re_pattern_short.findall(value)[0]

            release = "0"
            try:
                commitish = subprocess.check_output(
                    "git rev-parse HEAD", stderr=subprocess.STDOUT
                ).decode()
                commitish = commitish[:7]
                vers_parts += (release, commitish)
            except:
                vers_parts += (release,)

        vers = GitVersionInfo(*vers_parts)
        vers.committish = vers.committish[1:]
        return vers

    def __repr__(self):
        return "GitVersionInfo(major={0}, minor={1}, release={2}, committish={3})".format(
            self.major, self.minor, self.release, self.committish
        )

    def __lt__(self, other):

        if self.major < other.major:
            return True
        elif self.major > other.major:
            return False
        elif self.minor < other.minor:
            return True
        elif self.minor > other.minor:
            return False
        elif self.release < other.release:
            return True
        elif self.release < other.release:
            return False
        else:
            return False

    def __eq__(self, other):

        if isinstance(other, str):
            return str(self) == other
        else:
            return (
                (self.major == other.major)
                and (self.minor == other.minor)
                and (self.release == other.release)
                and (self.committish == other.committish)
            )

    def __gt__(self, other):

        return not self < other and not self == other

    @property
    def setuptools_version(self):
        """
        Returns the version string in a format exceptable for setuptools
        """
        return "{0}.{1}.{2}+{3}".format(
            self.major, self.minor, self.release, self.committish
        )

    @property
    def raw_version_string(self):
        """
        Returns the version as it would appear from the git describe command
        """
        return "{0}.{1}-{2}-{3}".format(
            self.major, self.minor, self.release, self.committish
        )

    @classmethod
    def save(cls, version_string, new_file):
        """
        Saves the version string to _version.py
        """
        # my_path = os.path.dirname(os.path.abspath(__file__))
        # new_file = os.path.join(my_path, 'version.py')
        with open(new_file, "w") as fid:
            fid.write('VERSION = "{0}"'.format(version_string.strip()))


def make_version_file(pkg_name):

    v = GitVersionInfo.get().setuptools_version

    my_path = os.path.dirname(os.path.abspath(__file__))
    new_file = os.path.join(my_path, "version.py")
    GitVersionInfo.save(v, new_file)

    new_file = os.path.join(my_path, pkg_name, "version.py")
    GitVersionInfo.save(v, new_file)

    return v


if __name__ == "__main__":

    pkg_name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    print(make_version_file(pkg_name))


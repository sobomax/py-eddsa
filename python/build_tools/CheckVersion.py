import sys
from distutils.errors import DistutilsOptionError

from setuptools import Command


class CheckVersion(Command):
    description = "Check package version against a git tag"
    user_options = [
        ("tag=", "t", "git tag to compare against package version"),
    ]

    def initialize_options(self):
        self.tag = None

    def finalize_options(self):
        if not self.tag:
            raise DistutilsOptionError("You must specify --tag")

    def run(self):
        pkg_version = self.distribution.get_version()
        accepted_tags = {f"v{pkg_version}"}
        if pkg_version.endswith(".0"):
            accepted_tags.add(f"v{pkg_version[:-2]}")
        if self.tag in accepted_tags:
            return
        sys.stderr.write(f"version {pkg_version} does not match tag {self.tag}\n")
        sys.exit(1)

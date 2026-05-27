import os
import shutil
import subprocess
from pathlib import Path

from setuptools import Command


class RunCTest(Command):
    description = "Build and run the C self-tests"
    user_options = []
    root_dir = Path(__file__).resolve().parents[2]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        build_dir = self.root_dir / "build" / "python-ctest"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True)

        env = os.environ.copy()
        subprocess.run(
            [
                "cmake",
                "-S",
                str(self.root_dir),
                "-B",
                str(build_dir),
                "-DBUILD_STATIC=ON",
                "-DBUILD_TESTING=ON",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            ],
            check=True,
            env=env,
        )
        subprocess.run(
            ["cmake", "--build", str(build_dir), "--config", "Release"],
            check=True,
            env=env,
        )
        subprocess.run(
            ["ctest", "--test-dir", str(build_dir), "--output-on-failure", "-C", "Release"],
            check=True,
            env=env,
        )

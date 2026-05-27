#!/usr/bin/env python

import os
import re
import shutil
import sys
from pathlib import Path
from sysconfig import get_config_var, get_platform

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.command.sdist import sdist as _sdist

SETUP_DIR = Path(__file__).resolve().parent
ROOT_DIR = SETUP_DIR.parent
sys.path.insert(0, str(SETUP_DIR))

from build_tools.CheckVersion import CheckVersion
from build_tools.RunCTest import RunCTest


os.chdir(SETUP_DIR)

PACKAGE_NAME = "py-eddsa"

is_win = get_platform().startswith("win")
is_mac = get_platform().startswith("macosx-")
is_elf = not is_win and not is_mac

vendor_lib_dir = Path("eddsa/_vendor/lib")
checkout_lib_dir = Path("../lib")


def read_version():
    cmake_lists = ROOT_DIR / "CMakeLists.txt"
    if not cmake_lists.exists():
        cmake_lists = Path("CMakeLists.txt")
    text = cmake_lists.read_text(encoding="utf-8")

    parts = {}
    for name in ("MAJOR", "MINOR"):
        match = re.search(rf"set\s*\(\s*EDDSA_VERSION_{name}\s+([0-9]+)\s*\)", text)
        if match is None:
            raise RuntimeError(f"EDDSA_VERSION_{name} not found in {cmake_lists}")
        parts[name] = match.group(1)
    return f"{parts['MAJOR']}.{parts['MINOR']}.0"


VERSION = read_version()

lib_sources = [
    "fld.c",
    "sc.c",
    "ed.c",
    "sha512.c",
    "ed25519-sha512.c",
    "x25519.c",
    "burn.c",
    "burnstack.c",
]

sources = ["eddsa/_eddsa.c"] + [str(vendor_lib_dir / source) for source in lib_sources]

define_macros = [
    ("EDDSA_STATIC", "1"),
    ("USE_STACKCLEAN", "1"),
]

extra_compile_args = []
extra_link_args = []

if is_win:
    extra_compile_args.extend(["/O2", "/GL"])
    extra_link_args.append("/LTCG")
else:
    cc = (os.environ.get("CC") or get_config_var("CC") or "").lower()
    extra_compile_args.extend([
        "-std=c99",
        "-fwrapv",
        "-Wall",
        "-Wextra",
        "-pedantic",
        "-O3",
        "-flto",
        "-fvisibility=hidden",
    ])
    extra_link_args.append("-flto")
    if "clang" in cc:
        extra_compile_args.append("-Wno-gnu-zero-variadic-macro-arguments")

if get_platform() == "linux-x86_64":
    # Avoid depending on x86-64-v2 instructions in manylinux builds.
    extra_compile_args.append("-march=x86-64")

if is_elf:
    extra_link_args.append("-Wl,--version-script=eddsa/_eddsa.map")
elif is_mac:
    extra_link_args.extend([
        "-Wl,-exported_symbols_list,eddsa/_eddsa.exports",
        "-undefined",
        "dynamic_lookup",
    ])


class Sdist(_sdist):
    _temp_project_files = []

    def _sync_project_files(self):
        for filename in ("README.md", "LICENSE", "CMakeLists.txt"):
            dst = SETUP_DIR / filename
            if not dst.exists():
                shutil.copy2(ROOT_DIR / filename, dst)
                self._temp_project_files.append(dst)

    def _sync_vendor_lib(self):
        if vendor_lib_dir.exists():
            shutil.rmtree(vendor_lib_dir)
        vendor_lib_dir.mkdir(parents=True)
        for path in (ROOT_DIR / "lib").iterdir():
            if path.is_file() and path.suffix in {".c", ".h"}:
                shutil.copy2(path, vendor_lib_dir / path.name)

    def run(self):
        self._sync_project_files()
        self._sync_vendor_lib()
        try:
            super().run()
        finally:
            shutil.rmtree(vendor_lib_dir.parent, ignore_errors=True)
            for path in self._temp_project_files:
                path.unlink(missing_ok=True)

    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)

        base = Path(base_dir)
        for filename in ("README.md", "LICENSE", "CMakeLists.txt"):
            shutil.copy2(ROOT_DIR / filename, base / filename)

        release_vendor_lib = base / vendor_lib_dir
        release_vendor_lib.mkdir(parents=True, exist_ok=True)
        for path in (ROOT_DIR / "lib").iterdir():
            if path.is_file() and path.suffix in {".c", ".h"}:
                shutil.copy2(path, release_vendor_lib / path.name)


class BuildExt(_build_ext):
    def build_extension(self, ext):
        if not (vendor_lib_dir / "eddsa.h").exists():
            ext.sources = ["eddsa/_eddsa.c"] + [str(checkout_lib_dir / source) for source in lib_sources]
            ext.include_dirs = [str(checkout_lib_dir)]
        super().build_extension(ext)


module = Extension(
    "eddsa._eddsa",
    sources=sources,
    include_dirs=[str(vendor_lib_dir)],
    define_macros=define_macros,
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

RunCTest.root_dir = ROOT_DIR

readme = ROOT_DIR / "README.md"
if not readme.exists():
    readme = Path("README.md")

with readme.open("r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description="CPython wrapper for libeddsa Ed25519 and X25519 primitives",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Maksym Sobolyev",
    author_email="sobomax@gmail.com",
    url="https://github.com/sippy/py-eddsa.git",
    packages=["eddsa"],
    ext_modules=[module],
    cmdclass={
        "sdist": Sdist,
        "build_ext": BuildExt,
        "runctest": RunCTest,
        "checkversion": CheckVersion,
    },
    license="Unlicense",
    package_data={"eddsa": ["_eddsa.map", "_eddsa.exports"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: C",
        "Programming Language :: Python :: 3",
        "Topic :: Security :: Cryptography",
    ],
    python_requires=">=3.8",
)

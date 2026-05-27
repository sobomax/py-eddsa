#!/usr/bin/env python

import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from sysconfig import get_config_var
from sysconfig import get_platform

try:
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler
except ImportError:
    from distutils.ccompiler import new_compiler
    from distutils.sysconfig import customize_compiler


THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parents[1]
LIB_DIR = ROOT_DIR / "lib"
BUILD_DIR = ROOT_DIR / "build" / "benchmark-c"

LIB_SOURCES = [
    "fld.c",
    "sc.c",
    "ed.c",
    "sha512.c",
    "ed25519-sha512.c",
    "x25519.c",
    "burn.c",
    "burnstack.c",
]


def compile_args():
    if get_platform().startswith("win"):
        if os.environ.get("CC", "").lower() == "clang-cl":
            return ["/std:clatest", "/O2", "/GL"], ["/LTCG", "-fuse-ld=lld"]
        return ["/std:clatest", "/O2", "/GL"], ["/LTCG"]
    cc = (os.environ.get("CC") or get_config_var("CC") or "").lower()
    c_args = [
        "-std=c99",
        "-fwrapv",
        "-Wall",
        "-Wextra",
        "-pedantic",
        "-O3",
        "-flto",
        "-fvisibility=hidden",
    ]
    if "clang" in cc:
        c_args.append("-Wno-gnu-zero-variadic-macro-arguments")
    if get_platform() == "linux-x86_64":
        c_args.append("-march=x86-64")
    return c_args, ["-flto"]


def build_clang_cl_executable():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    sources = [str(THIS_DIR / "benchmark_c.c")]
    sources.extend(str(LIB_DIR / name) for name in LIB_SOURCES)
    objects = []
    c_args, l_args = compile_args()

    for source in sources:
        obj_path = BUILD_DIR / (Path(source).stem + ".obj")
        subprocess.run([
            "clang-cl",
            "/nologo",
            "/c",
            f"/I{LIB_DIR}",
            "/DEDDSA_STATIC=1",
            "/DUSE_STACKCLEAN=1",
            *c_args,
            source,
            f"/Fo{obj_path}",
        ], check=True)
        objects.append(str(obj_path))

    exe_path = BUILD_DIR / "benchmark_c.exe"
    subprocess.run([
        "clang-cl",
        "/nologo",
        *objects,
        f"/Fe{exe_path}",
        "/link",
        *l_args,
    ], check=True)
    return exe_path


def build_executable():
    if get_platform().startswith("win") and os.environ.get("CC", "").lower() == "clang-cl":
        return build_clang_cl_executable()

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    compiler = new_compiler()
    customize_compiler(compiler)
    c_args, l_args = compile_args()
    sources = [str(THIS_DIR / "benchmark_c.c")]
    sources.extend(str(LIB_DIR / name) for name in LIB_SOURCES)

    objects = compiler.compile(
        sources,
        output_dir=str(BUILD_DIR),
        include_dirs=[str(LIB_DIR)],
        macros=[("EDDSA_STATIC", "1"), ("USE_STACKCLEAN", "1")],
        extra_preargs=c_args,
    )

    exe_path = BUILD_DIR / "benchmark_c"
    compiler.link_executable(objects, str(exe_path), extra_postargs=l_args)
    if get_platform().startswith("win"):
        exe_path = exe_path.with_suffix(".exe")
    return exe_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--target", default=os.environ.get("BENCHMARK_TARGET", "local"))
    parser.add_argument("--compiler", default=os.environ.get("BENCHMARK_COMPILER", "unknown"))
    args = parser.parse_args()

    exe_path = build_executable()
    output = subprocess.check_output([str(exe_path)], text=True)
    result = json.loads(output)
    result.update({
        "api": "C",
        "target": args.target,
        "compiler": args.compiler,
        "platform": platform.platform(),
        "runs": 1,
    })

    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()

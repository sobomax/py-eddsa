#!/usr/bin/env python

import argparse
import importlib.metadata
import json
import os
import platform
import random
import statistics
import time

import eddsa


MIN_SECONDS = 0.2
SAMPLES = 5
RNG_SEED = 0xedd5a


def measure(func):
    loops = 1
    while True:
        start = time.perf_counter()
        for _ in range(loops):
            func()
        elapsed = time.perf_counter() - start
        if elapsed >= MIN_SECONDS:
            break
        loops *= 2

    samples = []
    for _ in range(SAMPLES):
        start = time.perf_counter()
        for _ in range(loops):
            func()
        samples.append(time.perf_counter() - start)

    per_op = min(samples) / loops
    return {
        "loops": loops,
        "seconds": per_op,
        "ops_per_second": 1.0 / per_op,
        "median_seconds": statistics.median(samples) / loops,
    }


def build_operations():
    rng = random.Random(RNG_SEED)
    sec = bytes(rng.randrange(256) for _ in range(32))
    other_sec = bytes(rng.randrange(256) for _ in range(32))
    msg = bytes(rng.randrange(256) for _ in range(256))
    pub = eddsa.ed25519_genpub(sec)
    sig = eddsa.ed25519_sign(sec, pub, msg)
    point = eddsa.x25519_base(other_sec)

    return [
        ("ed25519_genpub", lambda: eddsa.ed25519_genpub(sec)),
        ("ed25519_sign_256b", lambda: eddsa.ed25519_sign(sec, pub, msg)),
        ("ed25519_verify_256b", lambda: eddsa.ed25519_verify(sig, pub, msg)),
        ("x25519_base", lambda: eddsa.x25519_base(sec)),
        ("x25519", lambda: eddsa.x25519(sec, point)),
        ("pk_ed25519_to_x25519", lambda: eddsa.pk_ed25519_to_x25519(pub)),
        ("sk_ed25519_to_x25519", lambda: eddsa.sk_ed25519_to_x25519(sec)),
    ]


def markdown_table(result):
    lines = [
        f"### Python {result['python_version']} benchmark",
        "",
        "| Operation | ops/sec | usec/op |",
        "| --- | ---: | ---: |",
    ]
    for name, data in result["benchmarks"].items():
        lines.append(
            f"| `{name}` | {data['ops_per_second']:,.0f} | {data['seconds'] * 1_000_000:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path")
    parser.add_argument("--markdown", dest="markdown_path")
    parser.add_argument("--target", default=os.environ.get("BENCHMARK_TARGET", "local"))
    parser.add_argument("--compiler", default=os.environ.get("BENCHMARK_COMPILER", "unknown"))
    parser.add_argument("--wheel", default=os.environ.get("BENCHMARK_WHEEL", "unknown"))
    args = parser.parse_args()

    result = {
        "package": "py-eddsa",
        "package_version": importlib.metadata.version("py-eddsa"),
        "api": "Python",
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "target": args.target,
        "compiler": args.compiler,
        "wheel": args.wheel,
        "runs": 1,
        "benchmarks": {},
    }

    for name, func in build_operations():
        result["benchmarks"][name] = measure(func)

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True)
            fh.write("\n")

    table = markdown_table(result)
    if args.markdown_path:
        with open(args.markdown_path, "w", encoding="utf-8") as fh:
            fh.write(table)
    elif not args.json_path:
        print(table)


if __name__ == "__main__":
    main()

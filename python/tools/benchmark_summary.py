#!/usr/bin/env python

import argparse
import json
from pathlib import Path


OPERATIONS = [
    ("ed25519_genpub", "genpub"),
    ("ed25519_sign_256b", "sign 256B"),
    ("ed25519_verify_256b", "verify 256B"),
    ("x25519_base", "x25519 base"),
    ("x25519", "x25519"),
    ("pk_ed25519_to_x25519", "pk convert"),
    ("sk_ed25519_to_x25519", "sk convert"),
]


def ops_per_second(result, name):
    return result["benchmarks"][name]["ops_per_second"]


def kilo_ops_per_second(result, name):
    return ops_per_second(result, name) / 1000.0


def wheel_suffix(result):
    wheel = result.get("wheel", "unknown")
    prefix = f"py_eddsa-{result.get('package_version', '')}-"
    if wheel.startswith(prefix):
        return wheel[len(prefix):]
    return wheel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args()

    results = []
    for pattern in args.results:
        for path in sorted(Path().glob(pattern)):
            with path.open("r", encoding="utf-8") as fh:
                results.append(json.load(fh))

    results.sort(key=lambda item: (
        item.get("target", ""),
        item.get("compiler", ""),
        tuple(int(part) for part in item["python_version"].split(".")[:3]),
    ))

    lines = [
        "## py-eddsa benchmarks",
        "",
        f"{len(results)} tested wheels benchmarked.",
        "",
        "| Target | Compiler | Python | Wheel | "
        + " | ".join(label for _, label in OPERATIONS)
        + " |",
        "| --- | --- | --- | --- | "
        + " | ".join("---:" for _ in OPERATIONS)
        + " |",
    ]

    for result in results:
        cells = [
            result.get("target", ""),
            result.get("compiler", ""),
            result["python_version"],
            f"`{wheel_suffix(result)}`",
        ]
        cells.extend(f"{kilo_ops_per_second(result, name):,.1f}" for name, _ in OPERATIONS)
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend([
        "",
        "Values are thousands of operations per second (Kps). Larger is better.",
        "",
    ])

    output = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()

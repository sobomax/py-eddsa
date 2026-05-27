#!/usr/bin/env python

import argparse
import html
import json
import re
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


def format_kps(result, name):
    return f"{kilo_ops_per_second(result, name):,.1f}"

_uar = b'\xf0\x9f\x94\xba'.decode('utf-8') # Up arrow (red)
_dar = b'\xe2\xac\x87\xef\xb8\x8f'.decode('utf-8') # Down arrow

def format_delta_from_c(result, c_result, name):
    if c_result is None:
        return ""
    c_ops = ops_per_second(c_result, name)
    if c_ops == 0:
        return ""
    delta = (ops_per_second(result, name) / c_ops - 1.0) * 100.0
    tag, icon = ('strong', _uar) if delta >= 0 else ('em', _dar)
    sign = "+" if delta >= 0 else ""
    return f'[<{tag}>{sign}{delta:.1f}%</{tag}>]{icon}'


def format_python_cell(result, c_result, name):
    return f"{format_kps(result, name)} {format_delta_from_c(result, c_result, name)}"


def average_group(group):
    averaged = {
        "api": group[0].get("api", "Python"),
        "target": group[0].get("target", ""),
        "compiler": group[0].get("compiler", ""),
        "runs": len(group),
        "benchmarks": {},
    }
    for name, _ in OPERATIONS:
        averaged["benchmarks"][name] = {
            "ops_per_second": sum(ops_per_second(item, name) for item in group) / len(group)
        }
    return averaged


def wheel_suffix(result):
    wheel = result.get("wheel", "unknown")
    prefix = f"py_eddsa-{result.get('package_version', '')}-"
    if wheel.startswith(prefix):
        wheel = wheel[len(prefix):]
    if wheel.endswith(".whl"):
        wheel = wheel[:-4]
    return wheel


def wheel_architecture(result):
    parts = wheel_suffix(result).split("-", 2)
    if len(parts) == 3:
        arch = parts[2]
    else:
        arch = wheel_suffix(result)
    if "_" in arch:
        return arch.split("_", 1)[1]
    return arch


def python_sort_version(result):
    parts = [int(part) for part in re.findall(r"\d+", result.get("python_version", ""))]
    return tuple((parts + [0, 0, 0])[:3])


def append_python_table(lines, python_results, c_by_platform):
    lines.extend([
        "<table>",
        "<thead>",
        "<tr>",
        "<th>Target</th>",
        "<th>Compiler</th>",
        "<th>Python</th>",
        "<th>Architecture</th>",
    ])
    for _, label in OPERATIONS:
        lines.append(f"<th>{html.escape(label)}</th>")
    lines.extend([
        "</tr>",
        "</thead>",
        "<tbody>",
    ])

    target_groups = []
    for result in python_results:
        if not target_groups or target_groups[-1][0] != result.get("target", ""):
            target_groups.append((result.get("target", ""), []))
        target_groups[-1][1].append(result)

    for target, target_rows in target_groups:
        compiler_groups = []
        for result in target_rows:
            if not compiler_groups or compiler_groups[-1][0] != result.get("compiler", ""):
                compiler_groups.append((result.get("compiler", ""), []))
            compiler_groups[-1][1].append(result)

        target_cell_pending = True
        for compiler, compiler_rows in compiler_groups:
            compiler_cell_pending = True
            c_result = c_by_platform.get((target, compiler))
            arch_groups = []
            for result in compiler_rows:
                arch = wheel_architecture(result)
                if not arch_groups or arch_groups[-1][0] != arch:
                    arch_groups.append((arch, []))
                arch_groups[-1][1].append(result)

            for arch, arch_rows in arch_groups:
                arch_cell_pending = True
                for result in arch_rows:
                    lines.append("<tr>")
                    if target_cell_pending:
                        lines.append(
                            f'<td rowspan="{len(target_rows)}">{html.escape(target)}</td>'
                        )
                        target_cell_pending = False
                    if compiler_cell_pending:
                        lines.append(
                            f'<td rowspan="{len(compiler_rows)}">{html.escape(compiler)}</td>'
                        )
                        compiler_cell_pending = False
                    lines.append(f'<td>{html.escape(result.get("python_version", ""))}</td>')
                    if arch_cell_pending:
                        lines.append(
                            f'<td rowspan="{len(arch_rows)}"><code>{html.escape(arch)}</code></td>'
                        )
                        arch_cell_pending = False
                    for name, _ in OPERATIONS:
                        lines.append(
                            f'<td align="right"><p>{format_python_cell(result, c_result, name)}</p></td>'
                        )
                    lines.append("</tr>")

    lines.extend([
        "</tbody>",
        "</table>",
    ])


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

    python_results = []
    c_groups = {}
    for result in results:
        if result.get("api", "Python") == "C":
            key = (
                result.get("target", ""),
                result.get("compiler", ""),
            )
            c_groups.setdefault(key, []).append(result)
        else:
            python_results.append(result)

    c_results = [average_group(group) for group in c_groups.values()]
    python_results.sort(key=lambda item: (
        item.get("target", ""),
        item.get("compiler", ""),
        python_sort_version(item),
        wheel_suffix(item),
    ))
    c_results.sort(key=lambda item: (
        item.get("target", ""),
        item.get("compiler", ""),
    ))
    c_by_platform = {
        (result.get("target", ""), result.get("compiler", "")): result
        for result in c_results
    }

    lines = [
        "## py-eddsa benchmarks",
        "",
        f"{len(python_results)} Python wheel runs and {len(results) - len(python_results)} C API runs benchmarked.",
        "",
        "### Python API",
        "",
    ]

    append_python_table(lines, python_results, c_by_platform)

    lines.extend([
        "",
        "### C API",
        "",
        "| Target | Compiler | Runs | "
        + " | ".join(label for _, label in OPERATIONS)
        + " |",
        "| --- | --- | ---: | "
        + " | ".join("---:" for _ in OPERATIONS)
        + " |",
    ])

    for result in c_results:
        cells = [
            result.get("target", ""),
            result.get("compiler", ""),
            str(result["runs"]),
        ]
        cells.extend(f"{kilo_ops_per_second(result, name):,.1f}" for name, _ in OPERATIONS)
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend([
        "",
        "Values are thousands of operations per second (Kps). Python `% C` cells are relative to the matching averaged C API row. Larger is better.",
        "",
    ])

    output = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()

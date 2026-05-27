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


def column_label(result):
    return "<br>".join([
        html.escape(result.get("target", "")),
        html.escape(result.get("compiler", "")),
        html.escape(result.get("python_version", "")),
        f"<code>{html.escape(wheel_architecture(result))}</code>",
    ])


def c_column_label(result):
    return "<br>".join([
        html.escape(result.get("target", "")),
        html.escape(result.get("compiler", "")),
        f"runs={result['runs']}",
    ])


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
        "<th>Operation</th>",
    ])
    for result in python_results:
        lines.append(f"<th>{column_label(result)}</th>")
    lines.extend([
        "</tr>",
        "</thead>",
        "<tbody>",
    ])

    for name, label in OPERATIONS:
        lines.append("<tr>")
        lines.append(f"<td>{html.escape(label)}</td>")
        for result in python_results:
            c_result = c_by_platform.get((result.get("target", ""), result.get("compiler", "")))
            lines.append(
                f'<td align="right"><p>{format_python_cell(result, c_result, name)}</p></td>'
            )
        lines.append("</tr>")

    lines.extend([
        "</tbody>",
        "</table>",
    ])


def append_c_table(lines, c_results):
    lines.extend([
        "<table>",
        "<thead>",
        "<tr>",
        "<th>Operation</th>",
    ])
    for result in c_results:
        lines.append(f"<th>{c_column_label(result)}</th>")
    lines.extend([
        "</tr>",
        "</thead>",
        "<tbody>",
    ])

    for name, label in OPERATIONS:
        lines.append("<tr>")
        lines.append(f"<td>{html.escape(label)}</td>")
        for result in c_results:
            lines.append(f'<td align="right">{format_kps(result, name)}</td>')
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
    ])

    append_c_table(lines, c_results)

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

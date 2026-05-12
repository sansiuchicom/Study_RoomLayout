"""Phase 0 demo for the atomic subdivision testfield."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ALGORITHM_ROOT = Path(__file__).resolve().parents[1]
if str(ALGORITHM_ROOT) not in sys.path:
    sys.path.insert(0, str(ALGORITHM_ROOT))

from celllayout_tf import cases
from celllayout_tf.zoning import zone_footprint


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("case_indices", nargs="*", type=int)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or [])
    all_cases = cases.make_cases()
    selected = (
        [(i, all_cases[i - 1]) for i in args.case_indices if 1 <= i <= len(all_cases)]
        if args.case_indices
        else list(enumerate(all_cases, start=1))
    )

    failures = []
    print(f"{'#':>3} {'Case':<26} | zones faces gap_area overlap_area outside invalid ok")
    print("=" * 86)
    for idx, (name, footprint) in selected:
        try:
            result = zone_footprint(footprint)
            report = result.validation
            print(
                f"{idx:>3} {name:<26} | "
                f"{len(result.zones):>5} {len(result.subdivision.faces):>5} "
                f"{report.gap_area:.9f} {report.overlap_area:.9f} "
                f"{report.outside_area:.9f} {report.invalid_count:>7} {report.ok}"
            )
            if not report.ok:
                failures.append((idx, name, "validation failed"))
        except Exception as exc:
            failures.append((idx, name, str(exc)))
            print(f"{idx:>3} {name:<26} | ERROR: {exc}")

    if args.strict and failures:
        print("\nFailures:")
        for idx, name, reason in failures:
            print(f"- {idx}: {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""Strict-capable demo for the atomic subdivision testfield."""

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
    parser.add_argument("--precision", type=float, default=0.001)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--max-failure-details", type=int, default=3)
    return parser.parse_args(argv)


def _failure_detail(report, max_items):
    detail = []
    if report.gap_area > report.tolerance:
        detail.append(
            f"gap={report.gap_area:.9f} "
            f"parts={report.gap_part_count} largest={report.largest_gap_area:.9f}"
        )
    if report.overlap_area > report.tolerance:
        pairs = ", ".join(
            f"{d.zone_a}-{d.zone_b}:{d.area:.9f}"
            for d in report.overlap_details[:max_items]
        )
        suffix = f" pairs=[{pairs}]" if pairs else ""
        detail.append(f"overlap={report.overlap_area:.9f}{suffix}")
    if report.outside_area > report.tolerance:
        detail.append(
            f"outside={report.outside_area:.9f} "
            f"parts={report.outside_part_count} largest={report.largest_outside_area:.9f}"
        )
    if report.invalid_details:
        reasons = ", ".join(
            f"{d.zone_id}:{d.reason}" for d in report.invalid_details[:max_items]
        )
        detail.append(f"invalid=[{reasons}]")
    if report.empty_count:
        detail.append(f"empty={report.empty_count}")
    if report.multipart_count:
        detail.append(f"multipart={report.multipart_count}")
    return "; ".join(detail) if detail else "ok"


def main(argv=None):
    args = parse_args(argv or [])
    all_cases = cases.make_cases()
    selected = (
        [(i, all_cases[i - 1]) for i in args.case_indices if 1 <= i <= len(all_cases)]
        if args.case_indices
        else list(enumerate(all_cases, start=1))
    )

    failures = []
    print(
        f"{'#':>3} {'Case':<26} | "
        "zones parts faces gap_area gap_n overlap pair_n outside invalid empty multi status"
    )
    print("=" * 116)
    for idx, (name, footprint) in selected:
        try:
            result = zone_footprint(
                footprint,
                precision=args.precision,
                tolerance=args.tolerance,
            )
            report = result.validation
            print(
                f"{idx:>3} {name:<26} | "
                f"{report.zone_count:>5} {report.part_count:>5} "
                f"{len(result.subdivision.faces):>5} "
                f"{report.gap_area:.9f} {report.gap_part_count:>5} "
                f"{report.overlap_area:.9f} {len(report.overlap_details):>6} "
                f"{report.outside_area:.9f} {report.invalid_count:>7} "
                f"{report.empty_count:>5} {report.multipart_count:>5} "
                f"{report.short_status()}"
            )
            if not report.ok:
                failures.append(
                    (
                        idx,
                        name,
                        report.short_status(),
                        _failure_detail(report, args.max_failure_details),
                    )
                )
        except Exception as exc:
            failures.append((idx, name, "exception", str(exc)))
            print(f"{idx:>3} {name:<26} | ERROR: {exc}")

    if args.strict and failures:
        print("\nFailures:")
        for idx, name, status, detail in failures:
            print(f"- {idx}: {name}: {status}; {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

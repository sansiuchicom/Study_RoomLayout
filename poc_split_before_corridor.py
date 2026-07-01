"""PoC (throwaway) — split-before-corridor 가능성 측정.

질문: growth 다음에 *큰 방을 region 2분할*하고 corridor를 돌리면 —
  ① corridor가 두 조각 *다*에 복도를 뻗나? (access 오프로드 성립?)
  ② 면적 보존? ③ 조각이 emptied/disconnected 안 나나?

GO/NO-GO: 위 3개 + golden 흔들림 납득가능. NO-GO면 honest 기록 후 폐기.

run() 안 쓰고 floor별 파이프라인을 *corridor까지* 복제 (라벨링은 split 조각의
spec이 없어 skip). 33 golden 케이스에 적용.

실행: source activate IfcOpenHouse && python poc_split_before_corridor.py
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from room_layout.schema import ProgramRequest, ShapeInput, from_dict
from room_layout.stages.anchors import subtract_anchors
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.polygonize import build_region_polygons
from room_layout.stages.program_adapter import program_to_fixture
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.room_growth import GrownRoom

GOLDEN = Path("/workspace/Study_RoomLayout/tests/golden")
OUT = Path("/workspace/ResearchBIM_synthetic-bim/_viz_output")
SPLIT_MIN_AREA = 18.0  # 이 면적 넘는 비-hub 방을 split 후보로


def _region_adjacency(region_poly: dict[int, Polygon]) -> dict[int, set[int]]:
    """region rid → 인접 rid 집합 (경계 공유 길이 > 0)."""
    ids = list(region_poly)
    adj: dict[int, set[int]] = {r: set() for r in ids}
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            ra, rb = ids[a], ids[b]
            inter = region_poly[ra].boundary.intersection(region_poly[rb].boundary)
            if not inter.is_empty and inter.length > 1e-6:
                adj[ra].add(rb)
                adj[rb].add(ra)
    return adj


def _bfs_half(rids, region_poly):
    """rids 를 면적 ~반반 *둘 다 연결* 2그룹으로 — **2-source 성장**.

    양 끝(longer-axis 최소·최대) seed 2개에서 동시에 키움. 매 스텝 *작은 쪽*에
    인접 region 1개 흡수 → 각 그룹이 seed 로부터 BFS 트리라 *둘 다 연결 보장*
    (sweep 의 orphan + 단일-seed BFS 의 B 끊김, 둘 다 해결). 미청구 섬은 A 로.
    """
    sub = {r: region_poly[r] for r in rids}
    adj = _region_adjacency(sub)  # 방 *내부* 인접만
    areas = {r: region_poly[r].area for r in rids}
    minx, miny, maxx, maxy = unary_union(list(sub.values())).bounds
    axis_x = (maxx - minx) >= (maxy - miny)

    def key(r):
        return region_poly[r].centroid.x if axis_x else region_poly[r].centroid.y

    rset = set(rids)
    ordered = sorted(rids, key=key)
    seedA, seedB = ordered[0], ordered[-1]
    A, B = {seedA}, {seedB}
    aA, aB = areas[seedA], areas[seedB]
    claimed = {seedA, seedB}
    while len(claimed) < len(rset):
        grow_A = aA <= aB  # 작은 쪽부터 → 균형
        grp = A if grow_A else B
        frontier = [n for r in grp for n in adj.get(r, set()) if n in rset and n not in claimed]
        if not frontier:  # 막히면 반대 그룹 성장
            grow_A = not grow_A
            grp = A if grow_A else B
            frontier = [n for r in grp for n in adj.get(r, set()) if n in rset and n not in claimed]
            if not frontier:
                break
        nxt = (min if grow_A else max)(frontier, key=key)
        grp.add(nxt)
        claimed.add(nxt)
        if grow_A:
            aA += areas[nxt]
        else:
            aB += areas[nxt]
    A |= rset - claimed  # 미청구(분리 섬) fallback
    return sorted(A), sorted(B)


def split_biggest(growth, region_poly):
    """제일 큰 비-hub 방(≥SPLIT_MIN_AREA, region≥2) → region 2분할 (BFS 연결).

    반환 (growth2, info) 또는 (None, reason).
    """
    hub = growth.fixture.hub_room_index
    cands = [
        (i, r)
        for i, r in enumerate(growth.rooms)
        if i != hub and r.area_m2 >= SPLIT_MIN_AREA and len(r.region_ids) >= 2
    ]
    if not cands:
        return None, "no candidate"
    i, room = max(cands, key=lambda t: t[1].area_m2)
    rids = [rid for rid in room.region_ids if rid in region_poly]
    if len(rids) < 2:
        return None, "single region"

    groupA, groupB = _bfs_half(rids, region_poly)
    if not groupA or not groupB:
        return None, "degenerate"

    aU = unary_union([region_poly[r] for r in groupA])
    bU = unary_union([region_poly[r] for r in groupB])
    new_rooms = list(growth.rooms)
    new_rooms[i] = GrownRoom(room.name, room.role, tuple(sorted(groupA)), aU.area)
    new_rooms.append(GrownRoom(room.name + "__B", room.role, tuple(sorted(groupB)), bU.area))
    growth2 = dataclasses.replace(growth, rooms=tuple(new_rooms))
    info = {
        "room": room.name,
        "role": room.role,
        "idxA": i,
        "idxB": len(new_rooms) - 1,
        "areaA": aU.area,
        "areaB": bU.area,
        "connA": isinstance(aU, Polygon),
        "connB": isinstance(bU, Polygon),
    }
    return growth2, info


def run_floor(shape, program, floor, *, do_split):
    holed = subtract_anchors(floor, shape.vertical_anchors)
    atoms = atomize(holed)
    regions = regionize(holed, atoms=atoms)
    rg = build_region_graph(holed, atoms=atoms, regions=regions)
    fixture = program_to_fixture(holed, program)
    growth = region_partition_growth(holed, fixture, regions=regions, region_graph=rg)
    region_poly = build_region_polygons(regions)
    info = None
    if do_split:
        g2, sinfo = split_biggest(growth, region_poly)
        if g2 is not None:
            growth = g2
            info = sinfo  # split 성공 시에만 dict; 실패면 None 유지
    carved = carve_corridors(holed, growth, regions=regions, region_graph=rg)
    return holed, region_poly, growth, carved, info


def access_ok(carved, region_poly, idx) -> bool:
    """carved.rooms[idx] 가 corridor∪hub 에 인접하나 (post-carve access)."""
    room = carved.rooms[idx]
    if not room.region_ids:
        return False  # emptied
    adj = _region_adjacency(region_poly)
    hub = carved.fixture.hub_room_index
    circ = set(carved.base_corridor_region_ids) | set(carved.shortcut_corridor_region_ids)
    if hub is not None:
        circ |= set(carved.rooms[hub].region_ids)
    return any(adj.get(rid, set()) & circ for rid in room.region_ids)


def _draw(ax, region_poly, rooms, corridor_ids, title, hi=()):
    palette = [
        "#A4C2F4",
        "#FFD27F",
        "#B6D7A8",
        "#F4A4A4",
        "#D5A6BD",
        "#FFE8B8",
        "#C9DAF8",
        "#CFE2F3",
        "#E6B8D9",
        "#D0E0B0",
    ]
    bnds = []
    for k, room in enumerate(rooms):
        polys = [region_poly[r] for r in room.region_ids if r in region_poly]
        if not polys:
            continue
        u = unary_union(polys)
        bnds.append(u.bounds)
        is_hi = k in hi
        for g in u.geoms if isinstance(u, MultiPolygon) else [u]:
            xs, ys = g.exterior.xy
            ax.add_patch(
                MplPoly(
                    list(zip(xs, ys)),
                    facecolor=palette[k % len(palette)],
                    edgecolor="#C00" if is_hi else "#555",
                    lw=2.5 if is_hi else 0.5,
                )
            )
        ax.text(
            u.centroid.x,
            u.centroid.y,
            f"{room.name[:6]}\n{u.area:.0f}",
            ha="center",
            va="center",
            fontsize=5,
            color="#900" if is_hi else "black",
        )
    for rid in corridor_ids:
        if rid in region_poly:
            xs, ys = region_poly[rid].exterior.xy
            ax.add_patch(MplPoly(list(zip(xs, ys)), facecolor="#EEE", edgecolor="#AAA", lw=0.3))
    if bnds:
        m = 0.5
        ax.set_xlim(min(b[0] for b in bnds) - m, max(b[2] for b in bnds) + m)
        ax.set_ylim(min(b[1] for b in bnds) - m, max(b[3] for b in bnds) + m)
    ax.set_title(title, fontsize=7)
    ax.set_aspect("equal")
    ax.axis("off")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cases = sorted(p for p in GOLDEN.iterdir() if p.is_dir())
    rows = []
    renders = []
    print(f"\n{'=' * 70}\nPoC split-before-corridor — {len(cases)} golden\n{'=' * 70}")
    for cd in cases:
        try:
            data = json.loads((cd / "input.json").read_text(encoding="utf-8"))
            shape = from_dict(ShapeInput, data["shape"])
            program = from_dict(ProgramRequest, data["program"])
        except Exception:  # noqa: BLE001
            continue
        for floor in shape.floors:
            try:
                _, rpoly_b, _, carved_b, _ = run_floor(shape, program, floor, do_split=False)
                _, rpoly_s, growth_s, carved_s, info = run_floor(
                    shape, program, floor, do_split=True
                )
            except Exception as e:  # noqa: BLE001
                rows.append((cd.name, floor.level, f"PIPE-FAIL {type(e).__name__}"))
                continue
            if info is None:
                continue  # split 후보 없음 (작은 floor)
            okA = access_ok(carved_s, rpoly_s, info["idxA"])
            okB = access_ok(carved_s, rpoly_s, info["idxB"])
            disc = carved_s.diagnostics.get("disconnected_rooms", ())
            empt = carved_s.diagnostics.get("emptied_rooms", ())
            flag = (
                "OK"
                if (
                    okA
                    and okB
                    and info["connA"]
                    and info["connB"]
                    and info["idxB"] not in empt
                    and info["idxA"] not in disc
                    and info["idxB"] not in disc
                )
                else "FAIL"
            )
            hub = carved_s.fixture.hub_room_index
            n_pub = sum(1 for r in carved_s.rooms if r.role == "public")
            rows.append(
                (
                    cd.name,
                    floor.level,
                    f"{flag} hub={hub} pub={n_pub} split={info['room'][:5]}({info['role'][:3]}) "
                    f"A={info['areaA']:.0f}/{okA} B={info['areaB']:.0f}/{okB} "
                    f"conn={info['connA']}/{info['connB']} disc={list(disc)} empt={list(empt)}",
                )
            )
            renders.append((flag, cd.name, floor.level, rpoly_b, carved_b, rpoly_s, carved_s, info))

    # 콘솔
    n_split = sum(1 for r in rows if "split=" in r[2])
    n_ok = sum(1 for r in rows if r[2].startswith("OK"))
    for name, lv, note in rows:
        print(f"  {name:26s} L{lv} {note}")
    print(f"\n  split 시도 {n_split} / 둘 다 access+conn OK {n_ok} / FAIL {n_split - n_ok}")

    # 렌더 (split 케이스 before|after)
    show = [r for r in renders if r[0] == "OK"][:4] + [r for r in renders if r[0] == "FAIL"]
    if show:
        fig, axes = plt.subplots(len(show), 2, figsize=(8, 3.4 * len(show)), squeeze=False)
        for i, (flag, name, lv, rpb, cb, rps, cs, info) in enumerate(show):
            corr_b = list(cb.base_corridor_region_ids) + list(cb.shortcut_corridor_region_ids)
            corr_s = list(cs.base_corridor_region_ids) + list(cs.shortcut_corridor_region_ids)
            _draw(axes[i][0], rpb, cb.rooms, corr_b, f"{name} L{lv} BEFORE")
            _draw(
                axes[i][1],
                rps,
                cs.rooms,
                corr_s,
                f"[{flag}] AFTER split {info['room'][:5]} A/B(red)",
                hi=(info["idxA"], info["idxB"]),
            )
        fig.suptitle("PoC split-before-corridor — split pieces red; grey=corridor", fontsize=11)
        fig.tight_layout()
        out = OUT / "poc_split.png"
        fig.savefig(out, dpi=115, bbox_inches="tight")
        plt.close(fig)
        print(f"\nsaved {out}")


if __name__ == "__main__":
    main()

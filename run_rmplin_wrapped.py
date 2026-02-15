#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


# ----------------------------
# Paths (edit only if needed)
# ----------------------------
ROOT = Path.home() / "Documents/Tearing/MARS-Q"
EQUI_DIR = ROOT / "EXAMPLE/Equi"
RMP_DIR = ROOT / "EXAMPLE/RmpLin"
DATA_DIR = ROOT / "EXAMPLE/Data"
OUT_DIR = ROOT / "EXAMPLE/RmpLin_auto_results"

# Scripts you already have
CHEASE_PEST = EQUI_DIR / "Rchease_EXAMPLE_base_PEST"
CHEASE_GEOM = EQUI_DIR / "Rchease_EXAMPLE_base_GEOM"
MARS_TEMP   = RMP_DIR / "Rmars_EXAMPLE_RmpLin_temp"
MARS_VAC    = RMP_DIR / "Rmars_EXAMPLE_RmpLin_vac"
MARS_PLS    = RMP_DIR / "Rmars_EXAMPLE_RmpLin_pls"

# Where we expect logs
LOG_VAC = RMP_DIR / "log_mars_vac"
LOG_PLS = RMP_DIR / "log_mars_pls"

# Where we save mapping files (matches memo convention)
PANGLE_PEST = DATA_DIR / "PANGLE_EXAMPLE_PEST"
PANGLE_GEOM = DATA_DIR / "PANGLE_EXAMPLE_GEOM"


# ----------------------------
# Parsing
# ----------------------------
TPSIM_RE = re.compile(
    r"OUTPUT\s+TPSIM:\s+([+-]?\d+\.\d+E[+-]\d+)\s+([+-]?\d+\.\d+E[+-]\d+)\s+([+-]?\d+\.\d+E[+-]\d+)\s+([+-]?\d+\.\d+E[+-]\d+)",
    re.IGNORECASE
)

# Example:
# COMPUTE TOTAL JXB TORQUE:-0.115673E-06  -0.559199E+01
TORQUE_RE = re.compile(
    r"COMPUTE\s+TOTAL\s+(JXB|NTV|REYNOLDS)\s+TORQUE:\s*([+-]?\d+\.\d+E[+-]\d+)\s+([+-]?\d+\.\d+E[+-]\d+)",
    re.IGNORECASE
)


@dataclass
class TPSimRow:
    case: str              # "vac" or "pls"
    m: float
    s_res: float
    re_b1res: float
    im_b1res: float
    source_log: str


@dataclass
class TorqueRow:
    kind: str              # JXB / NTV / REYNOLDS
    val1: float            # first number printed (often tiny)
    val2: float            # second number printed (Nm-ish in memo)
    source_log: str


# ----------------------------
# Helpers
# ----------------------------
def run_cmd(cmd: List[str], cwd: Path, log_file: Optional[Path] = None) -> None:
    """Run a command, stream output, optionally save output to a log file."""
    print(f"\n>> {' '.join(cmd)}  (cwd={cwd})")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    lines: List[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        lines.append(line)
    rc = proc.wait()
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("".join(lines))
    if rc != 0:
        raise RuntimeError(f"Command failed (rc={rc}): {' '.join(cmd)}")


def must_exist(p: Path, hint: str) -> None:
    if not p.exists():
        raise FileNotFoundError(f"{hint}: {p}")


def copy_if_exists(src: Path, dst: Path) -> None:
    must_exist(src, "Expected file missing")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def parse_tpsim(log_path: Path, case: str) -> List[TPSimRow]:
    must_exist(log_path, "Missing log file for TPSIM parsing")
    rows: List[TPSimRow] = []
    for line in log_path.read_text().splitlines():
        m = TPSIM_RE.search(line)
        if not m:
            continue
        rows.append(
            TPSimRow(
                case=case,
                m=float(m.group(1)),
                s_res=float(m.group(2)),
                re_b1res=float(m.group(3)),
                im_b1res=float(m.group(4)),
                source_log=log_path.name
            )
        )
    return rows

def copy_pangle_auto(tag: str, dst: Path) -> None:
    # common names seen in different MARS distributions
    candidates = [
        RMP_DIR / "PANGLE.OUT",
        RMP_DIR / "PANGLE_PEST.IN",
        RMP_DIR / "PANGLE_EQAC.IN",
        RMP_DIR / "PANGLE_GEOM.IN",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        raise FileNotFoundError(f"No PANGLE file found after temp run ({tag}). Looked for: " +
                                ", ".join(str(p.name) for p in candidates))
    # choose the most recently modified
    src = max(existing, key=lambda p: p.stat().st_mtime)
    shutil.copy2(src, dst)
    print(f"Saved {src.name} -> {dst}")

def parse_torque(log_path: Path) -> List[TorqueRow]:
    must_exist(log_path, "Missing log file for TORQUE parsing")
    rows: List[TorqueRow] = []
    for line in log_path.read_text().splitlines():
        m = TORQUE_RE.search(line)
        if not m:
            continue
        rows.append(
            TorqueRow(
                kind=m.group(1).upper(),
                val1=float(m.group(2)),
                val2=float(m.group(3)),
                source_log=log_path.name
            )
        )
    return rows


def write_csv(path: Path, header: List[str], rows: List[List[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ----------------------------
# Workflow
# ----------------------------
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Sanity
    for p in [CHEASE_PEST, CHEASE_GEOM, MARS_TEMP, MARS_VAC, MARS_PLS]:
        must_exist(p, "Missing required script")

    # 1) CHEASE PEST -> temp -> save PANGLE_EXAMPLE_PEST
    run_cmd(["bash", CHEASE_PEST.name], cwd=EQUI_DIR)
    # temp script expects OUT*MAR in ../Equi; it will copy internally
    run_cmd(["bash", MARS_TEMP.name], cwd=RMP_DIR)
    copy_pangle_auto("PEST", PANGLE_PEST)
    #copy_if_exists(RMP_DIR / "PANGLE.OUT", PANGLE_PEST)

    # 2) CHEASE GEOM -> temp -> save PANGLE_EXAMPLE_GEOM
    run_cmd(["bash", CHEASE_GEOM.name], cwd=EQUI_DIR)
    run_cmd(["bash", MARS_TEMP.name], cwd=RMP_DIR)
    copy_pangle_auto("GEOM", PANGLE_GEOM)
    #copy_if_exists(RMP_DIR / "PANGLE.OUT", PANGLE_GEOM)

    print("\nOK: mapping files updated:")
    print(f" - {PANGLE_PEST}")
    print(f" - {PANGLE_GEOM}")

    # 3) Vacuum RMP
    run_cmd(["bash", MARS_VAC.name], cwd=RMP_DIR)

    # 4) Plasma response
    run_cmd(["bash", MARS_PLS.name], cwd=RMP_DIR)

    # 5) Parse outputs
    tps_vac = parse_tpsim(LOG_VAC, "vac")
    tps_pls = parse_tpsim(LOG_PLS, "pls")
    torq = parse_torque(LOG_PLS)

    # Write CSVs
    tps_csv = OUT_DIR / "tpsim_vac_pls.csv"
    torq_csv = OUT_DIR / "torques_pls.csv"

    write_csv(
        tps_csv,
        ["case", "m", "s_res", "re_b1res", "im_b1res", "source_log"],
        [[r.case, r.m, r.s_res, r.re_b1res, r.im_b1res, r.source_log] for r in (tps_vac + tps_pls)]
    )

    write_csv(
        torq_csv,
        ["kind", "val1", "val2", "source_log"],
        [[r.kind, r.val1, r.val2, r.source_log] for r in torq]
    )

    # Summary (matches what you showed)
    print("\n=== TPSIM (vac) ===")
    for r in tps_vac:
        print(f"m={r.m:4.0f}  s={r.s_res:.6f}  Re={r.re_b1res:.6e}  Im={r.im_b1res:.6e}")

    print("\n=== TPSIM (pls) ===")
    for r in tps_pls:
        print(f"m={r.m:4.0f}  s={r.s_res:.6f}  Re={r.re_b1res:.6e}  Im={r.im_b1res:.6e}")

    print("\n=== TORQUES (pls) ===")
    for r in torq:
        print(f"{r.kind:8s}  {r.val1:.6e}  {r.val2:.6e}")

    print("\nSaved:")
    print(f" - {tps_csv}")
    print(f" - {torq_csv}")
    print(f" - {PANGLE_PEST}")
    print(f" - {PANGLE_GEOM}")
    print(f"\nRun directory: {RMP_DIR}")
    print("Done.")


if __name__ == "__main__":
    main()

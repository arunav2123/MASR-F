#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path.home() / "Documents/Tearing/MARS-Q"
CHEASE = ROOT / "CheaseMerge/chease.x"
MARS = ROOT / "MarsQ_2FK/marsq.x"

DATA_DIR = ROOT / "EXAMPLE/Data"
EQUI_DIR = ROOT / "EXAMPLE/Equi"
WORK_DIR = ROOT / "EXAMPLE/RmpLin_auto"   # created if missing

EXPEQ_SRC = DATA_DIR / "EXPEQ_EXAMPLE"
PROFDEN_SRC = DATA_DIR / "PROFDEN_EXAMPLE.IN"

PANGLE_PEST = DATA_DIR / "PANGLE_EXAMPLE_PEST"
PANGLE_GEOM = DATA_DIR / "PANGLE_EXAMPLE_GEOM"

def run(cmd, cwd=None, log_path=None):
    print(f"\n>> {cmd} (cwd={cwd})")
    with subprocess.Popen(
        cmd, cwd=cwd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    ) as p:
        out_lines = []
        for line in p.stdout:
            print(line, end="")
            out_lines.append(line)
        rc = p.wait()
    if log_path is not None:
        Path(log_path).write_text("".join(out_lines))
    if rc != 0:
        raise RuntimeError(f"Command failed (rc={rc}): {cmd}")
    return "".join(out_lines)

def write_chease_datain(path: Path, negp: int, ner: int):
    # This matches your example base datain, changing only NEGP/NER.
    txt = f"""*** Example Torus
 &EQDATA
   NEQDSK=0, NSURF=6, NTCASE=0,
   NBLOPT=0, NBSOPT=0, CPRESS=1.000, CFBAL=1.0000,
   NCSCAL = 2, CSSPEC=0.000, QSPEC =1.6185,
   NTMF0=0,CURRT = 0.3000,
   NSTTP=2, NFUNC = 4, NIPR=1, NISO=100,
   NPPFUN=4, NPP=1, NPPR=30,
   NSOUR=2, NPROPT = 2,
   NS=60, NT=60, NPSI=240, NCHI= 200,
   NV=160, REXT=6.0, NVEXP=8, R0W=0.90, RZ0W=0.0,
   NMESHA=3, SOLPDA=0.60, QWIDTH0=0.40, ROTE=0.0000, NTOR=1,
   NPOIDQ=5, QSHAVE=100.0,
   QPLACE(1)= 2.0000, 3.0000, 4.0000, 5.0000, 6.0000, 7.0000, 8.0000,
   QWIDTH(1)= 0.0100, 0.0080, 0.0060, 0.0040, 0.0020, 0.0010, 0.0010,
   NEGP={negp},  NER={ner},
   EPSLON=1.0E-10, GAMMA=1.6666666667,
   MSMAX=40, NINMAP=50, NINSCA=50,
   NOPT = 0, NPLOT=1, NBAL=0,
   B0EXP=1.5, R0EXP=3.0,
 &END
"""
    path.write_text(txt)

def write_run_in(path: Path, *, incfeed: int, ncase: int = 2, nconvb1: int = 0, nconvcs: int = 0,
                 nv: int = 160, rntor: float = -1.0, talpha1="(0.0,0.0)", include_coils: bool = False):
    # IMPORTANT: use "/" namelist terminators and include &QLIN to avoid EOF issues.
    # Coils: placeholder; replace with the coil geometry from the example scripts if you have them.
    feedback_block = f"""&FEEDBACK
  INCFEED= {incfeed},
"""
    if include_coils:
        feedback_block += """  NCOIL  = 2,
  FCCHI  = 0.34219, -0.405470,
  FWCHI  = 0.12187,  0.089063,
  BTCHI  = 0.05,
  FEEDI  = (0.0,-1.2046e-3),(0.0,-1.3217e-3),
  IFEED  = 3,
  KKF    = -1,
"""
    feedback_block += "/\n"

    txt = f"""&BASIC
  NCASE  = {ncase},
  RNTOR  = {rntor},
  NV     = {nv},
  NWALL  = 0,
  ETA    = 0.0,
  TALPHA1= {talpha1},
  M1     = -9,
  M2     = 33,
  NPROFN = 4,
/
{feedback_block}
&KINETIC
  INCKIN = 0,
/
&QLIN
  KSOLSAVE = 0,
  KSOLREAD = 0,
/
&NUMERIC
  NCONVB1 = {nconvb1},
  NCONVCS = {nconvcs},
  IOMPNUM = 1,
/
&OUTOPT
  OUTDAT = .F.,
/
"""
    path.write_text(txt)

def extract_pangle(work: Path, save_to: Path):
    p = work / "PANGLE.OUT"
    if not p.exists():
        # Some builds may name it differently; add more fallbacks if needed.
        raise FileNotFoundError("PANGLE.OUT not produced; check log_mars for 'PANGLE'.")
    shutil.copy2(p, save_to)
    print(f"Saved {p.name} -> {save_to}")

def ensure_inputs():
    for f in [CHEASE, MARS, EXPEQ_SRC, PROFDEN_SRC]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required file: {f}")
    WORK_DIR.mkdir(parents=True, exist_ok=True)


def chease_run_via_script(script_name: str):
    """
    Run an existing CHEASE wrapper script in EXAMPLE/Equi that we know works.
    It should create OUTRMAR/OUTVMAR in-place.
    """
    if not (EQUI_DIR / script_name).exists():
        raise FileNotFoundError(f"Missing CHEASE script: {EQUI_DIR/script_name}")

    run(f"bash {script_name}", cwd=EQUI_DIR, log_path=WORK_DIR / f"log_{script_name}.txt")

    for name in ["OUTRMAR", "OUTVMAR"]:
        if not (EQUI_DIR / name).exists():
            raise FileNotFoundError(f"{name} not produced by {script_name} in {EQUI_DIR}")

    print(f"{script_name}: OK (OUTRMAR/OUTVMAR present in {EQUI_DIR})")


def chease_run(tag: str, negp: int, ner: int):
    run_dir = WORK_DIR / f"chease_{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXPEQ_SRC, run_dir / "EXPEQ")
    write_chease_datain(run_dir / "datain", negp=negp, ner=ner)
    # clean old
    for f in run_dir.glob("OUT*MAR"):
        f.unlink()
    out = run(f"{CHEASE} < datain", cwd=run_dir, log_path=run_dir / "log_chease")
    # copy equilibrium outputs to EQUI_DIR as "current"
    for name in ["OUTRMAR", "OUTVMAR"]:
        src = run_dir / name
        if not src.exists():
            raise FileNotFoundError(f"CHEASE did not produce {name} in {run_dir}")
        shutil.copy2(src, EQUI_DIR / name)
    print(f"CHEASE {tag}: wrote OUTRMAR/OUTVMAR -> {EQUI_DIR}")
    return out

def mars_temp_make_pangle(tag: str, nconvcs: int, save_to: Path):
    run_dir = WORK_DIR / f"mars_temp_{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # stage inputs
    shutil.copy2(EQUI_DIR / "OUTRMAR", run_dir / "OUTRMAR")
    shutil.copy2(EQUI_DIR / "OUTVMAR", run_dir / "OUTVMAR")
    shutil.copy2(PROFDEN_SRC, run_dir / "PROFDEN.IN")

    write_run_in(run_dir / "RUN.IN", incfeed=0, ncase=2, nconvb1=1, nconvcs=nconvcs, talpha1="(0.0,0.0)")
    # clean
    for f in run_dir.glob("*.OUT"):
        f.unlink()
    (run_dir / "log_mars").unlink(missing_ok=True)

    run(f"{MARS} > log_mars", cwd=run_dir)
    extract_pangle(run_dir, save_to)


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


def mars_rmp(tag: str, incfeed: int):
    run_dir = WORK_DIR / f"mars_rmp_{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # stage GEOM equilibrium (recommended)
    shutil.copy2(EQUI_DIR / "OUTRMAR", run_dir / "OUTRMAR")
    shutil.copy2(EQUI_DIR / "OUTVMAR", run_dir / "OUTVMAR")
    shutil.copy2(PROFDEN_SRC, run_dir / "PROFDEN.IN")

    # stage mapping files (used when NCONVB1=2)
    shutil.copy2(PANGLE_PEST, run_dir / "PANGLE_EXAMPLE_PEST")
    shutil.copy2(PANGLE_GEOM, run_dir / "PANGLE_EXAMPLE_GEOM")

    # Here we assume NCONVB1=2 means: use mapping files to output resonant harmonics in SFL/PEST
    write_run_in(
        run_dir / "RUN.IN",
        incfeed=incfeed,
        ncase=2,
        nconvb1=2,
        nconvcs=1,   # run in GEOM
        talpha1="(0.0,0.0)",  # static RMP
        include_coils=True
    )

    for f in run_dir.glob("*.OUT"):
        f.unlink()
    (run_dir / "log_mars").unlink(missing_ok=True)

    log = run(f"{MARS} > log_mars", cwd=run_dir)
    # quick parse for resonant harmonic output (string depends on build)
    # Use memo hint: search "OUTPUT TPSIM"
    hits = [ln for ln in log.splitlines() if "OUTPUT TPSIM" in ln.upper()]
    (run_dir / "tpsim_lines.txt").write_text("\n".join(hits) + "\n")
    print(f"{tag}: extracted {len(hits)} 'OUTPUT TPSIM' lines -> {run_dir/'tpsim_lines.txt'}")
    return run_dir

def main():
    ensure_inputs()

    # Step 1/2: PEST mapping
    chease_run_via_script("Rchease_EXAMPLE_base_PEST")
    mars_temp_make_pangle("PEST", nconvcs=0, save_to=PANGLE_PEST)

    # Step 3/4: GEOM mapping
    chease_run_via_script("Rchease_EXAMPLE_base_GEOM")
    mars_temp_make_pangle("GEOM", nconvcs=1, save_to=PANGLE_GEOM)

    # Step 5: vacuum + plasma response
    mars_rmp("vac", incfeed=4)
    mars_rmp("pls", incfeed=8)

    print("\nDONE. Outputs in:", WORK_DIR)

if __name__ == "__main__":
    main()

"""
Read-only diagnostic for EQDSK g-file.
Prints key sign-convention quantities CHEASE needs.

Usage: python diagnose_gfile.py g028957.004300
"""
import sys, re, numpy as np

def read_gfile_values(fname):
    with open(fname, 'r') as f:
        text = f.read()

    lines = text.split('\n')

    # --- Header line: extract nw, nh ---
    hdr = lines[0]
    # Last two integers on the header line
    ints = re.findall(r'\d+', hdr)
    nw, nh = int(ints[-2]), int(ints[-1])
    print(f"Header: {hdr.strip()}")
    print(f"Grid:   nw={nw}, nh={nh}")

    # --- Read ALL floating-point values after header ---
    # EQDSK stores everything as space-separated floats after line 1
    body = '\n'.join(lines[1:])
    # Match all floats (including Fortran-style E notation)
    floats = re.findall(r'[+-]?\d+\.\d+[EeDd][+-]?\d+|[+-]?\d+\.\d+', body)
    vals = np.array([float(v.replace('D', 'E').replace('d', 'e')) for v in floats])

    print(f"Total floats parsed: {len(vals)}")
    print(f"Expected minimum: {20 + 4*nw + nw*nh + nw} = {20 + 5*nw + nw*nh}")

    # --- Map to EQDSK fields ---
    # Scalars: 5 lines x 5 values = 20 scalars (indices 0..19)
    # Line 2 (idx 0-4):  rdim, zdim, rcentr, rleft, zmid
    # Line 3 (idx 5-9):  rmaxis, zmaxis, simag, sibry, bcentr
    # Line 4 (idx 10-14): cpasma, simag_dup, xdum, rmaxis_dup, xdum
    # Line 5 (idx 15-19): zmaxis_dup, xdum, sibry_dup, xdum, xdum

    rdim    = vals[0]
    zdim    = vals[1]
    rcentr  = vals[2]
    rleft   = vals[3]
    zmid    = vals[4]
    rmaxis  = vals[5]
    zmaxis  = vals[6]
    simag   = vals[7]
    sibry   = vals[8]
    bcentr  = vals[9]
    cpasma  = vals[10]

    print(f"\n{'='*60}")
    print(f"KEY EQDSK SCALARS")
    print(f"{'='*60}")
    print(f"  rdim    = {rdim:+16.9E}   (domain width in R)")
    print(f"  zdim    = {zdim:+16.9E}   (domain height in Z)")
    print(f"  rcentr  = {rcentr:+16.9E}   (R reference for Bt)")
    print(f"  rleft   = {rleft:+16.9E}   (left R of domain)")
    print(f"  zmid    = {zmid:+16.9E}   (Z midpoint of domain)")
    print(f"  rmaxis  = {rmaxis:+16.9E}   (R of magnetic axis)")
    print(f"  zmaxis  = {zmaxis:+16.9E}   (Z of magnetic axis)")
    print(f"  simag   = {simag:+16.9E}   (psi at axis)       *** KEY ***")
    print(f"  sibry   = {sibry:+16.9E}   (psi at boundary)   *** KEY ***")
    print(f"  bcentr  = {bcentr:+16.9E}   (Bt at rcentr)")
    print(f"  cpasma  = {cpasma:+16.9E}   (plasma current Ip)")

    # 1D profiles (each nw long), starting at index 20
    i0 = 20
    fpol    = vals[i0:i0+nw];           i0 += nw
    pres    = vals[i0:i0+nw];           i0 += nw
    ffprime = vals[i0:i0+nw];           i0 += nw
    pprime  = vals[i0:i0+nw];           i0 += nw

    # 2D psirz
    psirz = vals[i0:i0+nw*nh].reshape((nh, nw)); i0 += nw*nh

    # q profile
    qpsi = vals[i0:i0+nw]; i0 += nw

    print(f"\n{'='*60}")
    print(f"PROFILE SIGNS AND RANGES")
    print(f"{'='*60}")
    print(f"  fpol    : [{fpol.min():+12.5E}, {fpol.max():+12.5E}]  (sign={'+' if fpol[0]>0 else '-'})")
    print(f"  pres    : [{pres.min():+12.5E}, {pres.max():+12.5E}]")
    print(f"  ffprime : [{ffprime.min():+12.5E}, {ffprime.max():+12.5E}]  *** KEY ***")
    print(f"  pprime  : [{pprime.min():+12.5E}, {pprime.max():+12.5E}]  *** KEY ***")
    print(f"  psirz   : [{psirz.min():+12.5E}, {psirz.max():+12.5E}]  *** KEY ***")
    print(f"  qpsi    : [{qpsi.min():+12.5E}, {qpsi.max():+12.5E}]")

    print(f"\n{'='*60}")
    print(f"CHEASE COMPATIBILITY CHECK")
    print(f"{'='*60}")

    ok = True

    # Check 1: psimag < 0
    if simag >= 0:
        print(f"  FAIL: psimag = {simag:+.6E} >= 0  (CHEASE requires psimag < 0)")
        ok = False
    else:
        print(f"  OK:   psimag = {simag:+.6E} < 0")

    # Check 2: psibdry > psimag
    if sibry <= simag:
        print(f"  FAIL: psibdry = {sibry:+.6E} <= psimag = {simag:+.6E}")
        ok = False
    else:
        print(f"  OK:   psibdry = {sibry:+.6E} > psimag = {simag:+.6E}")

    # Check 3: pprime <= 0 (pressure falls as psi increases from axis to edge)
    if pprime.max() > 0 and pprime.max() > 1e-10 * abs(pprime.min()):
        print(f"  WARN: pprime has positive values (max={pprime.max():+.4E})")
        print(f"         CHEASE expects dp/dpsi < 0 with psi increasing from axis to edge")
    else:
        print(f"  OK:   pprime <= 0")

    # Check 4: psirz at axis location
    # Map rmaxis, zmaxis to grid indices
    ir_axis = int(round((rmaxis - rleft) / rdim * (nw - 1)))
    iz_axis = int(round((zmaxis - (zmid - zdim/2)) / zdim * (nh - 1)))
    ir_axis = max(0, min(nw-1, ir_axis))
    iz_axis = max(0, min(nh-1, iz_axis))
    psi_at_axis = psirz[iz_axis, ir_axis]
    print(f"\n  psirz at grid point nearest axis (ir={ir_axis},iz={iz_axis}): {psi_at_axis:+.6E}")

    if not ok:
        print(f"\n  >>> FIX NEEDED: flip psi, pprime, ffprime (and cplasma) <<<")
        print(f"  >>> Run: python fix_gfile_inplace.py {fname} <<<")
    else:
        print(f"\n  All checks passed — g-file should be CHEASE-compatible.")

    return {
        'simag': simag, 'sibry': sibry, 'bcentr': bcentr,
        'cpasma': cpasma, 'pprime': pprime, 'ffprime': ffprime,
        'psirz': psirz, 'fpol': fpol, 'qpsi': qpsi, 'nw': nw, 'nh': nh
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_gfile.py <geqdsk_file>")
        sys.exit(1)
    read_gfile_values(sys.argv[1])
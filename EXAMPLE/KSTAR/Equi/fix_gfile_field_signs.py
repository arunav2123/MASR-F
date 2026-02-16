"""
Format-preserving field-sign fix for CHEASE compatibility.

CHEASE requires Bt > 0, Ip > 0, F > 0 in the EQDSK.
This script flips ONLY: bcentr, cpasma, fpol
It does NOT flip: psimag, psibdry, psirz, pprime, ffprime (already correct).

Strategy: locate each float token by character position in the raw text,
negate only the targeted tokens, write back in the same field width.

Usage: python fix_gfile_field_signs.py g028957.004300 [output_file]
"""
import sys, re, numpy as np


def negate_token(field_text):
    """
    Negate a Fortran-formatted float string, preserving exact field width.
    E.g. ' -1.234567890E+00' -> '  1.234567890E+00'
         '  1.234567890E+00' -> ' -1.234567890E+00'
    """
    width = len(field_text)
    val = float(field_text.strip().replace('D', 'E').replace('d', 'e'))
    val = -val

    # Determine decimal digits from original
    match = re.search(r'\.(\d+)', field_text)
    ndec = len(match.group(1)) if match else 9

    # Format with same width and decimal places
    new_s = f'{val:+{width}.{ndec}E}'
    # Remove the explicit '+' if the value is positive to save space
    if val >= 0:
        new_s = f'{val:{width}.{ndec}E}'

    # Ensure exact width
    while len(new_s) > width and ndec > 1:
        ndec -= 1
        new_s = f'{val:{width}.{ndec}E}'

    if len(new_s) < width:
        new_s = new_s.rjust(width)
    elif len(new_s) > width:
        new_s = new_s[:width]

    return new_s


def fix_field_signs(infile, outfile=None):
    with open(infile, 'r') as f:
        text = f.read()

    lines = text.split('\n')
    header = lines[0]

    # Parse nw, nh
    ints = re.findall(r'\d+', header)
    nw, nh = int(ints[-2]), int(ints[-1])
    print(f"Grid: nw={nw}, nh={nh}")

    # Find all float tokens with positions
    body = '\n'.join(lines[1:])
    header_offset = len(header) + 1

    pattern = r'[+-]?\d+\.\d+[EeDd][+-]?\d+|[+-]?\d+\.\d+'
    tokens = []
    for m in re.finditer(pattern, body):
        tokens.append({
            'start': header_offset + m.start(),
            'end': header_offset + m.end(),
            'text': m.group(),
            'value': float(m.group().replace('D', 'E').replace('d', 'e'))
        })

    print(f"Found {len(tokens)} float tokens")

    # EQDSK layout (token indices):
    # Scalars [0..19]:
    #   [0-4]:   rdim, zdim, rcentr, rleft, zmid
    #   [5-9]:   rmaxis, zmaxis, simag, sibry, bcentr
    #   [10-14]: cpasma, simag_dup, xdum, rmaxis_dup, xdum
    #   [15-19]: zmaxis_dup, xdum, sibry_dup, xdum, xdum
    # Arrays:
    #   [20 .. 20+nw-1]:                fpol
    #   [20+nw .. 20+2*nw-1]:           pres
    #   [20+2*nw .. 20+3*nw-1]:         ffprime  (NOT flipped)
    #   [20+3*nw .. 20+4*nw-1]:         pprime   (NOT flipped)
    #   [20+4*nw .. 20+4*nw+nw*nh-1]:   psirz    (NOT flipped)

    IDX_BCENTR = 9
    IDX_CPASMA = 10
    IDX_FPOL_START = 20
    IDX_FPOL_END = 20 + nw

    bcentr = tokens[IDX_BCENTR]['value']
    cpasma = tokens[IDX_CPASMA]['value']
    simag = tokens[7]['value']
    sibry = tokens[8]['value']
    fpol_0 = tokens[IDX_FPOL_START]['value']

    print(f"\nBefore fix:")
    print(f"  bcentr = {bcentr:+16.9E}")
    print(f"  cpasma = {cpasma:+16.9E}")
    print(f"  fpol[0]= {fpol_0:+16.9E}")
    print(f"  simag  = {simag:+16.9E}  (NOT changing)")
    print(f"  sibry  = {sibry:+16.9E}  (NOT changing)")

    # Check if fix is needed
    needs_fix = False
    if bcentr < 0:
        print(f"\n  bcentr < 0 → will flip to positive")
        needs_fix = True
    if cpasma < 0:
        print(f"  cpasma < 0 → will flip to positive")
        needs_fix = True

    if not needs_fix:
        print(f"\n  bcentr and cpasma already positive — no field-sign fix needed.")
        print(f"  If CHEASE still fails, the issue is elsewhere.")
        return

    if simag >= 0:
        print(f"\n  WARNING: simag >= 0 — you also need a psi sign fix!")

    # Collect token indices to flip: bcentr, cpasma, fpol array
    flip_indices = set()
    flip_indices.add(IDX_BCENTR)
    flip_indices.add(IDX_CPASMA)
    for i in range(IDX_FPOL_START, IDX_FPOL_END):
        flip_indices.add(i)

    print(f"\n  Flipping {len(flip_indices)} token values "
          f"(1 bcentr + 1 cpasma + {nw} fpol)...")

    # Apply flips in reverse order to preserve positions
    text_chars = list(text)

    for idx in sorted(flip_indices, reverse=True):
        tok = tokens[idx]
        start = tok['start']
        end = tok['end']

        # Extend field to include leading whitespace (part of Fortran field)
        field_start = start
        while field_start > 0 and text_chars[field_start - 1] == ' ':
            # Don't cross newlines
            if field_start > 1 and text_chars[field_start - 2] == '\n':
                break
            # Don't go too far (max 16 chars field width)
            if start - field_start >= 15:
                break
            field_start -= 1

        old_field = ''.join(text_chars[field_start:end])
        new_field = negate_token(old_field)

        # Sanity: must be same length
        assert len(new_field) == len(old_field), \
            f"Field width mismatch at idx {idx}: {len(old_field)} vs {len(new_field)}"

        for ci, c in enumerate(new_field):
            text_chars[field_start + ci] = c

    new_text = ''.join(text_chars)

    # Verify
    body2 = '\n'.join(new_text.split('\n')[1:])
    tokens2 = list(re.finditer(pattern, body2))
    new_bcentr = float(tokens2[IDX_BCENTR].group().replace('D', 'E'))
    new_cpasma = float(tokens2[IDX_CPASMA].group().replace('D', 'E'))
    new_fpol0 = float(tokens2[IDX_FPOL_START].group().replace('D', 'E'))
    new_simag = float(tokens2[7].group().replace('D', 'E'))

    print(f"\nAfter fix:")
    print(f"  bcentr = {new_bcentr:+16.9E}")
    print(f"  cpasma = {new_cpasma:+16.9E}")
    print(f"  fpol[0]= {new_fpol0:+16.9E}")
    print(f"  simag  = {new_simag:+16.9E}  (unchanged)")

    assert new_bcentr > 0, f"bcentr flip failed: {new_bcentr}"
    assert new_cpasma > 0, f"cpasma flip failed: {new_cpasma}"
    assert new_fpol0 > 0, f"fpol flip failed: {new_fpol0}"
    assert new_simag < 0, f"simag was corrupted: {new_simag}"

    if outfile is None:
        base, ext = (infile.rsplit('.', 1) + [''])[:2]
        outfile = f"{base}_fixed.{ext}" if ext else f"{infile}_fixed"

    with open(outfile, 'w') as f:
        f.write(new_text)

    sz_orig = len(text)
    sz_new = len(new_text)
    print(f"\nWritten: {outfile}")
    print(f"File size: {sz_orig} -> {sz_new} (delta={sz_new - sz_orig})")
    if sz_orig != sz_new:
        print(f"  WARNING: size changed — Fortran reader may fail!")
    else:
        print(f"  Size preserved ✓")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_gfile_field_signs.py <geqdsk_file> [output_file]")
        sys.exit(1)
    fix_field_signs(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
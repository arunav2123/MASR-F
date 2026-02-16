"""
Smooth the plasma boundary in an EQDSK g-file to remove the X-point cusp.

The X-point creates a geometric singularity in the boundary (R,Z) that
causes CHEASE's vacuum Green's function matrix to be singular (ZERO PIVOT).

This script Fourier-filters the boundary, keeping only the first N harmonics.
This naturally rounds off the X-point cusp while preserving the overall
shape (elongation, triangularity, etc.).

Usage: python smooth_gfile_boundary.py g028957_fixed.004300 [N_harmonics] [output]
  N_harmonics: number of Fourier modes to keep (default: 8)
               Lower = smoother. 6-10 is typical.
"""
import sys, re
import numpy as np


def read_boundary_from_gfile(fname):
    """Read g-file, return text + parsed boundary info."""
    with open(fname, 'r') as f:
        text = f.read()

    lines = text.split('\n')
    header = lines[0]
    ints = re.findall(r'\d+', header)
    nw, nh = int(ints[-2]), int(ints[-1])

    # Find all float tokens
    body = '\n'.join(lines[1:])
    pattern = r'[+-]?\d+\.\d+[EeDd][+-]?\d+|[+-]?\d+\.\d+'
    tokens = list(re.finditer(pattern, body))
    header_offset = len(header) + 1

    # EQDSK layout:
    # 20 scalars + fpol(nw) + pres(nw) + ffprime(nw) + pprime(nw) + psirz(nw*nh) + qpsi(nw)
    # Then: nbbbs, limitr (as integers in a line)
    # Then: rbbbs,zbbbs pairs (2*nbbbs floats)

    n_before_bdry = 20 + 5*nw + nw*nh  # tokens before nbbbs/limitr line

    # Find the nbbbs/limitr line - it contains two integers
    # Skip past all the float arrays
    float_count = 0
    line_idx = 1  # start after header
    while line_idx < len(lines):
        line = lines[line_idx]
        floats_in_line = re.findall(pattern, line)
        if floats_in_line:
            float_count += len(floats_in_line)
            if float_count >= n_before_bdry:
                # Next non-float line should be nbbbs/limitr
                line_idx += 1
                break
        line_idx += 1

    # Find the integer line (nbbbs, limitr)
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if line and not re.match(pattern, line.split()[0] if line.split() else ''):
            # This should be the integer line
            int_vals = [int(x) for x in line.split()]
            nbbbs = int_vals[0]
            limitr = int_vals[1] if len(int_vals) > 1 else 0
            break
        line_idx += 1

    print(f"Grid: nw={nw}, nh={nh}")
    print(f"Boundary points: nbbbs={nbbbs}, limiter points: limitr={limitr}")

    # Now read boundary floats from remaining tokens
    # Find where boundary tokens start in the full token list
    bdry_token_start = n_before_bdry
    # But the integer line isn't a float token, so boundary starts at n_before_bdry in tokens

    # Actually, let's just count: after n_before_bdry float tokens + the integer line,
    # the next 2*nbbbs floats are the boundary
    # The qpsi array ends at token index (20 + 5*nw + nw*nh - 1)
    # Token n_before_bdry is the FIRST boundary float

    rbbbs = []
    zbbbs = []
    for i in range(nbbbs):
        r_idx = n_before_bdry + 2*i
        z_idx = n_before_bdry + 2*i + 1
        r_val = float(tokens[r_idx].group().replace('D', 'E').replace('d', 'e'))
        z_val = float(tokens[z_idx].group().replace('D', 'E').replace('d', 'e'))
        rbbbs.append(r_val)
        zbbbs.append(z_val)

    rbbbs = np.array(rbbbs)
    zbbbs = np.array(zbbbs)

    # Store token positions for replacement
    bdry_tokens = []
    for i in range(2 * nbbbs):
        tok = tokens[n_before_bdry + i]
        bdry_tokens.append({
            'start': header_offset + tok.start(),
            'end': header_offset + tok.end(),
            'text': tok.group()
        })

    return text, nw, nh, nbbbs, rbbbs, zbbbs, bdry_tokens, header_offset


def fourier_smooth_boundary(rbbbs, zbbbs, n_harmonics=8):
    """
    Smooth boundary by keeping only first N Fourier harmonics.
    Boundary is parameterized by geometric angle theta from centroid.
    """
    n = len(rbbbs)

    # Compute centroid
    r0 = np.mean(rbbbs)
    z0 = np.mean(zbbbs)

    # Parameterize by angle from centroid
    theta = np.arctan2(zbbbs - z0, rbbbs - r0)

    # Sort by angle
    idx = np.argsort(theta)
    theta_s = theta[idx]
    r_s = rbbbs[idx]
    z_s = zbbbs[idx]

    # Uniform theta grid for FFT
    theta_uniform = np.linspace(-np.pi, np.pi, n, endpoint=False)
    r_interp = np.interp(theta_uniform, theta_s, r_s, period=2*np.pi)
    z_interp = np.interp(theta_uniform, theta_s, z_s, period=2*np.pi)

    # FFT
    r_fft = np.fft.fft(r_interp)
    z_fft = np.fft.fft(z_interp)

    # Zero out high harmonics
    r_fft_filtered = np.zeros_like(r_fft)
    z_fft_filtered = np.zeros_like(z_fft)

    # Keep DC + first n_harmonics positive and negative frequencies
    r_fft_filtered[0] = r_fft[0]
    z_fft_filtered[0] = z_fft[0]
    for k in range(1, n_harmonics + 1):
        if k < n:
            r_fft_filtered[k] = r_fft[k]
            z_fft_filtered[k] = z_fft[k]
        if n - k > 0:
            r_fft_filtered[n - k] = r_fft[n - k]
            z_fft_filtered[n - k] = z_fft[n - k]

    # Inverse FFT
    r_smooth = np.real(np.fft.ifft(r_fft_filtered))
    z_smooth = np.real(np.fft.ifft(z_fft_filtered))

    # Map back to original theta ordering
    r_out = np.interp(theta, theta_uniform, r_smooth, period=2*np.pi)
    z_out = np.interp(theta, theta_uniform, z_smooth, period=2*np.pi)

    return r_out, z_out


def format_float_like(value, template):
    """Format a float to match the field width of the template string."""
    width = len(template)
    match = re.search(r'\.(\d+)', template)
    ndec = len(match.group(1)) if match else 9

    new_s = f'{value:{width}.{ndec}E}'
    while len(new_s) > width and ndec > 1:
        ndec -= 1
        new_s = f'{value:{width}.{ndec}E}'

    if len(new_s) < width:
        new_s = new_s.rjust(width)
    elif len(new_s) > width:
        new_s = new_s[:width]

    return new_s


def smooth_gfile(infile, n_harmonics=8, outfile=None):
    text, nw, nh, nbbbs, rbbbs, zbbbs, bdry_tokens, header_offset = \
        read_boundary_from_gfile(infile)

    print(f"\nOriginal boundary:")
    print(f"  R range: [{rbbbs.min():.4f}, {rbbbs.max():.4f}]")
    print(f"  Z range: [{zbbbs.min():.4f}, {zbbbs.max():.4f}]")

    # Detect X-point: find the point with smallest R on the bottom
    z_min_idx = np.argmin(zbbbs)
    print(f"  Likely X-point region: R={rbbbs[z_min_idx]:.4f}, Z={zbbbs[z_min_idx]:.4f}")

    # Smooth
    r_smooth, z_smooth = fourier_smooth_boundary(rbbbs, zbbbs, n_harmonics)

    print(f"\nSmoothed boundary (N_harmonics={n_harmonics}):")
    print(f"  R range: [{r_smooth.min():.4f}, {r_smooth.max():.4f}]")
    print(f"  Z range: [{z_smooth.min():.4f}, {z_smooth.max():.4f}]")

    # Max displacement
    dr = np.abs(r_smooth - rbbbs)
    dz = np.abs(z_smooth - zbbbs)
    disp = np.sqrt(dr**2 + dz**2)
    print(f"  Max displacement: {disp.max():.6f} (at point {np.argmax(disp)})")
    print(f"  Mean displacement: {disp.mean():.6f}")

    # Replace boundary values in text (reverse order to preserve positions)
    text_chars = list(text)

    for i in range(nbbbs - 1, -1, -1):
        r_tok = bdry_tokens[2*i]
        z_tok = bdry_tokens[2*i + 1]

        # Replace Z value
        z_start = z_tok['start']
        z_end = z_tok['end']
        # Include leading whitespace
        z_field_start = z_start
        while z_field_start > 0 and text_chars[z_field_start - 1] == ' ':
            if z_field_start > 1 and text_chars[z_field_start - 2] == '\n':
                break
            if z_start - z_field_start >= 15:
                break
            z_field_start -= 1
        old_z_field = ''.join(text_chars[z_field_start:z_end])
        new_z_field = format_float_like(z_smooth[i], old_z_field)
        assert len(new_z_field) == len(old_z_field)
        for ci, c in enumerate(new_z_field):
            text_chars[z_field_start + ci] = c

        # Replace R value
        r_start = r_tok['start']
        r_end = r_tok['end']
        r_field_start = r_start
        while r_field_start > 0 and text_chars[r_field_start - 1] == ' ':
            if r_field_start > 1 and text_chars[r_field_start - 2] == '\n':
                break
            if r_start - r_field_start >= 15:
                break
            r_field_start -= 1
        old_r_field = ''.join(text_chars[r_field_start:r_end])
        new_r_field = format_float_like(r_smooth[i], old_r_field)
        assert len(new_r_field) == len(old_r_field)
        for ci, c in enumerate(new_r_field):
            text_chars[r_field_start + ci] = c

    new_text = ''.join(text_chars)

    if outfile is None:
        base = infile.rsplit('.', 1)
        outfile = base[0] + '_smooth.' + base[1] if len(base) > 1 else infile + '_smooth'

    with open(outfile, 'w') as f:
        f.write(new_text)

    sz_orig = len(text)
    sz_new = len(new_text)
    print(f"\nWritten: {outfile}")
    print(f"File size: {sz_orig} -> {sz_new} (delta={sz_new - sz_orig})")
    if sz_orig != sz_new:
        print(f"  WARNING: size changed!")
    else:
        print(f"  Size preserved ✓")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python smooth_gfile_boundary.py <geqdsk_file> [N_harmonics] [output]")
        print("  N_harmonics: Fourier modes to keep (default 8). Lower = smoother.")
        sys.exit(1)

    infile = sys.argv[1]
    n_harm = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    outfile = sys.argv[3] if len(sys.argv) > 3 else None
    smooth_gfile(infile, n_harm, outfile)
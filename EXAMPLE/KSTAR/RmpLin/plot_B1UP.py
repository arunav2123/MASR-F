#!/usr/bin/env python3
"""Plot B1UP.OUT from MARS-F RmpLin run."""
import numpy as np
import matplotlib.pyplot as plt

# Load data
data = np.loadtxt('B1UP.OUT')
s    = data[:, 0]   # normalised radial coord (sqrt psi_pol), -1 to 1
re1  = data[:, 1]   # Re(b1_perp)  — dominant perturbed field component
im1  = data[:, 2]   # Im(b1_perp)
re2  = data[:, 3]   # Re(b1_par)   — parallel component (usually small)
im2  = data[:, 4]   # Im(b1_par)

amp1 = np.sqrt(re1**2 + im1**2)
amp2 = np.sqrt(re2**2 + im2**2)

fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True)

# --- Panel 1: Real & Imaginary of b1_perp ---
ax = axes[0]
ax.plot(s, re1*1e3, 'b-',  label=r'Re($b^1_\perp$)')
ax.plot(s, im1*1e3, 'r--', label=r'Im($b^1_\perp$)')
ax.axhline(0, color='k', lw=0.5)
ax.set_ylabel(r'$b^1_\perp$ [$\times 10^{-3}$]')
ax.legend(loc='best')
ax.set_title('KSTAR 28957 — MARS-F RmpLin: B1UP (plasma response)')

# --- Panel 2: Amplitude of b1_perp ---
ax = axes[1]
ax.plot(s, amp1*1e3, 'k-', lw=1.5, label=r'$|b^1_\perp|$')
ax.set_ylabel(r'$|b^1_\perp|$ [$\times 10^{-3}$]')
ax.legend(loc='best')

# --- Panel 3: Parallel component ---
ax = axes[2]
ax.plot(s, re2*1e6, 'b-',  label=r'Re($b^1_\parallel$)')
ax.plot(s, im2*1e6, 'r--', label=r'Im($b^1_\parallel$)')
ax.plot(s, amp2*1e6, 'k-', lw=1.5, alpha=0.5, label=r'$|b^1_\parallel|$')
ax.axhline(0, color='k', lw=0.5)
ax.set_ylabel(r'$b^1_\parallel$ [$\times 10^{-6}$]')
ax.set_xlabel(r'$s$ (normalised radius)')
ax.legend(loc='best')

for ax in axes:
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('B1UP_KSTAR28957.png', dpi=150)
plt.show()
print("Saved B1UP_KSTAR28957.png")
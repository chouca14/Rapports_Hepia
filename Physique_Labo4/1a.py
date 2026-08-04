#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Labo 4A - Manipulation 1a : relation de conjugaison de Gauss.
Source de donnees : A.xlsx, feuille "1. a." (cm -> mm).
Modele : 1/q = m*(-1/p) + b   ->  pente theorique m = +1, ordonnee b = 1/f.
"""
import numpy as np
import openpyxl
from scipy import stats
import matplotlib.pyplot as plt

XLSX = "A.xlsx"
SHEET = "1. a."
AB = 10.0          # taille objet F (mm) = 1 cm
DELTA_L = 1.0      # incertitude de lecture par position (mm)

# --- Lecture des donnees (colonnes : C = p+offset, E = q-offset, F = A1B1, en cm) ---
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb[SHEET]
p, q, A1B1 = [], [], []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[2] is None or row[4] is None:
        continue
    p.append(float(row[2]) * 10.0)      # cm -> mm
    q.append(float(row[4]) * 10.0)
    A1B1.append(float(row[5]) * 10.0)
p, q, A1B1 = map(np.array, (p, q, A1B1))

# --- Grandeurs derivees ---
gamma = A1B1 / AB

# --- Propagation des incertitudes ---
# p = mesure_p + offset_p (lectures +/-1 mm chacune)  -> dp = sqrt(2)
# q = mesure_q - offset_q (mesure q +/-2 mm, offset +/-1 mm) -> dq = sqrt(2^2+1^2)
dp = np.sqrt(DELTA_L**2 + DELTA_L**2)            # = sqrt(2) ~ 1.41 mm
dq = np.sqrt((2*DELTA_L)**2 + DELTA_L**2)         # = sqrt(5) ~ 2.24 mm
dgamma = DELTA_L / AB                              # = 0.1

inv_q = 1.0 / q
inv_p = 1.0 / p
d_invq = dq / q**2
d_invp = dp / p**2

# --- Regression lineaire  Y = 1/q  vs  X = -1/p ---
X = -inv_p
Y = inv_q
res = stats.linregress(X, Y)
m, b = res.slope, res.intercept
dm, db = res.stderr, res.intercept_stderr
R2 = res.rvalue**2
f = 1.0 / b
df = db / b**2

print(f"dp = {dp:.4f} mm   dq = {dq:.4f} mm   dgamma = {dgamma}")
print(f"m  = {m:.4f} +/- {dm:.4f}   (theorique +1, ecart {abs(m-1)*100:.1f} %)")
print(f"b  = ({b*1e3:.5f} +/- {db*1e3:.5f}) e-3 mm^-1")
print(f"R2 = {R2:.5f}")
print(f"f  = {f:.2f} +/- {df:.2f} mm   (nominal 100 mm, ecart {abs(f-100)/100*100:.1f} %)")

# --- Tableau LaTeX (1/q et -1/p en 1e-3 mm^-1) ---
print("\n% --- corps de tableau (a coller) ---")
for i in range(len(p)):
    print(f"{p[i]:.0f} & {q[i]:.0f} & {gamma[i]:.1f} & "
          f"{inv_q[i]*1e3:.3f} & {d_invq[i]*1e3:.4f} & "
          f"{-inv_p[i]*1e3:.3f} & {d_invp[i]*1e3:.3f} \\\\")

# --- Figure ---
fig, ax = plt.subplots(figsize=(6.2, 4.4))
ax.errorbar(X*1e3, Y*1e3, xerr=d_invp*1e3, yerr=d_invq*1e3,
            fmt='o', ms=4, capsize=3, lw=0.8, color='#1f3b73',
            ecolor='#888', label='Mesures')
xfit = np.linspace(X.min(), X.max(), 100)
ax.plot(xfit*1e3, (m*xfit + b)*1e3, '-', color='#c0392b', lw=1.4,
        label='Régréssion linéaire')
# Equation de la regression (unites tracees : 10^-3 mm^-1)
eq_txt = (r'$\dfrac{1}{q} = (%.2f \pm %.2f)\left(-\dfrac{1}{p}\right) + (%.1f \pm %.1f)\times10^{-3}\,\mathrm{mm^{-1}}$'
          % (m, dm, b*1e3, db*1e3)
          + '\n' + r'$R^2 = %.4f \qquad f = 1/b = (%.0f \pm %.0f)\,\mathrm{mm}$' % (R2, f, df))
ax.text(0.04, 0.96, eq_txt, transform=ax.transAxes, va='top', ha='left',
        fontsize=8.5, bbox=dict(boxstyle='round,pad=0.4',
        fc='white', ec='#c0392b', alpha=0.9))
ax.set_xlabel(r'$-1/p\ \ /\ 10^{-3}\,\mathrm{mm^{-1}}$')
ax.set_ylabel(r'$1/q\ \ /\ 10^{-3}\,\mathrm{mm^{-1}}$')
ax.set_title('Relation de conjugaison de Gauss')
ax.grid(True, ls=':', alpha=0.5)
ax.legend(frameon=False, fontsize=9, loc='lower right')
fig.tight_layout()
fig.savefig("labo4_1a_gauss.pdf")
print("\nFigure -> labo4_1a_gauss.pdf")
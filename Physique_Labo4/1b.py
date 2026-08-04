#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Labo 4A - Manipulation 1b : methode de Bessel (Excel B).
Deux sorties : (1) f point par point, (2) ajustement lineaire (D^2-d^2)/4 = f*D
forcee par l'origine -> pente = f. Incertitudes affichees dans les labels.
"""
import numpy as np
import openpyxl
import matplotlib.pyplot as plt

XLSX, SHEET = "B.xlsx", "1. b. "
DELTA_L = 1.0
uD = ud = np.sqrt(2) * DELTA_L     # D et d : differences de 2 lectures +/-1 mm

# --- Lecture (colonnes A = D, D = d, en cm -> mm) ---
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb[SHEET]
D, d = [], []
for row in ws.iter_rows(min_row=2, values_only=True):
    if not isinstance(row[0], (int, float)):
        continue
    D.append(float(row[0]) * 10.0)
    d.append(float(row[3]) * 10.0)
D, d = np.array(D), np.array(d)

# --- f point par point + propagation ---
f = (D**2 - d**2) / (4 * D)
uf = np.sqrt(((D**2 + d**2) / (4 * D**2) * uD)**2 + (d / (2 * D) * ud)**2)
f_mean = f.mean()
f_std = f.std(ddof=1)
f_sem = f_std / np.sqrt(len(f))

# --- Ajustement lineaire force par l'origine : Y = f*X ---
X = D
Y = (D**2 - d**2) / 4.0                      # mm^2
uY = 0.5 * np.sqrt((D * uD)**2 + (d * ud)**2)
f_slope = np.sum(X * Y) / np.sum(X**2)
ss_res = np.sum((Y - f_slope * X)**2)
ss_tot = np.sum((Y - Y.mean())**2)
se_slope = np.sqrt(ss_res / ((len(X) - 1) * np.sum(X**2)))
r2 = 1 - ss_res / ss_tot

print(f"  point par point : f = ({f_mean:.3f} +/- {f_sem:.3f}) mm  [SEM]  s = {f_std:.3f} mm")
print(f"  ajustement lin. : f = ({f_slope:.3f} +/- {se_slope:.3f}) mm   R2 = {r2:.5f}")

# ============================ Figure 1 : f vs D ============================
fig1, ax1 = plt.subplots(figsize=(6.4, 4.4))
ax1.errorbar(D, f, yerr=uf, fmt='o', ms=5, color='#1f3b73', ecolor='#888',
             capsize=3, lw=0.8, zorder=3, label=r'$f$ par point')
ax1.axhline(f_mean, color='#c0392b', lw=1.6,
            label=fr'Moyenne : $f = ({f_mean:.2f} \pm {f_sem:.2f})$ mm')
ax1.fill_between([D.min() - 8, D.max() + 8], f_mean - f_std, f_mean + f_std,
                 color='#c0392b', alpha=0.12, label=fr'$\pm s = {f_std:.2f}$ mm')
ax1.set_xlim(D.min() - 8, D.max() + 8)
ax1.set_ylim(f_mean - 1.2, f_mean + 1.2)
ax1.set_xlabel('$D$ / mm'); ax1.set_ylabel('$f$ / mm')
ax1.set_title('Focale de Bessel en fonction de $D$')
ax1.grid(True, ls=':', alpha=0.5)
ax1.legend(fontsize=9, loc='upper right', frameon=False)
fig1.tight_layout(); fig1.savefig('labo4_1b_f_vs_D.pdf')

# =============== Figure 2 : Y=(D^2-d^2)/4 vs D, ajustement lineaire ===============
Dfit = np.linspace(D.min() - 8, D.max() + 8, 300)
fig2, ax2 = plt.subplots(figsize=(6.4, 4.4))
ax2.errorbar(X, Y, xerr=uD, yerr=uY, fmt='o', ms=5, color='#1f3b73',
             ecolor='#888', capsize=3, lw=0.8, zorder=3,
             label=r'$(D^2-d^2)/4$ mesuré')
ax2.plot(Dfit, f_slope * Dfit, '-', color='#c0392b', lw=1.6,
         label=fr'Régression : $f = ({f_slope:.2f} \pm {se_slope:.2f})$ mm, $R^2={r2:.4f}$')
ax2.set_xlabel('$D$ / mm'); ax2.set_ylabel(r'$(D^2-d^2)/4$ / mm$^2$')
ax2.set_title(r'Vérification : $(D^2-d^2)/4 = f\,D$')
ax2.grid(True, ls=':', alpha=0.5)
ax2.legend(fontsize=9, loc='upper left', frameon=False)
fig2.tight_layout(); fig2.savefig('labo4_1b_verification.pdf')
print("\n  Figures -> labo4_1b_f_vs_D.pdf , labo4_1b_verification.pdf")
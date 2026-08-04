#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Labo 4A - Manipulation 1c : grandissement gamma = f(d) par configuration (Excel B).
Deux systemes optiques distincts :
  (1) deux lentilles convexes (f1=100, f2=50)
        - accolee : d~8 mm (p1=43 mm) -> point d->0
        - separees : d = 25.4 / 28.7 / 30.6 cm (p1=185 mm)
  (2) convexe + concave (f1=100, f2=-100) : d = 18.4 / 19.2 / 20.5 cm
"2 collees" n'est PAS un systeme separe : c'est la limite d->0 du systeme (1).
"""
import numpy as np
import matplotlib.pyplot as plt

U_G = 0.1   # incertitude sur gamma (image +/-1 mm, objet 10 mm)

# ---- (1) deux convexes ----
cc_sep_d = np.array([25.4, 28.7, 30.6])   # cm, separees
cc_sep_g = np.array([3.6,  1.1,  0.8])
cc_acc_d, cc_acc_g = 0.8, 1.0             # accolee (d~8 mm)

# ---- (2) convexe + concave ----
cd_d = np.array([18.4, 19.2, 20.5])       # cm
cd_g = np.array([3.5,  2.6,  2.6])

def style(ax, title):
    ax.set_xlabel("Distance entre les lentilles $d$ (cm)")
    ax.set_ylabel(r"Grandissement $\gamma$")
    ax.set_title(title, fontweight='bold')
    ax.grid(True, ls=':', alpha=0.5)
    ax.legend(frameon=True, loc='best')

# --- Figure 1 : deux convexes ---
i = np.argsort(cc_sep_d)
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.errorbar(cc_sep_d[i], cc_sep_g[i], yerr=U_G, fmt='-o', color='#1f3bd6',
            mfc='white', mec='#1f3bd6', mew=1.8, ms=8, lw=2, capsize=3,
            label=r'$\gamma$ mesuré (séparées)')
style(ax, r"Deux lentilles convexes : $\gamma = f(d)$")
fig.tight_layout(); fig.savefig("labo4_1c_convconv.pdf")

# --- Figure 2 : convexe + concave ---
i = np.argsort(cd_d)
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.errorbar(cd_d[i], cd_g[i], yerr=U_G, fmt='-s', color='#d62728',
            mfc='white', mec='#d62728', mew=1.8, ms=8, lw=2, capsize=3,
            label=r'$\gamma$ mesuré')
style(ax, r"Lentille convexe + lentille concave : $\gamma = f(d)$")
fig.tight_layout(); fig.savefig("labo4_1c_convdiv.pdf")

feq = 1/(1/43 + 1/85)
print(f"Accolée : feq_mes = {feq:.1f} mm (théorie d=0 : 33.3 mm, écart {100*abs(feq-33.3)/33.3:.0f} %)")
print("Figures -> labo4_1c_convconv.pdf, labo4_1c_convdiv.pdf")
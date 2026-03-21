"""
Condensed matter / strongly correlated electrons domain configuration (skeleton).

Competing approaches to modeling strongly correlated electron systems.
Each method makes different predictions for the same observables.

To use: copy this to pipeline/config.py and adapt TheoryDef entries.
"""

DOMAIN = {
    "name": "Strongly Correlated Electrons",
    "description": "Competing methods for modeling strongly correlated electron systems",
    "theories": [
        {
            "name": "BCS Theory",
            "slug": "bcs",
            "key_object": "Cooper pair condensation, mean-field gap equation",
            "arxiv_categories": ["cond-mat.supr-con"],
            "search_queries": [
                "BCS theory superconductivity",
                "BCS gap equation",
            ],
            "seed_papers": [],
            "key_parameters": ["Delta (gap)", "lambda (coupling)", "T_c"],
        },
        {
            "name": "Eliashberg Theory",
            "slug": "eliashberg",
            "key_object": "strong-coupling superconductivity, retardation effects",
            "arxiv_categories": ["cond-mat.supr-con"],
            "search_queries": [
                "Eliashberg theory superconductivity",
                "strong coupling superconductivity phonon",
            ],
            "seed_papers": [],
            "key_parameters": ["lambda (electron-phonon)", "mu_star (Coulomb pseudopotential)", "omega_log"],
        },
        {
            "name": "DFT+U",
            "slug": "dft_plus_u",
            "key_object": "density functional theory with Hubbard U correction",
            "arxiv_categories": ["cond-mat.str-el", "cond-mat.mtrl-sci"],
            "search_queries": [
                "DFT+U strongly correlated",
                "Hubbard U correction density functional",
            ],
            "seed_papers": [],
            "key_parameters": ["U (Hubbard)", "J (Hund coupling)"],
        },
        {
            "name": "Dynamical Mean-Field Theory (DMFT)",
            "slug": "dmft",
            "key_object": "local self-energy, impurity solver, Mott transition",
            "arxiv_categories": ["cond-mat.str-el"],
            "search_queries": [
                "dynamical mean field theory",
                "DMFT Mott transition",
                "DMFT spectral function",
            ],
            "seed_papers": [],
            "key_parameters": ["Sigma(omega) (self-energy)", "Z (quasiparticle weight)"],
        },
        {
            "name": "Hubbard Model (Exact/Numerical)",
            "slug": "hubbard_exact",
            "key_object": "exact diagonalization, QMC, DMRG on Hubbard Hamiltonian",
            "arxiv_categories": ["cond-mat.str-el"],
            "search_queries": [
                "Hubbard model exact diagonalization",
                "quantum Monte Carlo Hubbard",
                "DMRG strongly correlated",
            ],
            "seed_papers": [],
            "key_parameters": ["U/t (interaction/hopping ratio)", "n (filling)"],
        },
    ],
    "comparable_quantities": [
        {
            "slug": "critical_temperature",
            "name": "Critical Temperature T_c",
            "description": "Superconducting transition temperature",
            "keywords": ["T_c", "critical temperature", "transition temperature", "superconducting"],
        },
        {
            "slug": "gap_symmetry",
            "name": "Order Parameter Symmetry",
            "description": "Symmetry of the superconducting gap (s-wave, d-wave, etc.)",
            "keywords": ["gap symmetry", "order parameter", "s-wave", "d-wave", "nodal"],
        },
        {
            "slug": "spectral_function",
            "name": "Single-Particle Spectral Function",
            "description": "A(k, omega) measured by ARPES",
            "keywords": ["spectral function", "ARPES", "quasiparticle", "self-energy"],
        },
        {
            "slug": "mott_transition",
            "name": "Mott Transition",
            "description": "Metal-insulator transition at critical U/t",
            "keywords": ["Mott transition", "metal-insulator", "U/t critical", "Mott gap"],
        },
        {
            "slug": "magnetic_order",
            "name": "Magnetic Ordering",
            "description": "Predicted magnetic phase and exchange constants",
            "keywords": ["antiferromagnetic", "magnetic order", "Neel temperature", "exchange coupling"],
        },
    ],
}

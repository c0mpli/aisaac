"""
Quantum Gravity domain configuration.

This is the default domain — 8 competing approaches to quantum gravity.
Use this as a template for creating your own domain.
"""

DOMAIN = {
    "name": "Quantum Gravity",
    "description": "Competing approaches to unifying gravity with quantum mechanics",
    "theories": [
        {
            "name": "String Theory",
            "slug": "string_theory",
            "key_object": "Polyakov action, worldsheet, strings/branes",
            "arxiv_categories": ["hep-th"],
            "search_queries": [
                "quantum gravity string theory",
                "string theory black hole entropy microscopic",
                "AdS/CFT correspondence gravity",
            ],
            "seed_papers": [
                "hep-th/9905111",   # MAGOO (AdS/CFT review)
                "hep-th/9601029",   # Strominger-Vafa BH entropy
                "gr-qc/9310024",    # Donoghue Newton correction
                "hep-th/0603001",   # Ryu-Takayanagi
            ],
            "key_parameters": ["alpha_prime (string tension)", "g_s (string coupling)"],
        },
        {
            "name": "Loop Quantum Gravity",
            "slug": "loop_quantum_gravity",
            "key_object": "Ashtekar connection, spin networks, spin foams",
            "arxiv_categories": ["gr-qc", "hep-th"],
            "search_queries": [
                "loop quantum gravity",
                "spin foam models quantum gravity",
                "loop quantum gravity black hole entropy",
            ],
            "seed_papers": [
                "gr-qc/0404018",   # Rovelli review
                "gr-qc/9411005",   # Area spectrum
                "gr-qc/0002040",   # Log correction to BH entropy
                "0811.1396",       # Spectral dimension in LQG
            ],
            "key_parameters": ["gamma_I (Immirzi parameter)", "l_P (Planck length)"],
        },
        {
            "name": "Causal Dynamical Triangulations",
            "slug": "cdt",
            "key_object": "simplicial path integral with causality",
            "arxiv_categories": ["hep-th", "gr-qc"],
            "search_queries": [
                "causal dynamical triangulations",
                "CDT quantum gravity spectral dimension",
            ],
            "seed_papers": [
                "hep-th/0105267",  # Ambjorn-Jurkiewicz-Loll
                "hep-th/0505113",  # Spectral dimension in CDT
            ],
            "key_parameters": ["kappa_0 (inverse Newton)", "kappa_4 (cosmological)"],
        },
        {
            "name": "Asymptotic Safety",
            "slug": "asymptotic_safety",
            "key_object": "functional RG for gravity, UV fixed point",
            "arxiv_categories": ["hep-th", "gr-qc"],
            "search_queries": [
                "asymptotic safety quantum gravity",
                "functional renormalization group gravity",
            ],
            "seed_papers": [
                "1202.2274",       # Reuter-Saueressig review
                "hep-th/9605030",  # Reuter original
                "hep-th/0508202",  # Spectral dimension from AS
            ],
            "key_parameters": ["G(k) (running Newton)", "g_star (UV fixed point)"],
        },
        {
            "name": "Causal Sets",
            "slug": "causal_sets",
            "key_object": "partially ordered set (causet)",
            "arxiv_categories": ["gr-qc", "hep-th"],
            "search_queries": [
                "causal set quantum gravity",
                "causal set cosmological constant",
            ],
            "seed_papers": [
                "gr-qc/0309009",  # Sorkin review
                "1903.11544",     # Surya review
            ],
            "key_parameters": ["rho (sprinkling density)"],
        },
        {
            "name": "Horava-Lifshitz Gravity",
            "slug": "horava_lifshitz",
            "key_object": "anisotropic scaling z=3 in UV",
            "arxiv_categories": ["hep-th", "gr-qc"],
            "search_queries": [
                "Horava-Lifshitz gravity",
                "Horava gravity anisotropic scaling",
            ],
            "seed_papers": [
                "0901.3775",      # Horava original
                "1007.5199",      # Mukohyama review
            ],
            "key_parameters": ["z (dynamical critical exponent)", "lambda (coupling)"],
        },
        {
            "name": "Noncommutative Geometry",
            "slug": "noncommutative_geometry",
            "key_object": "spectral triple, [x^mu, x^nu] != 0",
            "arxiv_categories": ["hep-th", "math-ph", "gr-qc"],
            "search_queries": [
                "noncommutative geometry gravity",
                "noncommutative spacetime quantum gravity",
            ],
            "seed_papers": [
                "hep-th/0510059", # Szabo review
                "hep-th/0012051", # NC dispersion relation
            ],
            "key_parameters": ["theta (noncommutativity parameter)"],
        },
        {
            "name": "Emergent Gravity / Holographic",
            "slug": "emergent_gravity",
            "key_object": "gravity from entanglement / thermodynamics",
            "arxiv_categories": ["hep-th", "gr-qc", "quant-ph"],
            "search_queries": [
                "emergent gravity entanglement",
                "Ryu-Takayanagi formula",
                "Verlinde entropic gravity",
            ],
            "seed_papers": [
                "1001.0785",      # Verlinde
                "1005.3035",      # Van Raamsdonk
                "0905.1317",      # RT review
            ],
            "key_parameters": ["S_EE (entanglement entropy)"],
        },
    ],
    "comparable_quantities": [
        {
            "slug": "spectral_dimension",
            "name": "Spectral Dimension",
            "description": "Effective dimensionality of spacetime as function of probe scale",
            "keywords": ["d_s", "spectral dimension", "return probability", "diffusion", "dimensional flow"],
        },
        {
            "slug": "black_hole_entropy",
            "name": "Black Hole Entropy",
            "description": "Microscopic derivation of Bekenstein-Hawking entropy S = A/4",
            "keywords": ["S_BH", "Bekenstein-Hawking", "microstate counting", "horizon entropy"],
        },
        {
            "slug": "bh_entropy_log_correction",
            "name": "BH Entropy Log Correction",
            "description": "Logarithmic correction coefficient to BH entropy",
            "keywords": ["logarithmic correction", "subleading", "ln(A)", "log correction"],
        },
        {
            "slug": "newton_correction",
            "name": "Newton Correction",
            "description": "Leading quantum correction to Newtonian gravitational potential",
            "keywords": ["quantum correction", "gravitational potential", "V(r)", "graviton exchange"],
        },
        {
            "slug": "dispersion_relation_modification",
            "name": "Modified Dispersion Relation",
            "description": "How E^2 = p^2 + m^2 is modified at high energy",
            "keywords": ["dispersion relation", "Lorentz violation", "Planck-scale", "E-p relation"],
        },
        {
            "slug": "running_gravitational_coupling",
            "name": "Running Gravitational Coupling",
            "description": "Scale-dependent Newton constant G(k)",
            "keywords": ["running G", "running Newton", "beta function", "RG flow", "scale-dependent"],
        },
        {
            "slug": "graviton_propagator_modification",
            "name": "Graviton Propagator Modification",
            "description": "How graviton propagator is modified at high energy",
            "keywords": ["graviton propagator", "UV graviton", "momentum-space gravity"],
        },
        {
            "slug": "area_gap",
            "name": "Area Gap",
            "description": "Minimum nonzero eigenvalue of area operator",
            "keywords": ["minimum area", "area spectrum", "area eigenvalue", "discrete area"],
        },
        {
            "slug": "entanglement_entropy_area_law",
            "name": "Entanglement Entropy Area Law",
            "description": "Entanglement entropy scales with boundary area",
            "keywords": ["Ryu-Takayanagi", "entanglement entropy", "holographic entanglement", "area law"],
        },
    ],
}

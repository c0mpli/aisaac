"""
Turbulence modeling domain configuration (skeleton).

Competing approaches to modeling turbulent flows.
Each RANS/LES/DNS family makes different predictions for
the same physical quantities. AIsaac can find where they
agree and disagree.

To use: copy this to pipeline/config.py and adapt TheoryDef entries.
"""

DOMAIN = {
    "name": "Turbulence Modeling",
    "description": "Competing closure models for turbulent fluid flows",
    "theories": [
        {
            "name": "k-epsilon Model",
            "slug": "k_epsilon",
            "key_object": "two-equation model: turbulent kinetic energy k, dissipation rate epsilon",
            "arxiv_categories": ["physics.flu-dyn"],
            "search_queries": [
                "k-epsilon turbulence model",
                "standard k-epsilon RANS",
                "k-epsilon closure coefficients",
            ],
            "seed_papers": [],  # Add DOIs or arXiv IDs of key papers
            "key_parameters": ["C_mu", "C_epsilon1", "C_epsilon2", "sigma_k", "sigma_epsilon"],
        },
        {
            "name": "k-omega SST Model",
            "slug": "k_omega_sst",
            "key_object": "two-equation model: k and specific dissipation rate omega",
            "arxiv_categories": ["physics.flu-dyn"],
            "search_queries": [
                "k-omega SST turbulence model",
                "Menter SST model",
            ],
            "seed_papers": [],
            "key_parameters": ["a1", "beta_star", "sigma_w1", "sigma_w2"],
        },
        {
            "name": "Reynolds Stress Model (RSM)",
            "slug": "rsm",
            "key_object": "full Reynolds stress transport equations",
            "arxiv_categories": ["physics.flu-dyn"],
            "search_queries": [
                "Reynolds stress model turbulence",
                "second moment closure turbulence",
            ],
            "seed_papers": [],
            "key_parameters": ["C_s", "C_L", "C_1", "C_2"],
        },
        {
            "name": "Large Eddy Simulation (LES)",
            "slug": "les",
            "key_object": "subgrid-scale models, filtered Navier-Stokes",
            "arxiv_categories": ["physics.flu-dyn"],
            "search_queries": [
                "large eddy simulation subgrid model",
                "Smagorinsky model LES",
                "dynamic subgrid scale model",
            ],
            "seed_papers": [],
            "key_parameters": ["C_s (Smagorinsky)", "Delta (filter width)"],
        },
        {
            "name": "Detached Eddy Simulation (DES)",
            "slug": "des",
            "key_object": "hybrid RANS-LES switching",
            "arxiv_categories": ["physics.flu-dyn"],
            "search_queries": [
                "detached eddy simulation",
                "DDES delayed detached eddy",
                "hybrid RANS-LES",
            ],
            "seed_papers": [],
            "key_parameters": ["C_DES", "switching function"],
        },
    ],
    "comparable_quantities": [
        {
            "slug": "reynolds_stress",
            "name": "Reynolds Stress Tensor",
            "description": "Predicted Reynolds stress components <u_i u_j>",
            "keywords": ["Reynolds stress", "turbulent stress", "u'v'", "anisotropy"],
        },
        {
            "slug": "dissipation_rate",
            "name": "Turbulent Dissipation Rate",
            "description": "Rate of turbulent kinetic energy dissipation",
            "keywords": ["dissipation rate", "epsilon", "energy cascade", "Kolmogorov"],
        },
        {
            "slug": "wall_function",
            "name": "Wall Function / Law of the Wall",
            "description": "Near-wall velocity profile prediction",
            "keywords": ["wall function", "law of the wall", "y+", "u+", "buffer layer"],
        },
        {
            "slug": "energy_spectrum",
            "name": "Turbulent Energy Spectrum",
            "description": "E(k) energy spectrum prediction",
            "keywords": ["energy spectrum", "E(k)", "inertial range", "Kolmogorov -5/3"],
        },
        {
            "slug": "separation_prediction",
            "name": "Flow Separation Point",
            "description": "Predicted location of boundary layer separation",
            "keywords": ["separation", "adverse pressure gradient", "recirculation"],
        },
    ],
}

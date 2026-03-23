"""Historical dataset of premise shifts in science.

Each entry documents a case where progress required abandoning a wrong premise,
recording the symptoms that preceded the shift and the nature of the error.

Historical accuracy is prioritized. Evidence citations refer to actual papers,
experiments, and observations. Where uncertainty exists, confidence is lowered.
"""

from .symptoms import (
    PremiseErrorType,
    PremiseShiftRecord,
    Symptom,
    SymptomType,
)


def build_dataset() -> list[PremiseShiftRecord]:
    """Build and return the historical dataset of premise shifts."""

    records: list[PremiseShiftRecord] = []

    # =========================================================================
    # PHYSICS
    # =========================================================================

    # 1. Special Relativity
    records.append(PremiseShiftRecord(
        field="physics",
        year=1905,
        person="Albert Einstein",
        old_premise="Time is absolute and the same for all observers; light propagates through a luminiferous ether",
        new_premise="The speed of light is constant in all inertial frames; time and space are relative to the observer",
        premise_error_type=PremiseErrorType.UNNECESSARY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Michelson-Morley experiment found no ether drift",
                evidence=[
                    "Michelson & Morley, 'On the Relative Motion of the Earth and the Luminiferous Ether', American Journal of Science 34 (1887) 333-345",
                    "Repeated by Morley & Miller (1902-1904) with consistent null results",
                ],
                confidence=0.95,
                affected_quantity="ether wind velocity",
                theories_involved=["Maxwellian electrodynamics", "Newtonian mechanics"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Lorentz-FitzGerald contraction hypothesis required ad-hoc length contraction to explain null result",
                evidence=[
                    "FitzGerald, Science 13 (1889) 390",
                    "Lorentz, 'Electromagnetic phenomena in a system moving with any velocity smaller than that of light', Proc. Royal Netherlands Acad. Arts Sci. 6 (1904) 809-831",
                ],
                confidence=0.90,
                affected_quantity="length contraction factor",
                theories_involved=["Lorentz ether theory"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Maxwell's equations predicted a universal speed of light independent of source motion, yet Newtonian mechanics required a preferred frame",
                evidence=[
                    "Maxwell, 'A Dynamical Theory of the Electromagnetic Field', Phil. Trans. Royal Society 155 (1865) 459-512",
                ],
                confidence=0.85,
                affected_quantity="speed of light",
                theories_involved=["Maxwell electrodynamics", "Newtonian mechanics"],
            ),
        ],
        time_stuck_years=18,
        time_to_solve_after=1,
        key_insight="Take Maxwell's equations at face value: the speed of light is a law of physics, not a property of a medium. Abandon absolute simultaneity.",
        what_made_it_hard="Absolute time was so deeply embedded in intuition and Newtonian mechanics that it was invisible as an assumption. Lorentz's ether theory could fit the data with enough patches.",
        trigger="Einstein's thought experiment about riding alongside a light beam, combined with reading Lorentz and Poincare on local time",
    ))

    # 2. General Relativity
    records.append(PremiseShiftRecord(
        field="physics",
        year=1915,
        person="Albert Einstein",
        old_premise="Gravity is a force acting at a distance through flat spacetime; spacetime geometry is fixed and non-dynamical",
        new_premise="Gravity is the curvature of spacetime caused by mass-energy; spacetime geometry is dynamical",
        premise_error_type=PremiseErrorType.IMPLICIT_BACKGROUND,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Inertial mass equals gravitational mass to extraordinary precision with no explanation",
                evidence=[
                    "Eotvos experiments (1885-1909) showing equivalence to 1 part in 10^8",
                    "Newton noted the coincidence in Principia Book III but offered no explanation",
                ],
                confidence=0.95,
                affected_quantity="ratio of inertial to gravitational mass",
                theories_involved=["Newtonian gravity"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Newtonian gravity acts instantaneously, violating special relativity's speed limit",
                evidence=[
                    "Poincare noted this incompatibility in 'Sur la dynamique de l'electron' (1905-1906)",
                    "Nordstrom's scalar theory of gravity (1912-1913) was an early attempt at reconciliation",
                ],
                confidence=0.90,
                affected_quantity="speed of gravitational interaction",
                theories_involved=["Newtonian gravity", "special relativity"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Anomalous precession of Mercury's perihelion: 43 arcseconds/century unexplained by Newtonian gravity",
                evidence=[
                    "Le Verrier, 'Lettre de M. Le Verrier a M. Faye sur la theorie de Mercure', Comptes Rendus 49 (1859) 379-383",
                    "Newcomb refined the discrepancy to 43 arcsec/century (1882)",
                ],
                confidence=0.95,
                affected_quantity="perihelion precession of Mercury",
                theories_involved=["Newtonian gravity", "celestial mechanics"],
            ),
        ],
        time_stuck_years=10,
        time_to_solve_after=3,
        key_insight="The equivalence of inertial and gravitational mass is not a coincidence but a clue: gravity is not a force but the geometry of spacetime. A person in free fall feels no gravity.",
        what_made_it_hard="The mathematical framework (Riemannian geometry, tensor calculus) was unfamiliar to physicists. The conceptual leap from fixed background to dynamical geometry was enormous.",
        trigger="Einstein's 'happiest thought' (1907): a person falling from a roof feels no gravity. This led to the equivalence principle as a foundational axiom.",
    ))

    # 3. Quantum mechanics (Planck)
    records.append(PremiseShiftRecord(
        field="physics",
        year=1900,
        person="Max Planck",
        old_premise="Energy is emitted and absorbed continuously; classical mechanics and electrodynamics apply at all scales",
        new_premise="Energy exchange between matter and radiation occurs in discrete quanta E = h*nu",
        premise_error_type=PremiseErrorType.CONTINUITY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Ultraviolet catastrophe: Rayleigh-Jeans law predicts infinite energy at high frequencies",
                evidence=[
                    "Rayleigh, 'Remarks upon the Law of Complete Radiation', Phil. Mag. 49 (1900) 539-540",
                    "Jeans, 'On the partition of energy between matter and ether', Phil. Mag. 10 (1905) 91-98",
                ],
                confidence=0.95,
                affected_quantity="blackbody spectral energy density at high frequencies",
                theories_involved=["classical electrodynamics", "equipartition theorem"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Wien's law fit short wavelengths but failed at long wavelengths; Rayleigh-Jeans fit long but diverged at short",
                evidence=[
                    "Wien, 'Ueber die Energievertheilung im Emissionsspectrum eines schwarzen Korpers', Annalen der Physik 294 (1896) 662-669",
                    "Lummer & Pringsheim (1899) and Rubens & Kurlbaum (1900) measured deviations from Wien's law",
                ],
                confidence=0.90,
                affected_quantity="blackbody spectrum",
                theories_involved=["Wien's radiation law", "Rayleigh-Jeans law"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Specific heats of solids deviated from the classical Dulong-Petit value at low temperatures",
                evidence=[
                    "Weber (1875) measured anomalously low specific heat of diamond",
                    "Dewar's cryogenic measurements (1890s) showed systematic deviations",
                ],
                confidence=0.75,
                affected_quantity="specific heat at low temperature",
                theories_involved=["classical statistical mechanics"],
            ),
        ],
        time_stuck_years=40,
        time_to_solve_after=1,
        key_insight="Treat energy quantization not as a mathematical trick but as physical reality. The oscillators in cavity walls can only exchange energy in units of h*nu.",
        what_made_it_hard="Continuity of energy was a bedrock assumption of all physics since Newton. Planck himself resisted the physical interpretation for years, calling it an act of desperation.",
        trigger="Rubens & Kurlbaum's precise measurements of the blackbody spectrum at long wavelengths (1900), which deviated from Wien's law and forced Planck to find an interpolation formula",
    ))

    # 4. Matrix mechanics / quantum observables
    records.append(PremiseShiftRecord(
        field="physics",
        year=1925,
        person="Werner Heisenberg",
        old_premise="Electrons have definite trajectories (position and momentum at all times); atomic physics should describe orbits",
        new_premise="Only observable quantities (spectral lines, transition amplitudes) have physical meaning; position and momentum are non-commuting operators",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Bohr-Sommerfeld old quantum theory required ad-hoc quantization rules and failed for helium and complex atoms",
                evidence=[
                    "Bohr, 'On the Constitution of Atoms and Molecules', Phil. Mag. 26 (1913) 1-25",
                    "Kramers' helium calculation (1923) failed to match experiments",
                    "The anomalous Zeeman effect could not be explained without additional ad-hoc rules",
                ],
                confidence=0.90,
                affected_quantity="atomic energy levels",
                theories_involved=["Bohr-Sommerfeld model"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Half-integer quantum numbers were needed for the anomalous Zeeman effect but had no classical justification",
                evidence=[
                    "Lande's g-factor (1921) required half-integer angular momentum",
                    "Pauli's exclusion principle (1925) was imposed without dynamical derivation",
                ],
                confidence=0.85,
                affected_quantity="angular momentum quantum numbers",
                theories_involved=["Bohr-Sommerfeld model", "classical mechanics"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Selection rules for spectral transitions had no mechanical explanation in orbit models",
                evidence=[
                    "Bohr's correspondence principle could derive selection rules only in the limit of large quantum numbers",
                    "Kramers-Heisenberg dispersion relation (1925) worked with transition amplitudes, not orbits",
                ],
                confidence=0.80,
                affected_quantity="spectral line intensities",
                theories_involved=["Bohr model", "classical dispersion theory"],
            ),
        ],
        time_stuck_years=12,
        time_to_solve_after=1,
        key_insight="Abandon the concept of electron orbits entirely. Build mechanics solely from observable quantities: transition frequencies and amplitudes between stationary states.",
        what_made_it_hard="The idea that particles 'must' have trajectories was deeply embedded in classical intuition. The mathematical framework (matrix algebra) was unfamiliar to most physicists.",
        trigger="Heisenberg's isolation on Helgoland (June 1925), working with Kramers-Heisenberg dispersion theory and realizing that arrays of transition amplitudes obeyed a non-commutative multiplication rule",
    ))

    # 5. Antimatter (Dirac)
    records.append(PremiseShiftRecord(
        field="physics",
        year=1928,
        person="Paul Dirac",
        old_premise="Negative energy solutions to relativistic wave equations are unphysical and should be discarded",
        new_premise="Negative energy solutions predict a new form of matter: antiparticles (positrons)",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Klein-Gordon equation had negative probability densities; negative energy solutions could not be consistently discarded",
                evidence=[
                    "Klein, 'Quantentheorie und funfdimensionale Relativitatstheorie', Zeitschrift fur Physik 37 (1926) 895-906",
                    "Gordon, 'Der Comptoneffekt nach der Schrodingerschen Theorie', Zeitschrift fur Physik 40 (1926) 117-133",
                ],
                confidence=0.85,
                affected_quantity="probability density (negative values)",
                theories_involved=["relativistic quantum mechanics"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Schrodinger equation was not Lorentz-invariant; any relativistic extension faced negative energy states",
                evidence=[
                    "Dirac, 'The Quantum Theory of the Electron', Proc. Royal Society A 117 (1928) 610-624",
                ],
                confidence=0.90,
                affected_quantity="relativistic electron energy spectrum",
                theories_involved=["quantum mechanics", "special relativity"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Electron spin (g-factor ~ 2) was an empirical add-on in non-relativistic quantum mechanics",
                evidence=[
                    "Uhlenbeck & Goudsmit proposed intrinsic spin (1925) but it was ad-hoc",
                    "Thomas precession (1926) gave the correct factor of 2 but from kinematic arguments",
                ],
                confidence=0.80,
                affected_quantity="electron g-factor",
                theories_involved=["non-relativistic quantum mechanics"],
            ),
        ],
        time_stuck_years=2,
        time_to_solve_after=4,
        key_insight="The Dirac equation naturally produces spin-1/2 and negative energy solutions. Rather than discard them, interpret the 'Dirac sea' as predicting positrons -- a new particle.",
        what_made_it_hard="No one expected the equation to predict new particles. Dirac initially tried to identify the negative energy states with protons. The positron had to be experimentally discovered (Anderson, 1932).",
        trigger="Dirac seeking a relativistic wave equation linear in time derivative to avoid negative probability densities, leading to a 4-component spinor equation",
    ))

    # 6. AdS/CFT correspondence
    records.append(PremiseShiftRecord(
        field="physics/string theory",
        year=1997,
        person="Juan Maldacena",
        old_premise="Gravitational theories and gauge theories are fundamentally different kinds of theories in different dimensions",
        new_premise="A gravitational theory in (d+1)-dimensional anti-de Sitter space is exactly dual to a conformal field theory on the d-dimensional boundary",
        premise_error_type=PremiseErrorType.FALSE_DICHOTOMY,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Black hole entropy scales with area, not volume, suggesting gravity has fewer degrees of freedom than expected",
                evidence=[
                    "Bekenstein, 'Black holes and entropy', Phys. Rev. D 7 (1973) 2333",
                    "'t Hooft, 'Dimensional Reduction in Quantum Gravity', gr-qc/9310026 (1993)",
                    "Susskind, 'The World as a Hologram', J. Math. Phys. 36 (1995) 6377",
                ],
                confidence=0.90,
                affected_quantity="black hole entropy (area vs volume scaling)",
                theories_involved=["general relativity", "quantum field theory", "string theory"],
            ),
            Symptom(
                symptom_type=SymptomType.DUAL_DESCRIPTION,
                description="D-branes could be described both as sources of closed-string (gravitational) fields and as objects on which open strings (gauge fields) end",
                evidence=[
                    "Polchinski, 'Dirichlet Branes and Ramond-Ramond Charges', Phys. Rev. Lett. 75 (1995) 4724",
                    "Strominger & Vafa, 'Microscopic Origin of the Bekenstein-Hawking Entropy', Phys. Lett. B 379 (1996) 99",
                ],
                confidence=0.90,
                affected_quantity="D-brane dynamics",
                theories_involved=["string theory", "gauge theory"],
            ),
            Symptom(
                symptom_type=SymptomType.UNIVERSAL_QUANTITY,
                description="The large-N limit of gauge theories resembled string perturbation theory in its diagrammatic structure",
                evidence=[
                    "'t Hooft, 'A Planar Diagram Theory for Strong Interactions', Nuclear Physics B 72 (1974) 461",
                ],
                confidence=0.80,
                affected_quantity="1/N expansion vs string coupling",
                theories_involved=["large-N gauge theory", "string theory"],
            ),
        ],
        time_stuck_years=23,
        time_to_solve_after=1,
        key_insight="The open-string and closed-string descriptions of D-brane stacks are not alternatives but are exactly equivalent: N=4 SYM in 4d equals Type IIB string theory on AdS_5 x S^5.",
        what_made_it_hard="Gauge/gravity duality requires changing the number of spacetime dimensions. The idea that a theory with gravity can be equivalent to one without gravity was deeply counterintuitive.",
        trigger="Maldacena studying the near-horizon limit of a stack of N D3-branes and recognizing the two descriptions (supergravity in the throat and gauge theory on the branes) must be equivalent",
    ))

    # 7. Hawking radiation
    records.append(PremiseShiftRecord(
        field="physics",
        year=1974,
        person="Stephen Hawking",
        old_premise="Black holes are perfectly black; nothing escapes from beyond the event horizon",
        new_premise="Black holes emit thermal radiation at temperature T = hbar*c^3 / (8*pi*G*M*k_B) and slowly evaporate",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Bekenstein showed black holes must carry entropy proportional to horizon area, implying thermodynamic behavior",
                evidence=[
                    "Bekenstein, 'Black holes and entropy', Phys. Rev. D 7 (1973) 2333-2346",
                ],
                confidence=0.90,
                affected_quantity="black hole entropy",
                theories_involved=["general relativity", "thermodynamics"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="If black holes have entropy but zero temperature, the second law of thermodynamics would be violated by throwing entropy into a black hole",
                evidence=[
                    "Bekenstein, 'Generalized second law of thermodynamics in black-hole physics', Phys. Rev. D 9 (1974) 3292",
                    "Bardeen, Carter & Hawking, 'The four laws of black hole mechanics', Commun. Math. Phys. 31 (1973) 161-170",
                ],
                confidence=0.85,
                affected_quantity="black hole temperature",
                theories_involved=["general relativity", "thermodynamics", "quantum field theory"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="The laws of black hole mechanics exactly paralleled the laws of thermodynamics, but the analogy was dismissed as formal",
                evidence=[
                    "Bardeen, Carter & Hawking (1973) derived four laws analogous to thermodynamic laws but stated the analogy was not physical",
                ],
                confidence=0.85,
                affected_quantity="surface gravity / temperature analogy",
                theories_involved=["general relativity", "thermodynamics"],
            ),
        ],
        time_stuck_years=1,
        time_to_solve_after=1,
        key_insight="Apply quantum field theory in curved spacetime near the horizon. Pair creation near the horizon allows one particle to escape while the other falls in, producing thermal radiation.",
        what_made_it_hard="Classical GR says nothing escapes. The calculation required combining quantum field theory with curved spacetime in a regime no one had explored. Most physicists believed the thermodynamic analogy was merely formal.",
        trigger="Hawking set out to prove Bekenstein wrong (that black holes have no real temperature) but his own calculation showed they do radiate",
    ))

    # 8. Bekenstein bound / black hole entropy
    records.append(PremiseShiftRecord(
        field="physics",
        year=1973,
        person="Jacob Bekenstein",
        old_premise="Black holes have no entropy; they destroy information and violate the second law of thermodynamics",
        new_premise="Black holes carry entropy proportional to their horizon area: S = k_B * A / (4 * l_P^2)",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Throwing a hot gas into a black hole would decrease the total observable entropy, violating the second law",
                evidence=[
                    "Wheeler posed this thought experiment to Bekenstein circa 1971 (recounted in Bekenstein's papers)",
                ],
                confidence=0.85,
                affected_quantity="total entropy of universe",
                theories_involved=["general relativity", "thermodynamics"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Hawking's area theorem (1971) showed black hole horizon area never decreases, exactly paralleling entropy",
                evidence=[
                    "Hawking, 'Gravitational Radiation from Colliding Black Holes', Phys. Rev. Lett. 26 (1971) 1344-1346",
                ],
                confidence=0.90,
                affected_quantity="black hole horizon area",
                theories_involved=["general relativity"],
            ),
            Symptom(
                symptom_type=SymptomType.UNIVERSAL_QUANTITY,
                description="The combination A/(l_P^2) is the unique dimensionless quantity constructible from horizon area and fundamental constants",
                evidence=[
                    "Bekenstein, 'Black holes and entropy', Phys. Rev. D 7 (1973) 2333",
                ],
                confidence=0.80,
                affected_quantity="entropy formula for black holes",
                theories_involved=["general relativity", "quantum mechanics", "statistical mechanics"],
            ),
        ],
        time_stuck_years=5,
        time_to_solve_after=1,
        key_insight="The area theorem is not just analogous to the second law -- it IS the second law for black holes. Entropy is real and proportional to the horizon area in Planck units.",
        what_made_it_hard="Hawking and others initially opposed the idea. If black holes have entropy they must have temperature, implying they radiate -- which seemed impossible classically.",
        trigger="Wheeler's thought experiment about dropping a cup of tea into a black hole, challenging Bekenstein to save the second law",
    ))

    # 9. Maxwell's unification
    records.append(PremiseShiftRecord(
        field="physics",
        year=1865,
        person="James Clerk Maxwell",
        old_premise="Electricity and magnetism are separate forces; they interact but are fundamentally distinct phenomena",
        new_premise="Electricity and magnetism are aspects of a single electromagnetic field; light is an electromagnetic wave",
        premise_error_type=PremiseErrorType.FALSE_DICHOTOMY,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The ratio of electromagnetic to electrostatic units equaled the speed of light",
                evidence=[
                    "Weber & Kohlrausch measured the ratio in 1856, obtaining ~3.1 x 10^8 m/s",
                    "Maxwell noted this coincidence in 'On Physical Lines of Force' (1861)",
                ],
                confidence=0.95,
                affected_quantity="ratio of electromagnetic to electrostatic units",
                theories_involved=["electrostatics", "magnetostatics", "optics"],
            ),
            Symptom(
                symptom_type=SymptomType.DUAL_DESCRIPTION,
                description="Faraday's induction and Ampere's law were mirror images of each other but treated as separate laws",
                evidence=[
                    "Faraday, 'Experimental Researches in Electricity' (1831-1855)",
                    "Ampere, 'Memoire sur la theorie des phenomenes electrodynamiques' (1826)",
                ],
                confidence=0.85,
                affected_quantity="electromagnetic coupling",
                theories_involved=["Faraday's field theory", "Ampere's force law"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Without the displacement current, Ampere's law violated charge conservation for time-varying fields",
                evidence=[
                    "Maxwell, 'A Dynamical Theory of the Electromagnetic Field', Phil. Trans. 155 (1865) 459-512",
                ],
                confidence=0.90,
                affected_quantity="displacement current",
                theories_involved=["Ampere's law", "charge conservation"],
            ),
        ],
        time_stuck_years=34,
        time_to_solve_after=2,
        key_insight="Add a displacement current term to Ampere's law, making the equations symmetric. The resulting wave equation propagates at the speed of light -- light IS electromagnetic radiation.",
        what_made_it_hard="Faraday's intuitive field concept was not mathematical; the German action-at-a-distance school resisted fields. Maxwell needed to synthesize Faraday's physical intuition with mathematical formalism.",
        trigger="Maxwell's mechanical model of the ether (molecular vortices) predicted a displacement current; once added, the equations immediately yielded electromagnetic waves at the speed of light",
    ))

    # 10. Noether's theorem
    records.append(PremiseShiftRecord(
        field="physics/mathematics",
        year=1918,
        person="Emmy Noether",
        old_premise="Conservation laws (energy, momentum, angular momentum) are independent empirical facts; symmetries are aesthetic features of equations",
        new_premise="Every continuous symmetry of the action corresponds to a conserved quantity, and vice versa",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Conservation of energy, momentum, and angular momentum all held across every branch of physics without a unifying reason",
                evidence=[
                    "Lagrange's 'Mecanique Analytique' (1788) derived conservation laws from variational principles without explaining why",
                    "Hamilton's principle (1834) connected symmetry and dynamics but the link to conservation was not formalized",
                ],
                confidence=0.80,
                affected_quantity="conservation laws",
                theories_involved=["classical mechanics", "electrodynamics", "thermodynamics"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="In general relativity, energy conservation appeared to fail because the gravitational field itself carries energy",
                evidence=[
                    "Hilbert and Klein corresponded about the failure of standard energy conservation in GR (1916-1918)",
                    "Einstein's pseudotensor for gravitational energy was coordinate-dependent",
                ],
                confidence=0.85,
                affected_quantity="gravitational energy",
                theories_involved=["general relativity"],
            ),
        ],
        time_stuck_years=130,
        time_to_solve_after=1,
        key_insight="The connection between symmetry and conservation is not a coincidence but a theorem. For generally covariant theories (like GR), the 'conservation law' becomes an identity, explaining the apparent failure.",
        what_made_it_hard="The mathematical apparatus (variational calculus, Lie groups) was available but physicists had not connected it to conservation laws. Noether's status as a woman in 1918 Germany meant her work was initially underappreciated.",
        trigger="Hilbert and Klein asked Noether to resolve the puzzle of energy conservation in GR. She proved two theorems: one linking global symmetries to conservation laws, another showing local (gauge) symmetries yield identities.",
    ))

    # 11. Wilson's renormalization group
    records.append(PremiseShiftRecord(
        field="physics",
        year=1971,
        person="Kenneth Wilson",
        old_premise="Infinities in quantum field theory are diseases to be cured by renormalization tricks; the cutoff must be removed to get physical answers",
        new_premise="Physical theories are effective theories valid at particular scales; renormalization group flow between scales is the fundamental concept",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Perturbative QFT produced infinities at every loop order requiring systematic subtraction procedures",
                evidence=[
                    "Tomonaga (1946), Schwinger (1948), Feynman (1948) independently developed renormalization for QED",
                    "Dyson, 'The Radiation Theories of Tomonaga, Schwinger, and Feynman', Phys. Rev. 75 (1949) 486",
                ],
                confidence=0.90,
                affected_quantity="loop integrals in QFT",
                theories_involved=["quantum electrodynamics", "quantum field theory"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Critical exponents in phase transitions were universal across wildly different physical systems (fluids, magnets)",
                evidence=[
                    "Guggenheim, 'The Principle of Corresponding States', J. Chem. Phys. 13 (1945) 253",
                    "Kadanoff, 'Scaling laws for Ising models near T_c', Physics 2 (1966) 263-272",
                ],
                confidence=0.85,
                affected_quantity="critical exponents",
                theories_involved=["statistical mechanics", "condensed matter physics"],
            ),
            Symptom(
                symptom_type=SymptomType.DUAL_DESCRIPTION,
                description="Kadanoff's block-spin argument gave the right scaling but lacked a systematic computational framework",
                evidence=[
                    "Kadanoff (1966) block-spin construction",
                    "Widom, 'Equation of State in the Neighborhood of the Critical Point', J. Chem. Phys. 43 (1965) 3898",
                ],
                confidence=0.80,
                affected_quantity="block-spin transformation",
                theories_involved=["Ising model", "mean field theory"],
            ),
        ],
        time_stuck_years=23,
        time_to_solve_after=2,
        key_insight="Integrate out high-energy modes shell by shell in momentum space. The resulting flow of coupling constants explains universality (IR fixed points) and makes the cutoff physical rather than a defect.",
        what_made_it_hard="The renormalization procedure 'worked' for QED calculations, removing motivation to understand it conceptually. The connection between statistical mechanics and QFT was not obvious.",
        trigger="Wilson combined Kadanoff's block-spin idea with Gell-Mann and Low's QFT renormalization group, realizing they were the same concept applied in different domains",
    ))

    # 12. 't Hooft gauge theory renormalizability
    records.append(PremiseShiftRecord(
        field="physics",
        year=1971,
        person="Gerard 't Hooft",
        old_premise="Non-abelian gauge theories with massive vector bosons are non-renormalizable and therefore physically meaningless as quantum theories",
        new_premise="Spontaneously broken non-abelian gauge theories (with Higgs mechanism) are renormalizable and yield consistent quantum predictions",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Fermi's four-fermion theory of weak interactions was non-renormalizable, producing uncontrolled divergences at high energies",
                evidence=[
                    "Fermi, 'Tentativo di una teoria dei raggi beta', Nuovo Cimento 11 (1934) 1-19",
                    "Heisenberg noted the unitarity violation of four-fermion theory at high energies",
                ],
                confidence=0.90,
                affected_quantity="weak interaction cross-sections at high energy",
                theories_involved=["Fermi theory of weak interactions"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Massive vector boson theories seemed to require explicit mass terms that broke gauge invariance and renormalizability",
                evidence=[
                    "Yang & Mills, 'Conservation of Isotopic Spin and Isotopic Gauge Invariance', Phys. Rev. 96 (1954) 191",
                    "Feynman and others struggled with quantizing massive Yang-Mills theories in the 1960s",
                ],
                confidence=0.85,
                affected_quantity="renormalizability of massive gauge theories",
                theories_involved=["Yang-Mills theory", "electroweak models"],
            ),
        ],
        time_stuck_years=17,
        time_to_solve_after=1,
        key_insight="If vector boson masses arise from spontaneous symmetry breaking (Higgs mechanism), the underlying gauge invariance is preserved and the theory is renormalizable. Use dimensional regularization to prove it.",
        what_made_it_hard="The Higgs mechanism was known (1964) but not connected to renormalizability. The technical proof required new regularization methods. Veltman had been working on it for years without the crucial insight.",
        trigger="'t Hooft, as Veltman's graduate student, combined Veltman's computational approach with the Higgs mechanism and developed dimensional regularization to complete the proof",
    ))

    # 13. Electroweak unification
    records.append(PremiseShiftRecord(
        field="physics",
        year=1967,
        person="Steven Weinberg, Abdus Salam",
        old_premise="The weak nuclear force and electromagnetism are completely separate interactions with different properties (range, parity violation)",
        new_premise="Electromagnetism and the weak force are low-energy manifestations of a single SU(2)xU(1) gauge theory, broken by the Higgs mechanism",
        premise_error_type=PremiseErrorType.FALSE_DICHOTOMY,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="The weak force had a very short range (massive mediators) while electromagnetism was long-range (massless photon), yet both coupled to leptons",
                evidence=[
                    "Fermi theory required a dimensional coupling constant G_F suggesting heavy mediators",
                    "Lee & Yang, 'Question of Parity Conservation in Weak Interactions', Phys. Rev. 104 (1956) 254",
                ],
                confidence=0.80,
                affected_quantity="weak boson masses / coupling",
                theories_involved=["Fermi weak theory", "QED"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Parity violation in weak interactions seemed to make unification with the parity-conserving electromagnetic force impossible",
                evidence=[
                    "Wu et al., 'Experimental Test of Parity Conservation in Beta Decay', Phys. Rev. 105 (1957) 1413",
                ],
                confidence=0.80,
                affected_quantity="parity symmetry",
                theories_involved=["weak interactions", "electromagnetism"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The electromagnetic and weak coupling constants were of similar magnitude when extrapolated to high energies",
                evidence=[
                    "This was recognized gradually through the 1960s as gauge theory structures were explored",
                ],
                confidence=0.70,
                affected_quantity="coupling constant values at high energy",
                theories_involved=["QED", "weak interaction theory"],
            ),
        ],
        time_stuck_years=11,
        time_to_solve_after=4,
        key_insight="Assign left-handed and right-handed fermions to different SU(2) representations. Spontaneous symmetry breaking via the Higgs gives W and Z bosons mass while keeping the photon massless.",
        what_made_it_hard="Parity violation seemed to rule out unification with a parity-conserving force. The renormalizability of the theory was not proven until 't Hooft (1971), so few took it seriously.",
        trigger="Weinberg applying the Higgs mechanism to Glashow's SU(2)xU(1) model for leptons, realizing it could give W/Z masses while keeping the photon massless",
    ))

    # 14. Quarks
    records.append(PremiseShiftRecord(
        field="physics",
        year=1964,
        person="Murray Gell-Mann, George Zweig",
        old_premise="Hadrons (protons, neutrons, pions, etc.) are fundamental particles; the growing 'particle zoo' contains independent entities",
        new_premise="Hadrons are composites of fractionally charged quarks; the particle zoo reflects the combinatorics of a few fundamental constituents",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.PROLIFERATION_WITHOUT_SELECTION,
                description="Over 100 'fundamental' hadrons discovered by the early 1960s with no organizing principle besides quantum numbers",
                evidence=[
                    "The Particle Data Group listings grew rapidly through the 1950s and 1960s",
                    "The 'hadron zoo' was a widely acknowledged crisis in particle physics",
                ],
                confidence=0.90,
                affected_quantity="number of hadron species",
                theories_involved=["strong interaction physics"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Hadrons fell into exact SU(3) flavor multiplets (octets, decuplets) with mass splittings following a simple pattern",
                evidence=[
                    "Gell-Mann, 'The Eightfold Way' (1961), Caltech Report CTSL-20",
                    "Ne'eman, 'Derivation of Strong Interactions from a Gauge Invariance', Nuclear Physics 26 (1961) 222",
                    "Prediction and discovery of the Omega-minus baryon (1964) confirmed the decuplet",
                ],
                confidence=0.95,
                affected_quantity="hadron mass spectrum and quantum numbers",
                theories_involved=["SU(3) flavor symmetry"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="No free quarks were observed despite extensive searches, creating doubt about their physical reality",
                evidence=[
                    "Searches at accelerators throughout the 1960s found no fractional charges",
                    "This led to the 'quark confinement' problem",
                ],
                confidence=0.70,
                affected_quantity="free quark cross-section",
                theories_involved=["quark model"],
            ),
        ],
        time_stuck_years=10,
        time_to_solve_after=5,
        key_insight="The SU(3) multiplets are representations built from a fundamental triplet. Hadrons are composites: mesons are quark-antiquark, baryons are three quarks.",
        what_made_it_hard="Fractional electric charges had never been observed. Quarks were confined and never seen free, leading many (including Gell-Mann initially) to treat them as mathematical devices rather than physical particles.",
        trigger="The success of SU(3) classification (Eightfold Way) and particularly the Omega-minus prediction made clear that the fundamental representation (quarks) had physical significance",
    ))

    # 15. Expanding universe
    records.append(PremiseShiftRecord(
        field="physics/cosmology",
        year=1929,
        person="Edwin Hubble (and Georges Lemaitre 1927)",
        old_premise="The universe is static and eternal; it has always existed in roughly its present form",
        new_premise="The universe is expanding; galaxies recede from each other with velocity proportional to distance",
        premise_error_type=PremiseErrorType.UNNECESSARY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Einstein added the cosmological constant Lambda to prevent gravitational collapse in a static universe",
                evidence=[
                    "Einstein, 'Kosmologische Betrachtungen zur allgemeinen Relativitatstheorie', Sitzungsberichte der Preuss. Akad. Wiss. (1917) 142-152",
                ],
                confidence=0.90,
                affected_quantity="cosmological constant",
                theories_involved=["general relativity"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Slipher's redshift measurements (1912-1925) showed most nebulae receding, with a distance-dependent pattern",
                evidence=[
                    "Slipher, 'The radial velocity of the Andromeda Nebula', Lowell Observatory Bulletin 2 (1913) 56-57",
                    "By 1925, Slipher had measured ~45 nebular redshifts, mostly recessional",
                ],
                confidence=0.85,
                affected_quantity="nebular radial velocities",
                theories_involved=["observational astronomy"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Friedmann and Lemaitre independently found that GR naturally predicts expansion or contraction, not a static universe",
                evidence=[
                    "Friedmann, 'Uber die Krummung des Raumes', Zeitschrift fur Physik 10 (1922) 377-386",
                    "Lemaitre, 'Un Univers homogene de masse constante et de rayon croissant', Annales de la Societe Scientifique de Bruxelles 47 (1927) 49-59",
                ],
                confidence=0.90,
                affected_quantity="cosmic scale factor",
                theories_involved=["general relativity", "cosmology"],
            ),
        ],
        time_stuck_years=12,
        time_to_solve_after=2,
        key_insight="The universe is not static. GR without the cosmological constant naturally predicts expansion, consistent with observed redshifts. The static universe was an unnecessary assumption.",
        what_made_it_hard="The static universe was a deeply held philosophical assumption shared by Einstein and nearly all physicists and astronomers. Einstein's authority reinforced the prejudice.",
        trigger="Hubble's systematic measurements of Cepheid distances to galaxies combined with Slipher's redshifts, establishing the linear velocity-distance relation (1929)",
    ))

    # =========================================================================
    # MATHEMATICS
    # =========================================================================

    # 16. Poincare conjecture (Perelman)
    records.append(PremiseShiftRecord(
        field="mathematics",
        year=2003,
        person="Grigori Perelman",
        old_premise="The Poincare conjecture should be attacked via topological methods directly; singularities in Ricci flow are obstacles to be avoided",
        new_premise="Singularities in Ricci flow are not obstacles but carry classifiable information; surgery on singularities yields the proof",
        premise_error_type=PremiseErrorType.INVERTED_CAUSATION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Hamilton's Ricci flow program (from 1982) stalled on classifying and handling singularities that form in finite time",
                evidence=[
                    "Hamilton, 'Three-manifolds with positive Ricci curvature', J. Differential Geometry 17 (1982) 255-306",
                    "Hamilton, 'Formation of singularities in the Ricci flow', Surveys in Differential Geometry 2 (1995) 7-136",
                ],
                confidence=0.90,
                affected_quantity="Ricci flow singularity classification",
                theories_involved=["Ricci flow", "3-manifold topology"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Many partial results over decades attacked special cases (e.g., simply connected, positive curvature) without reaching the general case",
                evidence=[
                    "Smale proved the generalized Poincare conjecture for dimensions >= 5 (1961)",
                    "Freedman proved it for dimension 4 (1982)",
                    "Dimension 3 remained open for a century despite being the original conjecture",
                ],
                confidence=0.85,
                affected_quantity="topological classification in dimension 3",
                theories_involved=["algebraic topology", "geometric topology"],
            ),
        ],
        time_stuck_years=99,
        time_to_solve_after=3,
        key_insight="Classify all possible singularities of Ricci flow (they are essentially round cylinders or their quotients), then perform surgery to cut them out and restart the flow. This yields the full geometrization.",
        what_made_it_hard="The singularity analysis required deep new estimates (no-local-collapsing theorem via Perelman's W-entropy). The combination of analysis, geometry, and topology was beyond most specialists in any one field.",
        trigger="Perelman's introduction of the W-entropy functional and L-length, which provided the missing monotonicity and compactness results for Ricci flow",
    ))

    # 17. Galois theory
    records.append(PremiseShiftRecord(
        field="mathematics",
        year=1832,
        person="Evariste Galois",
        old_premise="Solving polynomial equations means finding explicit radical formulas; the goal is to find the formula for degree 5+",
        new_premise="Study the symmetry group of the roots; solvability by radicals corresponds to solvability of the group",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Three centuries of attempts to find a quintic formula by generalizing the quadratic/cubic/quartic methods failed",
                evidence=[
                    "Cardano's formula for cubics (1545), Ferrari's for quartics (1545), but no progress on degree 5",
                    "Ruffini (1799) and Abel (1824) proved impossibility of a general quintic formula",
                ],
                confidence=0.95,
                affected_quantity="radical solution of quintic equations",
                theories_involved=["algebra"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Some specific quintic equations were solvable while the general one was not, with no explanation of what distinguished them",
                evidence=[
                    "Abel proved impossibility of the general case but could not characterize which specific equations were solvable",
                ],
                confidence=0.85,
                affected_quantity="solvability of specific polynomial equations",
                theories_involved=["algebra"],
            ),
        ],
        time_stuck_years=280,
        time_to_solve_after=1,
        key_insight="The right question is not 'what is the formula?' but 'what symmetries do the roots have?' A polynomial is solvable by radicals if and only if its Galois group is solvable.",
        what_made_it_hard="The concept of a group did not exist. Galois had to invent the theory of groups, normal subgroups, and quotient groups to even state the theorem. He died at 20 and his work was neglected for over a decade.",
        trigger="Galois sought to understand why Abel's impossibility result held and what distinguished solvable from unsolvable equations, leading him to study permutations of roots",
    ))

    # 18. Cantor's set theory / sizes of infinity
    records.append(PremiseShiftRecord(
        field="mathematics",
        year=1874,
        person="Georg Cantor",
        old_premise="Infinity is a single concept; all infinite collections are the same size; actual infinity should be avoided in favor of potential infinity",
        new_premise="There are different sizes of infinity (cardinalities); the reals are uncountable and strictly larger than the naturals",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The rationals are countable (same size as naturals) despite being dense, while the reals seem 'larger' without any rigorous way to say so",
                evidence=[
                    "Cantor's 1873 correspondence with Dedekind, where he first posed the question",
                ],
                confidence=0.85,
                affected_quantity="cardinality of number sets",
                theories_involved=["analysis", "number theory"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Foundational questions about the nature of real numbers and continuity could not be resolved without a rigorous theory of infinite sets",
                evidence=[
                    "Dedekind's 'Stetigkeit und irrationale Zahlen' (1872) constructed the reals via cuts but raised cardinality questions",
                    "Bolzano's 'Paradoxien des Unendlichen' (1851) catalogued paradoxes of infinity",
                ],
                confidence=0.80,
                affected_quantity="foundations of analysis",
                theories_involved=["real analysis"],
            ),
        ],
        time_stuck_years=200,
        time_to_solve_after=5,
        key_insight="Use bijections to compare sizes of infinite sets. The diagonal argument shows no surjection from naturals to reals exists, so the reals are a strictly larger infinity.",
        what_made_it_hard="The idea of 'different sizes of infinity' was philosophically shocking. Kronecker, Poincare, and others vigorously opposed it. Cantor suffered severe opposition and depression.",
        trigger="Cantor's work on uniqueness of trigonometric series representations led him to study point sets and their cardinalities",
    ))

    # 19. Godel's incompleteness theorems
    records.append(PremiseShiftRecord(
        field="mathematics/logic",
        year=1931,
        person="Kurt Godel",
        old_premise="A sufficiently powerful consistent formal system can prove all true statements within its domain (Hilbert's program: mathematics can be completely formalized)",
        new_premise="Any consistent formal system containing arithmetic has true statements that are unprovable within it; consistency cannot be proved internally",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Russell's paradox and other set-theoretic antinomies showed naive formalization leads to contradictions",
                evidence=[
                    "Russell's paradox (1901) in Frege's system",
                    "Russell & Whitehead's 'Principia Mathematica' (1910-1913) attempted to fix this with type theory, at great complexity cost",
                ],
                confidence=0.85,
                affected_quantity="consistency of formal systems",
                theories_involved=["set theory", "formal logic"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Attempts to formalize all of mathematics required increasingly elaborate axiom systems with no guarantee of completeness",
                evidence=[
                    "Zermelo's axiomatization of set theory (1908) and its extensions",
                    "Hilbert's program (1920s) sought a finitary consistency proof that was never achieved",
                ],
                confidence=0.80,
                affected_quantity="axiom system complexity",
                theories_involved=["formal logic", "proof theory"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The liar paradox and Richard's paradox had structural similarities to formal undecidability but the connection was unclear",
                evidence=[
                    "Richard's paradox (1905) about definability of real numbers",
                    "The liar paradox has ancient roots but was not connected to formal systems until Godel",
                ],
                confidence=0.75,
                affected_quantity="self-referential statements",
                theories_involved=["logic", "philosophy"],
            ),
        ],
        time_stuck_years=30,
        time_to_solve_after=1,
        key_insight="Encode the syntax of a formal system within its own arithmetic (Godel numbering). Construct a sentence that says 'I am not provable in this system.' If consistent, this sentence is true but unprovable.",
        what_made_it_hard="Hilbert's program was enormously prestigious. The idea that mathematics has inherent limitations was psychologically and philosophically difficult to accept. The proof required the novel technique of arithmetization of syntax.",
        trigger="Godel attended a conference in Konigsberg (1930) where the completeness and consistency of formal systems was discussed, and realized self-reference could be formalized",
    ))

    # 20. Grothendieck's algebraic geometry
    records.append(PremiseShiftRecord(
        field="mathematics",
        year=1960,
        person="Alexander Grothendieck",
        old_premise="Algebraic geometry studies geometric objects (varieties) defined by polynomial equations over specific fields",
        new_premise="Algebraic geometry studies schemes: geometric objects defined over arbitrary commutative rings, with the structure sheaf as the fundamental object",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Weil's conjectures (1949) about zeta functions of varieties over finite fields could not be proved with existing algebraic geometry",
                evidence=[
                    "Weil, 'Numbers of solutions of equations in finite fields', Bull. AMS 55 (1949) 497-508",
                    "Weil's conjectures required a cohomology theory for varieties over finite fields that did not exist",
                ],
                confidence=0.90,
                affected_quantity="zeta function of varieties over finite fields",
                theories_involved=["algebraic geometry", "number theory"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Italian algebraic geometry had deep geometric intuition but lacked rigorous foundations; proofs often had gaps",
                evidence=[
                    "Zariski's 'Algebraic Surfaces' (1935) catalogued results of the Italian school and noted many unproved claims",
                    "The foundations crisis in algebraic geometry was widely acknowledged by the 1940s",
                ],
                confidence=0.85,
                affected_quantity="rigor of algebraic geometry proofs",
                theories_involved=["classical algebraic geometry"],
            ),
            Symptom(
                symptom_type=SymptomType.DUAL_DESCRIPTION,
                description="Algebraic geometry over different base fields (reals, complex, finite fields) used different techniques for essentially parallel theories",
                evidence=[
                    "Serre, 'Faisceaux Algebriques Coherents' (1955) began unifying with sheaf theory",
                    "The analogy between number fields and function fields was powerful but not formalized",
                ],
                confidence=0.80,
                affected_quantity="algebraic geometry over varying base fields",
                theories_involved=["algebraic geometry over C", "algebraic geometry over finite fields", "number theory"],
            ),
        ],
        time_stuck_years=11,
        time_to_solve_after=10,
        key_insight="Replace varieties with schemes (locally ringed spaces built from Spec of arbitrary rings). This unifies geometry over all base rings, provides the right cohomology theory (etale), and makes the Weil conjectures approachable.",
        what_made_it_hard="The level of abstraction was unprecedented. Grothendieck's approach required building an entirely new foundation (EGA/SGA totaling thousands of pages). Many mathematicians resisted the abstraction.",
        trigger="Grothendieck's realization that Serre's sheaf-theoretic methods in algebraic geometry needed to be taken further: the base field should be replaced by an arbitrary ring, and geometry should be built from algebra",
    ))

    # =========================================================================
    # OTHER SCIENCES
    # =========================================================================

    # 21. Information theory (Shannon)
    records.append(PremiseShiftRecord(
        field="electrical engineering/mathematics",
        year=1948,
        person="Claude Shannon",
        old_premise="Communication requires preserving the meaning of messages; noise sets a practical limit on reliable communication",
        new_premise="Information is a measurable quantity independent of meaning; channel capacity sets a sharp theoretical limit, and reliable communication up to that limit is achievable",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Engineers knew noise limited communication but had no theoretical framework for the maximum achievable rate",
                evidence=[
                    "Nyquist, 'Certain Topics in Telegraph Transmission Theory', Trans. AIEE 47 (1928) 617-644",
                    "Hartley, 'Transmission of Information', Bell System Technical Journal 7 (1928) 535-563",
                ],
                confidence=0.85,
                affected_quantity="channel capacity",
                theories_involved=["communication engineering"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Error correction was done ad-hoc with no theoretical basis for how much redundancy was needed or optimal",
                evidence=[
                    "Practical telegraphy and telephony used repetition and analog noise reduction without optimality theory",
                ],
                confidence=0.80,
                affected_quantity="error correction efficiency",
                theories_involved=["communication engineering"],
            ),
        ],
        time_stuck_years=20,
        time_to_solve_after=1,
        key_insight="Drop semantics entirely. Measure information as entropy (bits). A channel has a definite capacity C, and error-free communication at any rate below C is possible with appropriate coding. Above C, it is not.",
        what_made_it_hard="The idea that meaning is irrelevant to a theory of communication was deeply counterintuitive. The existence theorem for good codes was non-constructive, so it took decades to find practical codes approaching capacity.",
        trigger="Shannon's wartime work on cryptography at Bell Labs, where he realized that the mathematical structure of secrecy systems and communication systems were closely related",
    ))

    # 22. Evolution by natural selection
    records.append(PremiseShiftRecord(
        field="biology",
        year=1859,
        person="Charles Darwin (and Alfred Russel Wallace)",
        old_premise="Species are fixed and separately created; each species has an unchanging essence (typological thinking)",
        new_premise="Species change over time through heritable variation and natural selection; all life shares common descent",
        premise_error_type=PremiseErrorType.UNNECESSARY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Homologous structures (e.g., vertebrate limb bones) across unrelated species suggested shared origin",
                evidence=[
                    "Owen, 'On the Archetype and Homologies of the Vertebrate Skeleton' (1848)",
                    "Comparative anatomy tradition from Cuvier through Owen",
                ],
                confidence=0.85,
                affected_quantity="structural similarity across species",
                theories_involved=["comparative anatomy", "natural theology"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="The fossil record showed systematic progression from simple to complex organisms, with extinct forms intermediate between living groups",
                evidence=[
                    "Cuvier's studies of fossil mammals in the Paris basin (1796-1812)",
                    "Lyell's 'Principles of Geology' (1830-1833) established deep time",
                ],
                confidence=0.85,
                affected_quantity="fossil succession patterns",
                theories_involved=["paleontology", "geology", "special creation"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Biogeographic patterns: island species resembled nearby mainland species rather than species on ecologically similar but distant islands",
                evidence=[
                    "Darwin's observations on Galapagos finches and other island fauna (1835-1836)",
                    "Wallace's observations in the Malay Archipelago (1854-1862)",
                ],
                confidence=0.90,
                affected_quantity="geographic distribution of species",
                theories_involved=["biogeography", "special creation"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Separate creation required ad-hoc explanations for vestigial organs, embryological similarities, and classification hierarchy",
                evidence=[
                    "Darwin devoted chapters of 'Origin' to these patterns as evidence against special creation",
                ],
                confidence=0.80,
                affected_quantity="vestigial organs and embryological recapitulation",
                theories_involved=["natural theology", "comparative anatomy"],
            ),
        ],
        time_stuck_years=50,
        time_to_solve_after=1,
        key_insight="Species are not fixed types. Heritable variation + differential survival + vast time = transformation of species. No designer needed; the algorithm of selection explains adaptation.",
        what_made_it_hard="Religious and cultural commitment to special creation. The mechanism of heredity was unknown (pre-Mendel). The timescales involved were beyond intuition. Lord Kelvin's (wrong) estimate of Earth's age seemed too short.",
        trigger="Darwin's 5-year Beagle voyage (1831-1836), particularly Galapagos observations, followed by reading Malthus on population (1838) which suggested the selective mechanism",
    ))

    # 23. Plate tectonics
    records.append(PremiseShiftRecord(
        field="geology",
        year=1965,
        person="Alfred Wegener (1912), Harry Hess, J. Tuzo Wilson (1960s)",
        old_premise="Continents are fixed in position on the Earth's surface; vertical motion (subsidence, uplift) dominates",
        new_premise="The Earth's surface consists of rigid plates that move laterally; continents drift, ocean floors spread, and plates subduct",
        premise_error_type=PremiseErrorType.IMPLICIT_BACKGROUND,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The coastlines of Africa and South America fit together like jigsaw pieces, including matching geological formations and fossils",
                evidence=[
                    "Wegener, 'Die Entstehung der Kontinente und Ozeane' (1915)",
                    "du Toit, 'Our Wandering Continents' (1937) documented fossil and geological matches",
                ],
                confidence=0.90,
                affected_quantity="continental coastline geometry",
                theories_involved=["fixist geology", "continental drift"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Identical fossil species (Glossopteris, Mesosaurus) found on continents separated by vast oceans",
                evidence=[
                    "Glossopteris flora across South America, Africa, India, Antarctica, Australia",
                    "Mesosaurus found only in South America and southern Africa",
                ],
                confidence=0.95,
                affected_quantity="paleobiogeographic distribution",
                theories_involved=["paleontology", "biogeography"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="'Land bridges' between continents were postulated to explain fossil distributions, then conveniently sunk without trace",
                evidence=[
                    "Multiple hypothetical land bridges were proposed and widely accepted through the early 20th century",
                ],
                confidence=0.85,
                affected_quantity="hypothetical land bridges",
                theories_involved=["fixist geology"],
            ),
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Paleomagnetic studies showed rocks of the same age on different continents had different magnetic pole positions, consistent with drift",
                evidence=[
                    "Runcorn, 'Palaeomagnetic comparisons between Europe and North America', Proc. Geol. Assoc. Canada 8 (1956) 77-85",
                    "Irving, 'Palaeomagnetic and palaeoclimatological aspects of polar wandering', Geofisica Pura e Applicata 33 (1956) 23-41",
                ],
                confidence=0.85,
                affected_quantity="paleomagnetic pole positions",
                theories_involved=["paleomagnetism", "fixist geology"],
            ),
        ],
        time_stuck_years=53,
        time_to_solve_after=5,
        key_insight="The continents are not fixed on a static Earth. They ride on rigid lithospheric plates that move over the asthenosphere, driven by mantle convection and created/destroyed at mid-ocean ridges and subduction zones.",
        what_made_it_hard="Wegener had no mechanism for continental drift. The geological establishment (especially in the US and UK) rejected drift for 50 years. The key evidence (seafloor spreading, magnetic striping) required ocean-floor data that only became available in the 1950s-60s.",
        trigger="Hess's seafloor spreading hypothesis (1962), Vine-Matthews magnetic striping on the ocean floor (1963), and Wilson's transform faults (1965) provided the mechanism and definitive evidence",
    ))

    # 24. Statistical mechanics (Boltzmann)
    records.append(PremiseShiftRecord(
        field="physics",
        year=1877,
        person="Ludwig Boltzmann",
        old_premise="Thermodynamics is a fundamental theory of continuous fluids; entropy is a primary quantity not derivable from mechanics",
        new_premise="Thermodynamic quantities are statistical averages over microscopic states; S = k_B * ln(W)",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="The second law of thermodynamics (entropy increase) had no mechanical explanation; it appeared as an independent postulate",
                evidence=[
                    "Clausius introduced entropy as a state function (1865) without microscopic derivation",
                    "Thomson (Lord Kelvin) formulated the second law independently (1851)",
                ],
                confidence=0.85,
                affected_quantity="entropy",
                theories_involved=["thermodynamics", "classical mechanics"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Classical mechanics is time-reversible but thermodynamics has a preferred direction of time (entropy increase)",
                evidence=[
                    "Loschmidt's reversibility paradox (1876)",
                    "Zermelo's recurrence paradox based on Poincare's recurrence theorem (1896)",
                ],
                confidence=0.90,
                affected_quantity="time-reversal symmetry vs irreversibility",
                theories_involved=["Newtonian mechanics", "thermodynamics"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The ideal gas law PV=NkT connected macroscopic observables to a count of particles with no deeper explanation",
                evidence=[
                    "Avogadro's hypothesis (1811) on equal volumes containing equal numbers of molecules",
                    "Clausius kinetic theory (1857) began connecting gas properties to molecular motion",
                ],
                confidence=0.75,
                affected_quantity="ideal gas constant / Boltzmann constant",
                theories_involved=["thermodynamics", "kinetic theory"],
            ),
        ],
        time_stuck_years=30,
        time_to_solve_after=5,
        key_insight="Entropy is the logarithm of the number of microstates consistent with a macrostate. The second law is not absolute but overwhelmingly probable. Irreversibility emerges from statistics, not fundamental law.",
        what_made_it_hard="Many physicists (Mach, Ostwald) denied the existence of atoms. The reversibility and recurrence objections seemed devastating. Boltzmann's probabilistic interpretation of a supposedly absolute law was radical.",
        trigger="Boltzmann's study of the H-theorem (1872) and the subsequent objections by Loschmidt forced him to reformulate entropy in terms of probability (1877): S = k log W",
    ))

    # 25. DNA structure
    records.append(PremiseShiftRecord(
        field="biology/chemistry",
        year=1953,
        person="James Watson, Francis Crick (with key data from Rosalind Franklin and Maurice Wilkins)",
        old_premise="Proteins are the carriers of genetic information (due to their complexity); DNA is too simple (a 'stupid molecule') to encode heredity",
        new_premise="DNA carries genetic information in its base sequence; the double helix structure immediately suggests the copying mechanism",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Chargaff's rules: in any DNA sample, adenine equals thymine and guanine equals cytosine, with no explanation from protein-centric models",
                evidence=[
                    "Chargaff, 'Chemical specificity of nucleic acids and mechanism of their enzymatic degradation', Experientia 6 (1950) 201-209",
                ],
                confidence=0.90,
                affected_quantity="base pair ratios in DNA",
                theories_involved=["biochemistry"],
            ),
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Avery-MacLeod-McCarty experiment (1944) showed DNA, not protein, was the transforming principle, but was widely doubted",
                evidence=[
                    "Avery, MacLeod & McCarty, 'Studies on the Chemical Nature of the Substance Inducing Transformation of Pneumococcal Types', J. Exp. Med. 79 (1944) 137-158",
                ],
                confidence=0.85,
                affected_quantity="identity of genetic material",
                theories_involved=["genetics", "biochemistry"],
            ),
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Hershey-Chase experiment (1952) confirmed DNA, not protein, carries genetic information in bacteriophages",
                evidence=[
                    "Hershey & Chase, 'Independent Functions of Viral Protein and Nucleic Acid in Growth of Bacteriophage', J. Gen. Physiology 36 (1952) 39-56",
                ],
                confidence=0.90,
                affected_quantity="identity of genetic material",
                theories_involved=["genetics", "virology"],
            ),
        ],
        time_stuck_years=9,
        time_to_solve_after=1,
        key_insight="DNA is a double helix with complementary base pairing (A-T, G-C). The structure immediately suggests how DNA replicates: the two strands separate and each templates a new complementary strand.",
        what_made_it_hard="The protein paradigm was deeply entrenched. DNA seemed too chemically simple with only 4 bases vs 20 amino acids. Franklin's X-ray data was crucial but its interpretation was disputed.",
        trigger="Watson and Crick's model-building approach, informed by Franklin's X-ray Photo 51 (showing helical B-form DNA) and Chargaff's base-pairing rules",
    ))

    # =========================================================================
    # FAILED SHIFTS (succeeded=False)
    # =========================================================================

    # 26. Lorentz ether theory
    records.append(PremiseShiftRecord(
        field="physics",
        year=1904,
        person="Hendrik Lorentz",
        old_premise="The ether exists but is undetectable due to length contraction and local time effects on moving bodies",
        new_premise="Retain the ether but add compensating effects (contraction, local time) to explain every null result",
        premise_error_type=PremiseErrorType.UNNECESSARY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Michelson-Morley and subsequent experiments consistently found no ether drift",
                evidence=[
                    "Michelson & Morley (1887)",
                    "Trouton-Noble experiment (1903) found no torque from ether wind on a charged capacitor",
                ],
                confidence=0.95,
                affected_quantity="ether wind velocity",
                theories_involved=["ether theory", "electrodynamics"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Each null result required a new compensating hypothesis: contraction, local time, velocity-dependent mass",
                evidence=[
                    "FitzGerald contraction (1889), Lorentz local time (1895), full Lorentz transformations (1904)",
                ],
                confidence=0.90,
                affected_quantity="ether compensating mechanisms",
                theories_involved=["Lorentz ether theory"],
            ),
        ],
        time_stuck_years=18,
        time_to_solve_after=0,
        key_insight="Lorentz found the right mathematical transformations but for the wrong reason. The ether was unnecessary. Einstein's SR derived the same transformations from two postulates without any ether.",
        what_made_it_hard="Lorentz's theory was empirically equivalent to special relativity. The difference was conceptual: Lorentz kept the ether as an undetectable background. It required Einstein's philosophical boldness to discard it.",
        trigger="The theory was superseded by Einstein's SR (1905), which derived the same results more simply from first principles",
        succeeded=False,
    ))

    # 27. Steady state cosmology
    records.append(PremiseShiftRecord(
        field="cosmology",
        year=1948,
        person="Fred Hoyle, Hermann Bondi, Thomas Gold",
        old_premise="The universe is expanding but has always looked the same on large scales; matter is continuously created to maintain constant density",
        new_premise="Continuous matter creation preserves the cosmological principle in time (perfect cosmological principle)",
        premise_error_type=PremiseErrorType.UNNECESSARY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Hubble's expansion implied a beginning (Big Bang), which seemed philosophically troubling to many",
                evidence=[
                    "Hubble's velocity-distance relation (1929)",
                    "Lemaitre's 'primeval atom' hypothesis (1931)",
                ],
                confidence=0.80,
                affected_quantity="age of the universe",
                theories_involved=["Big Bang cosmology"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Early Hubble constant estimates gave an age younger than the Earth, creating an apparent contradiction",
                evidence=[
                    "Hubble's original H_0 ~ 500 km/s/Mpc implied age ~ 2 billion years, less than geological estimates of Earth's age",
                ],
                confidence=0.85,
                affected_quantity="Hubble constant / age of universe",
                theories_involved=["Big Bang cosmology", "geology"],
            ),
        ],
        time_stuck_years=16,
        time_to_solve_after=0,
        key_insight="The steady state model correctly identified a problem (the age crisis) but proposed the wrong solution (continuous creation). The real fix was a revised Hubble constant (Baade 1952) and Big Bang nucleosynthesis.",
        what_made_it_hard="The steady state model was aesthetically appealing and the age discrepancy was a real problem with 1940s data. Hoyle was a brilliant advocate. It took the discovery of the CMB (1965) to decisively refute it.",
        trigger="Penzias and Wilson's discovery of the cosmic microwave background (1965) matched Big Bang predictions and had no natural explanation in steady state",
        succeeded=False,
    ))

    # 28. S-matrix theory (bootstrap)
    records.append(PremiseShiftRecord(
        field="physics",
        year=1960,
        person="Geoffrey Chew",
        old_premise="Abandon quantum field theory for strong interactions; derive everything from consistency conditions on the S-matrix (analyticity, unitarity, crossing symmetry) without fundamental fields",
        new_premise="No particle is fundamental; each is a bound state of the others (nuclear democracy / bootstrap)",
        premise_error_type=PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Perturbative QFT could not handle strong interactions because the coupling constant was large (g >> 1)",
                evidence=[
                    "Dyson (1952) showed the perturbation series for QED diverges",
                    "Strong coupling meant standard Feynman diagram methods were useless for hadronic physics",
                ],
                confidence=0.85,
                affected_quantity="strong interaction coupling",
                theories_involved=["quantum field theory"],
            ),
            Symptom(
                symptom_type=SymptomType.PROLIFERATION_WITHOUT_SELECTION,
                description="The hadron zoo had no clear fundamental constituents, making 'nuclear democracy' plausible",
                evidence=[
                    "Chew, 'S-Matrix Theory of Strong Interactions' (1961)",
                    "Regge trajectories organized hadrons by spin and mass^2 in linear relationships",
                ],
                confidence=0.80,
                affected_quantity="hadron spectrum",
                theories_involved=["S-matrix theory", "Regge theory"],
            ),
        ],
        time_stuck_years=10,
        time_to_solve_after=0,
        key_insight="The bootstrap program correctly identified that QFT perturbation theory was inadequate for strong interactions, and some S-matrix ideas (duality, Regge theory) seeded string theory. But the actual solution was QCD -- a non-abelian gauge QFT solved non-perturbatively.",
        what_made_it_hard="The bootstrap was partially right: Regge trajectories and duality (Veneziano amplitude) were real features. But it threw out too much by abandoning fields entirely. Asymptotic freedom (1973) showed QFT worked after all.",
        trigger="Discovery of asymptotic freedom by Gross, Wilczek, and Politzer (1973) rehabilitated QFT for strong interactions as QCD",
        succeeded=False,
    ))

    # 29. Phlogiston theory
    records.append(PremiseShiftRecord(
        field="chemistry",
        year=1667,
        person="Johann Joachim Becher, Georg Ernst Stahl",
        old_premise="Combustion involves the release of a fire-element (phlogiston) from the burning substance; metals are calx + phlogiston",
        new_premise="Phlogiston explains combustion as loss of a substance from the burning material",
        premise_error_type=PremiseErrorType.INVERTED_CAUSATION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Calxes (metal oxides) weighed MORE than the original metal, opposite to what phlogiston loss predicted",
                evidence=[
                    "Jean Rey noted the weight gain of tin calx as early as 1630",
                    "Lavoisier's precise measurements (1772-1774) confirmed weight gain in combustion",
                ],
                confidence=0.90,
                affected_quantity="mass change during combustion",
                theories_involved=["phlogiston theory"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Phlogiston was assigned negative weight (or 'levity') to explain mass increase during calcination",
                evidence=[
                    "Guyton de Morveau proposed negative-weight phlogiston (1772)",
                    "Some versions had phlogiston as an imponderable fluid",
                ],
                confidence=0.85,
                affected_quantity="phlogiston weight",
                theories_involved=["phlogiston theory"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Different gases (oxygen, nitrogen, hydrogen, CO2) were all confused as variations of 'phlogisticated' or 'dephlogisticated' air",
                evidence=[
                    "Priestley called oxygen 'dephlogisticated air' (1774)",
                    "Cavendish, Scheele, and Priestley discovered distinct gases but interpreted them in phlogiston terms",
                ],
                confidence=0.85,
                affected_quantity="identity of gaseous elements",
                theories_involved=["phlogiston theory", "pneumatic chemistry"],
            ),
        ],
        time_stuck_years=107,
        time_to_solve_after=15,
        key_insight="Combustion is not loss of phlogiston but GAIN of oxygen. The causation is inverted: the burning substance combines with a component of air rather than releasing an internal principle.",
        what_made_it_hard="Phlogiston theory explained qualitative features of combustion (flames, heat) intuitively. Quantitative precision in chemistry was not standard until Lavoisier. The theory was flexible enough to accommodate many observations.",
        trigger="Lavoisier's careful gravimetric experiments (1772-1789) showing that combustion and calcination involved combination with a specific gas (oxygen), with precise mass balance",
        succeeded=False,
    ))

    # 30. Caloric theory of heat
    records.append(PremiseShiftRecord(
        field="physics/chemistry",
        year=1783,
        person="Antoine Lavoisier (formalized by various 18th-century scientists)",
        old_premise="Heat is an indestructible, self-repulsive fluid (caloric) that flows from hot to cold bodies; it is conserved in all processes",
        new_premise="Caloric is a conserved substance that explains heat transfer and gas behavior",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Count Rumford's cannon-boring experiments (1798) showed apparently unlimited heat generation from friction, inconsistent with a conserved fluid",
                evidence=[
                    "Rumford, 'An Inquiry Concerning the Source of the Heat Which Is Excited by Friction', Phil. Trans. 88 (1798) 80-102",
                ],
                confidence=0.90,
                affected_quantity="heat generated by friction",
                theories_involved=["caloric theory"],
            ),
            Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description="Joule's experiments (1840s) showed precise equivalence between mechanical work and heat, implying heat is a form of energy, not a substance",
                evidence=[
                    "Joule, 'On the Mechanical Equivalent of Heat', Phil. Trans. 140 (1850) 61-82",
                ],
                confidence=0.90,
                affected_quantity="mechanical equivalent of heat",
                theories_involved=["caloric theory", "mechanics"],
            ),
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Caloric theory needed special pleading for friction (claiming caloric was 'squeezed out' of materials), latent heat, and radiant heat",
                evidence=[
                    "Various 18th-century modifications to caloric theory to handle anomalies",
                    "Davy's ice-rubbing experiment (1799) showed heat from friction even when no caloric could be squeezed from ice",
                ],
                confidence=0.80,
                affected_quantity="caloric in friction, radiation, latent heat",
                theories_involved=["caloric theory"],
            ),
        ],
        time_stuck_years=60,
        time_to_solve_after=10,
        key_insight="Heat is not a substance but a form of energy (kinetic energy of molecules). It can be created from work and converted back. The caloric fluid does not exist.",
        what_made_it_hard="Caloric theory explained conduction, specific heat, and gas expansion quite well. It was championed by Lavoisier and the French school. The kinetic theory of heat required belief in atoms, which many resisted.",
        trigger="Joule's precise calorimetric experiments (1843-1850) establishing the mechanical equivalent of heat, combined with Mayer's theoretical arguments (1842) for energy conservation",
        succeeded=False,
    ))

    # =========================================================================
    # ADDITIONAL ENTRIES
    # =========================================================================

    # 31. Copernican heliocentrism
    records.append(PremiseShiftRecord(
        field="astronomy",
        year=1543,
        person="Nicolaus Copernicus",
        old_premise="The Earth is the stationary center of the universe; all celestial bodies orbit the Earth",
        new_premise="The Earth and other planets orbit the Sun; the Earth rotates daily on its axis",
        premise_error_type=PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Ptolemaic geocentric model required ~80 epicycles, deferents, and equants to match planetary observations",
                evidence=[
                    "Ptolemy, 'Almagest' (~150 CE)",
                    "Alfonso X's 'Alfonsine Tables' (1252) extended and corrected Ptolemaic parameters",
                ],
                confidence=0.85,
                affected_quantity="planetary positions",
                theories_involved=["Ptolemaic astronomy"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Retrograde motion of outer planets always occurred when the planet was opposite the Sun, with no explanation in geocentric models",
                evidence=[
                    "Ancient astronomers noted this correlation but it was not explained by Ptolemy's model",
                ],
                confidence=0.85,
                affected_quantity="retrograde motion timing",
                theories_involved=["Ptolemaic astronomy"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="The period of the Sun appeared as a component in every planet's motion (the 'great inequality'), without structural explanation",
                evidence=[
                    "Copernicus, 'De Revolutionibus' (1543) noted this simplification",
                ],
                confidence=0.80,
                affected_quantity="solar period in planetary models",
                theories_involved=["Ptolemaic astronomy"],
            ),
        ],
        time_stuck_years=1400,
        time_to_solve_after=10,
        key_insight="Put the Sun at the center. Retrograde motion is automatically explained as the Earth overtaking outer planets. The Sun's ubiquity in all planetary models vanishes because it is the actual center.",
        what_made_it_hard="Geocentrism was supported by Aristotelian physics (heavy things fall to the center), common sense (we don't feel the Earth move), lack of observed stellar parallax, and religious doctrine.",
        trigger="Copernicus's dissatisfaction with Ptolemy's equant (which violated the principle of uniform circular motion) led him to explore alternative geometries",
    ))

    # 32. Pasteur / germ theory of disease
    records.append(PremiseShiftRecord(
        field="medicine/biology",
        year=1862,
        person="Louis Pasteur, Robert Koch",
        old_premise="Disease arises spontaneously from miasma (bad air), imbalanced humors, or environmental conditions; living organisms arise by spontaneous generation",
        new_premise="Specific diseases are caused by specific microorganisms that can be identified, cultured, and transmitted",
        premise_error_type=PremiseErrorType.INVERTED_CAUSATION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Semmelweis showed handwashing dramatically reduced puerperal fever mortality, but no mechanism was known",
                evidence=[
                    "Semmelweis, 'Die Aetiologie, der Begriff und die Prophylaxis des Kindbettfiebers' (1861)",
                    "Mortality dropped from ~10% to ~1% with chlorinated hand-washing at Vienna General Hospital (1847)",
                ],
                confidence=0.90,
                affected_quantity="maternal mortality rate",
                theories_involved=["miasma theory", "humoral medicine"],
            ),
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Epidemics followed clear transmission patterns (person-to-person, water supply) incompatible with miasma theory",
                evidence=[
                    "Snow, 'On the Mode of Communication of Cholera' (1855): Broad Street pump investigation",
                ],
                confidence=0.85,
                affected_quantity="disease transmission patterns",
                theories_involved=["miasma theory", "contagionism"],
            ),
            Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description="Pasteur's swan-neck flask experiments showed no spontaneous generation when contamination was prevented",
                evidence=[
                    "Pasteur, 'Memoire sur les corpuscules organises qui existent dans l'atmosphere' (1861)",
                ],
                confidence=0.95,
                affected_quantity="spontaneous generation of microorganisms",
                theories_involved=["spontaneous generation theory"],
            ),
        ],
        time_stuck_years=200,
        time_to_solve_after=20,
        key_insight="Microorganisms cause disease and decay. They come from pre-existing organisms, not spontaneous generation. Each disease has a specific microbial cause that can be isolated (Koch's postulates, 1884).",
        what_made_it_hard="Microorganisms were invisible without microscopes. Miasma theory had some predictive success (swamps are disease-prone). Semmelweis was rejected by the medical establishment. The diversity of microbial diseases made a unified theory seem implausible.",
        trigger="Pasteur's work on fermentation (1857-1861) established that microorganisms caused specific chemical transformations, which he extended to disease causation",
    ))

    # 33. Lavoisier / oxygen theory of combustion
    records.append(PremiseShiftRecord(
        field="chemistry",
        year=1789,
        person="Antoine Lavoisier",
        old_premise="Combustion releases phlogiston from materials; air is a simple substance that absorbs phlogiston",
        new_premise="Combustion is combination with oxygen from the air; mass is conserved in chemical reactions; elements combine in definite proportions",
        premise_error_type=PremiseErrorType.INVERTED_CAUSATION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Metals gained weight upon calcination, opposite to what phlogiston release predicted",
                evidence=[
                    "Lavoisier's sealed-vessel experiments (1772-1774) showed precise mass gain equal to air consumed",
                ],
                confidence=0.95,
                affected_quantity="mass change in calcination",
                theories_involved=["phlogiston theory"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Priestley's 'dephlogisticated air' (oxygen) supported combustion and respiration in exactly parallel ways",
                evidence=[
                    "Priestley, 'Experiments and Observations on Different Kinds of Air' (1774-1786)",
                ],
                confidence=0.85,
                affected_quantity="oxygen's role in combustion and respiration",
                theories_involved=["phlogiston theory", "pneumatic chemistry"],
            ),
        ],
        time_stuck_years=107,
        time_to_solve_after=15,
        key_insight="Combustion is gain of oxygen, not loss of phlogiston. Careful mass balance shows that the total mass of reactants equals products. Chemical elements are substances that cannot be decomposed further.",
        what_made_it_hard="Phlogiston theory was a broad framework connecting combustion, smelting, and respiration. Lavoisier had to replace not just the theory but the entire chemical nomenclature and conceptual framework.",
        trigger="Lavoisier's quantitative experiments with phosphorus and sulfur combustion in sealed vessels (1772), followed by learning of Priestley's discovery of oxygen (1774)",
    ))

    # 34. Kepler / elliptical orbits
    records.append(PremiseShiftRecord(
        field="astronomy",
        year=1609,
        person="Johannes Kepler",
        old_premise="Celestial bodies move in combinations of perfect circles (a metaphysical necessity from Plato through Copernicus)",
        new_premise="Planets move in ellipses with the Sun at one focus; they sweep equal areas in equal times",
        premise_error_type=PremiseErrorType.UNNECESSARY_ASSUMPTION,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                description="Even Copernicus's heliocentric model required epicycles to match observations because it used circular orbits",
                evidence=[
                    "Copernicus, 'De Revolutionibus' (1543) still used ~30 circles",
                    "Copernicus's predictions were no more accurate than Ptolemy's for most planets",
                ],
                confidence=0.85,
                affected_quantity="planetary positions",
                theories_involved=["Copernican astronomy"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description="Mars's orbit deviated from circular predictions by 8 arcminutes -- small but clearly outside Tycho's observational precision of 2 arcminutes",
                evidence=[
                    "Tycho Brahe's observations of Mars (1580-1601), the most precise pre-telescopic measurements",
                    "Kepler, 'Astronomia Nova' (1609) describes his struggle with the 8-arcminute discrepancy",
                ],
                confidence=0.95,
                affected_quantity="Mars orbital position error",
                theories_involved=["circular orbit astronomy"],
            ),
        ],
        time_stuck_years=2000,
        time_to_solve_after=5,
        key_insight="Abandon perfect circles. Ellipses fit Mars's orbit exactly. The physical cause is the Sun's influence (Kepler intuited a force, later identified as gravity by Newton).",
        what_made_it_hard="Circles were a metaphysical commitment stretching from Plato to Copernicus. The deviation for Mars was only 8 arcminutes. Kepler himself spent years trying circular combinations before reluctantly trying ellipses.",
        trigger="Tycho Brahe's unprecedentedly precise observations of Mars bequeathed to Kepler, and Kepler's stubborn insistence that 8 arcminutes of error mattered: 'these 8 minutes paved the way for the reformation of all astronomy'",
    ))

    # 35. Faraday / field concept
    records.append(PremiseShiftRecord(
        field="physics",
        year=1845,
        person="Michael Faraday",
        old_premise="Electric and magnetic forces act instantaneously at a distance between point charges and currents; the space between is empty and passive",
        new_premise="Electric and magnetic forces are mediated by fields filling all of space; the field is the fundamental physical entity, not the charges",
        premise_error_type=PremiseErrorType.IMPLICIT_BACKGROUND,
        symptoms_before=[
            Symptom(
                symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                description="Action-at-a-distance theories required instantaneous propagation, which was physically implausible and led to retardation problems",
                evidence=[
                    "Newton himself expressed discomfort with action at a distance in letters to Bentley (1692-1693)",
                    "The German school (Weber, Neumann) developed action-at-a-distance electrodynamics with increasing complexity",
                ],
                confidence=0.80,
                affected_quantity="speed of electromagnetic interaction",
                theories_involved=["action-at-a-distance electrodynamics"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Iron filings around magnets traced continuous curves (field lines) suggesting a physical reality filling space",
                evidence=[
                    "Faraday, 'Experimental Researches in Electricity', Series I-XXX (1831-1855)",
                    "Faraday's visualization of 'lines of force' from iron filing patterns",
                ],
                confidence=0.85,
                affected_quantity="electromagnetic field structure",
                theories_involved=["electrostatics", "magnetostatics"],
            ),
            Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description="Electromagnetic induction depended on rate of change of field lines through a circuit, not on the source charges directly",
                evidence=[
                    "Faraday's law of induction (1831): EMF depends on rate of change of magnetic flux",
                ],
                confidence=0.85,
                affected_quantity="electromagnetic induction",
                theories_involved=["electrodynamics"],
            ),
        ],
        time_stuck_years=100,
        time_to_solve_after=20,
        key_insight="The field is not a mathematical convenience but a physical entity that stores energy, carries momentum, and mediates forces. The 'empty space' between charges is filled with a dynamical field.",
        what_made_it_hard="The Newtonian paradigm of point particles and forces was enormously successful. Faraday lacked mathematical training and was not taken seriously by Continental mathematicians. The field concept required Maxwell's mathematical formulation to gain acceptance.",
        trigger="Faraday's experiments on electromagnetic induction (1831) and the magneto-optical effect (1845), which showed light interacting with magnetic fields -- proving the field had physical reality",
    ))

    return records

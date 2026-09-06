# YAX V5.1 architecture matrix

This matrix names each empirical treatment rather than treating “AI exposure” as a single observed variable. All six measures are harmonized to Census 2018 occupations. The strict no-renormalization coverage rule retains an occupation only when every mapped source component has a finite score; partially scored occupations remain missing rather than having surviving weights rescaled.

| Architecture | Technology/capability primitive | Occupational primitive and labels | Aggregation | Native taxonomy | Harmonization | Final stock treatment |
|---|---|---|---|---|---|---|
| AIOE administrative/equal | Progress in ten AI applications | 52 O\*NET abilities linked to AI applications using crowd judgments; published occupation AIOE | Published occupation scores; equal mean when multiple SOC-2010 sources enter a target Census occupation | SOC 2010 | Official SOC 2010→2018 and SOC→Census bridges; equal administrative aggregation; strict full-component support | Employment-weighted occupation quintiles; standardized continuous score where specified |
| AIOE ability/direct | Same ten AI applications | Application–ability relatedness and target-occupation O\*NET ability importance/prevalence | Direct reconstruction on the target occupation's abilities | Source application/ability data plus target O\*NET 25.1 | Direct target-occupation reconstruction, then Census 2018 bridge; strict full-component support | Same representations |
| AIOE source-employment weighted | Same ten AI applications | Published SOC-2010 occupation AIOE | Multiple SOC-2010 parents weighted by May 2018 OEWS employment | SOC 2010 | Official 2010→2018 bridge using source-vintage OEWS weights, then Census 2018; strict full-component support | Same representations |
| Eloundou alpha | Direct LLM task acceleration | O\*NET tasks labeled E0/E1/E2 by GPT-4; E1 indicates an LLM alone can halve completion time at constant quality | Share of tasks labeled E1 | O\*NET-SOC 2019 / SOC 2018 | Six-digit SOC collapse and official SOC→Census 2018 bridge; strict full-component support | Same representations |
| Eloundou beta | Direct LLM plus limited software complementarity | Same GPT-4 task labels | E1 + 0.5×E2 task share | O\*NET-SOC 2019 / SOC 2018 | Same | Same representations; confirmatory primary architecture |
| Eloundou broad | LLM plus complementary software | Same GPT-4 task labels | E1 + E2 task share (published paper's zeta; source file calls it gamma) | O\*NET-SOC 2019 / SOC 2018 | Same | Same representations |

For 2017–2019 CPS observations, Census 2010 occupation codes are route-expanded through the official Census 2010→2018 conversion weights. From 2020 forward, raw CPS occupations are already Census 2018 codes and are directly matched. Literal common-support comparisons use the same 444 occupations (83.14% of model-period employment), but each architecture still defines its own scores, ranks, quintiles, and high-exposure membership.

The family-balanced consensus component is descriptive:

\[
A_o={1\over3}\sum_{j\in AIOE}Z_{jo},\quad
E_o={1\over3}\sum_{j\in Eloundou}Z_{jo},\quad
F_o={A_o+E_o\over2},\quad G_o={A_o-E_o\over2}.
\]

`F` is an equal-family-weight consensus construction, not an estimated latent factor. `G` captures only the AIOE-versus-Eloundou family-centroid dimension, not every architecture-specific difference.

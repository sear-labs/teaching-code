# The energy-system series: layout plan

The companion code for **Introduction to Energy System Modeling** by Erick C. Jones Jr., the CC BY
open textbook. Rewritten 2026-09-06 against the manuscript. This file lives here until the
repository it describes exists, then moves into it.

> **The manuscript is the source of truth, not the Pressbooks site.** The published book at
> <https://uta.pressbooks.pub/energysystemmodeling> is the **1 September snapshot** and is two
> chapters behind. Verified: the online contents match
> `CARES Book/Archive/2026-09-01 pre-Part-IV-expansion/` heading for heading. Build any mapping
> against `CARES Book/Manuscript/`, and re-check it whenever that folder changes.

**The book is the spine, not the semester.** A reader arrives from a chapter. Course codes (`M0`,
`SB6`, `GRAD_N`) and term folders (`2026 Fall`) name a delivery of the course rather than the
subject, and age badly for something revised over years.

---

## The correction that matters most

My previous draft named notebook folders for chapter numbers, `ch15_transport_problem` and so on.
**That was wrong, and the book just proved it.** Part IV expanded from four chapters to six on
1 September, so every chapter from 14 upward shifted by two. Chapter-numbered folders would have
meant renaming ten directories and breaking every link into them, for an edit that changed no
subject matter at all.

> **Folders are named for their part and their subject. Chapter numbers live in one mapping table
> and nowhere else.** Parts have been stable across the expansion; chapter numbers have not. When
> the book renumbers again, one table changes and no path does.

## Identity

| | |
|---|---|
| repository | `sear-labs/energy-system-modeling`, public |
| package | `esm`, imported from `src/` by path, as `orteach` is here |
| code licence | MIT, matching `advopt-lithiumsc` and `code-standard` |
| prose licence | CC BY 4.0 on notebooks and text, matching the book |
| archetype | A + T: Parts 1–2 govern `src/`, Part 3 governs `notebooks/`, Part 4 the boundary |

`teaching-code`'s missing `LICENSE` was added 2026-09-06.

## Layout

```
src/esm/                  the package
data/raw/                 authored instance tables, both sides read them
data/vendor/              third-party data, one sidecar per file
notebooks/
  p1_foundations/         model_boundary.ipynb
                          one_house_balance.ipynb
                          README.md  -> teaching-code 12 for the toy LP and PyPSA
  p2_demand/              representative_days.ipynb
                          end_use_disaggregation.ipynb
                          process_heat_electrification.ipynb          NEW
                          depot_charging.ipynb                        NEW
  p3_generation/          capital_and_lcoe.ipynb
                          screening_curves.ipynb                      NEW
  p4_networks/            feeder_hosting_capacity.ipynb               NEW
                          pipeline_pressure_and_n1.ipynb              NEW
                          cost_of_transit_by_mode.ipynb               NEW
                          pipeline_transport.ipynb
                          power_flow_and_lmp.ipynb
                          real_network_import.ipynb
                          texas_multi_city_buildout.ipynb
  p5_storage_supply/      storage_duration_sizing.ipynb               NEW
                          material_requirements.ipynb
                          README.md  -> teaching-code 12 for the battery, 13 for sourcing
  appendix/               facility_decision.ipynb
  graduate/               model_diversity.ipynb
tests/  tools/  tools/builders/
```

## The mapping table

Twenty-two chapters, five case studies, one appendix. This is the only place chapter numbers appear.

| ch | title | companion |
|---|---|---|
| 1 | What Is Energy System Modeling | `model_boundary` (motivating exception) |
| 2 | Physical Laws and Energy Balances | `one_house_balance` |
| 3 | Building and Solving a Model | → teaching-code 12 |
| 4 | Modeling in Code, PyPSA and Capacity Expansion | → teaching-code 12 |
| 5 | Demand Fundamentals | `representative_days` |
| 6 | Residential and Commercial Demand | `end_use_disaggregation` |
| 7 | Industrial Demand | `process_heat_electrification` NEW |
| 8 | Transportation Demand and Charging Infrastructure | `depot_charging` NEW |
| 9 | Generation Metrics and the Modern Modeling Goal | `capital_and_lcoe` |
| 10–12 | Thermal, Nuclear and Petroleum, Renewables | `screening_curves` NEW |
| 13 | Spatial Mismatch and the Modalities of Movement | `cost_of_transit_by_mode` NEW |
| **14** | **The Distribution System** | `feeder_hosting_capacity` NEW |
| **15** | **Pipeline Capacity, Pressure, and Reliability** | `pipeline_pressure_and_n1` NEW |
| 16 | The Economics of Energy Transit | `cost_of_transit_by_mode` NEW |
| 17 | Network Optimization, The Transportation Problem | `pipeline_transport` |
| 18 | Grid Physics and Discrete Logistics | `power_flow_and_lmp`, `real_network_import` |
| 19 | Traditional and Battery Storage | → teaching-code 12 |
| 20 | Long-Duration and Unconventional Storage | `storage_duration_sizing` NEW |
| 21 | Energy Supply Chains and Material Intensity | `material_requirements` |
| 22 | Supply-Chain Optimization and Trade Policy | → teaching-code 13 |
| CS4 | The Energy Arteries | `texas_multi_city_buildout` |
| App A | Writing the Capstone Final Report | `facility_decision` |

Chapters 14 and 15 are the two the expansion added. Case Studies 1, 2, 3 and 5 have no companion;
CS3 is a scenario sweep over the Texas instance rather than a new notebook, and CS2 is a scenario
exercise better placed as a closing question in Chapter 22's material.

## What does not move, because it is already published

| chapter | already at |
|---|---|
| 3 and 4, building and solving, PyPSA | `teaching-code` notebook 12, which is REE Module 0 |
| 19, battery storage | notebook 12, which carries the battery, its efficiencies and standing loss |
| 22, supply-chain optimisation | notebook 13, named as REE Module 4's model in its own docstring |

This shrinks the Module 4 split to almost nothing: its sourcing LP is already notebook 13, so only
the material-intensity accounting moves across, as Chapter 21's companion.

## Placement rule

**Anchor at the last chapter whose material the notebook needs; forward-reference from the first
chapter that touches it.** A companion is only runnable once the reader has its prerequisites.

One deliberate exception: a notebook whose job is to raise the question the chapters then answer
anchors at the first chapter. `model_boundary` is that case.

**Split when the halves have different methods and different prerequisites**, not merely because a
notebook touches two chapters. Only Module 4 fails that test.

## Vendored data

Third-party files live in `data/vendor/`, never mixed with authored tables, each with a sidecar
naming source URL, retrieval date, licence and citation. **None of the current sources is MIT.**

| file | licence | note |
|---|---|---|
| TX-123BT, Lu and Li 2023 | CC BY 4.0 | DOI `10.6084/m9.figshare.22144616`, attribution required |
| PyPSA technology-data costs | **GPL-3.0** | keep its notice beside it, do not relicense |
| MATPOWER cases | BSD-3 in practice, no SPDX detected | confirm before vendoring |
| Open-Meteo archive | CC BY 4.0 under their terms | an API; cache a snapshot |
| TU Berlin cloud time series | **none stated** | replace, do not vendor |

The GPL-3.0 cost tables are the one file in an MIT repository that will not be MIT. Legal so long as
it keeps its notice and is not relicensed, but it should be a conscious choice. The TU Berlin file is
unlicensed and behind a personal share link that can vanish, so it is both unredistributable and
unreproducible.

## Seven new notebooks

Coverage today is roughly ten of the twenty-eight chapter, case-study and appendix slots. These take
it to about twenty. Each is small, reuses machinery already in the two repositories, and has an
obvious agreement assertion.

**`screening_curves`, Chapters 10–12.** Cost per MWh against capacity factor for gas, coal, nuclear,
solar and wind; the crossovers; the merit order falling out of them. No solver, so it is cheap. It is
the missing link between Chapter 9's LCOE and every capacity model later: it answers why baseload and
peaker are different machines rather than asserting it. Three chapters from one notebook.

**`cost_of_transit_by_mode`, Chapters 13 and 16.** Dollars per MWh-mile for transmission, pipeline,
LNG, rail coal and diesel truck, with energy density beside it. No solver. It gives the transport
model in Chapter 17 its motivation: you move fuel rather than electrons over distance, and here is
the arithmetic that says so.

**`feeder_hosting_capacity`, Chapter 14.** A radial distribution feeder with load along it and
rooftop solar being added. How much can it host before voltage limits or transformer ratings bind?
Teaches why distribution constrains the transition in a way transmission does not, and bridges the
house in Part II to the grid in Chapter 18. One of the two chapters the expansion added.

**`pipeline_pressure_and_n1`, Chapter 15.** Gas flow is not a capacity bound: it follows the
square root of the difference of squared pressures. Model a small network with pressure as a
variable, then remove a compressor and re-solve. This is the notebook that shows what the capacity
bound in `pipeline_transport` was hiding, and the nonlinear relation needs lifting, so it reuses
teaching-code notebook 06 directly. The clearest case in the whole series of the method library
serving the case series.

**`depot_charging`, Chapter 8.** A fleet returning at known times with known energy needs, a
connection limit, and a site demand charge. The demand charge is a cost on the peak, so it needs an
auxiliary variable bounding every hour, the first genuinely new modelling trick since lifting. Gives
Case Study 1 something to stand on.

**`process_heat_electrification`, Chapter 7.** Industrial process heat at temperature, currently
gas-fired, choosing between boiler, heat pump and resistance against an hourly price. A heat pump's
efficiency falls as the lift rises, which is why industrial electrification is harder than
residential. Fills the one part where companions stop halfway.

**`storage_duration_sizing`, Chapter 20.** A wind profile with a multi-day lull, sized twice: a
battery with high round-trip efficiency and dear energy capacity, hydrogen with the opposite.
Teaches the power-versus-energy split and why duration picks the technology. Extends the battery
already in notebook 12 rather than rebuilding it.

## A discipline the book already has, worth keeping

`Tools/build_figures.py` re-derives the merit-order dispatch and re-solves the battery, and
**asserts both against the notebooks' published output before drawing**, so a figure cannot drift
from the code a student runs. That is an agreement assertion in everything but name, and it should
move into the new repository and extend to every figure. The code-chunk plan already states the
matching rule: chapters name the notebook that produces every figure.

## Build order

1. Repository, licences, README carrying the mapping table, builders, and the existing drift checker.
2. Environment that runs all thirteen: PyPSA, Gurobi, PuLP, NetworkX, SciPy, Plotly, ipywidgets.
3. Execute everything as-is and record what breaks. Diagnostic only.
4. Vertical slice on `power_flow_and_lmp`: eighteen cells, two assertions already, no network fetch.
   It fixes the package shape, the table layout and the assertion pattern before the rest inherit them.
5. Tables into `data/raw/`, then the package, then one agreement assertion per notebook.
6. `screening_curves` and `cost_of_transit_by_mode` next: cheapest, and four chapters between them.
7. `feeder_hosting_capacity` and `pipeline_pressure_and_n1`, the two chapters the expansion added.
8. The three remaining newcomers.
9. Conventions pass, execute, commit with defect records, push. Repoint the two READMEs here.

## Open, still

- A static capacity sweep must precede the sliders in `pipeline_transport`. Widgets render nothing
  when executed headlessly, so the recorded output currently carries none of the lesson.
- Whether the graduate notebooks sit in `graduate/` or as advanced companions inside their part.
  `model_diversity` fits no chapter; `real_network_import` is Chapter 18 at real scale.
- The mapping was built from manuscript chapter titles and the notebooks, not from chapter text.
  Confirming it against the text is a real task.
- The manuscript moves. Re-check the table against `CARES Book/Manuscript/` before trusting it.

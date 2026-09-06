# The energy-system series: layout plan

The companion code for **Introduction to Energy System Modeling** by Erick Jones, the CC BY open
textbook at <https://uta.pressbooks.pub/energysystemmodeling>. Decided 2026-09-06. This file lives
here until the repository it describes exists, then moves into it.

**The book is the spine, not the semester.** A reader arrives from a chapter, so the folder they land
in is named for that chapter. Course codes (`M0`, `SB6`, `GRAD_N`) and term folders (`2026 Fall`)
name a delivery of the course, not the subject, and they age badly for something meant to be revised
over years.

---

## Identity

| | |
|---|---|
| repository | `sear-labs/energy-system-modeling`, public |
| package | `esm`, imported from `src/` by path, as `orteach` is here |
| code licence | MIT, matching `advopt-lithiumsc` and `code-standard` |
| prose licence | CC BY 4.0 on notebooks and text, matching the book |
| archetype | A + T, so Parts 1–2 govern `src/`, Part 3 governs `notebooks/`, Part 4 the boundary |

`teaching-code` is missing a `LICENSE` file entirely and is public, which under GitHub's defaults
means all rights reserved. Add MIT there in the same pass.

## Layout

```
src/esm/                     the package
data/raw/                    authored instance tables, both sides read them
data/vendor/                 third-party data, one sidecar per file (see below)
notebooks/
  ch01_what_is_modeling/     -> model_boundary.ipynb          (motivating exception)
  ch02_energy_balances/      -> one_house_balance.ipynb
  ch04_modeling_in_code/     -> README: points at teaching-code 12
  ch05_demand_fundamentals/  -> representative_days.ipynb
  ch06_residential_demand/   -> end_use_disaggregation.ipynb
  ch07_industrial_demand/    -> process_heat_electrification.ipynb        NEW
  ch08_transport_demand/     -> depot_charging.ipynb                      NEW
  ch09_generation_metrics/   -> capital_and_lcoe.ipynb
  ch10_12_technologies/      -> screening_curves.ipynb                    NEW
  ch13_14_moving_energy/     -> cost_of_transit_by_mode.ipynb             NEW
  ch15_transport_problem/    -> pipeline_transport.ipynb
  ch16_grid_physics/         -> power_flow_and_lmp.ipynb
                                real_network_import.ipynb
  ch17_storage/              -> README: points at teaching-code 12
  ch18_long_duration/        -> storage_duration_sizing.ipynb             NEW
  ch19_material_intensity/   -> material_requirements.ipynb   (half of Module 4)
  ch20_supply_chain_opt/     -> README: points at teaching-code 13
  cs04_energy_arteries/      -> texas_multi_city_buildout.ipynb
  appA_capstone/             -> facility_decision.ipynb
  graduate/                  -> model_diversity.ipynb
tests/  tools/  tools/builders/
```

Zero-padded chapter numbers so the sort key is the reading order. A folder spanning two chapters is
named for both, `ch10_12_technologies`, and anchors at the later one.

## What does not move, because it is already published

Three chapters need no new notebook. The material exists in this library and the series points at it
rather than copying it, which is the library-teaches-the-method, series-carries-the-case rule.

| chapter | already at |
|---|---|
| 4, modeling in code with PyPSA | `teaching-code` notebook 12, which is REE Module 0 |
| 17, battery storage | notebook 12, which carries the battery, its efficiencies and standing loss |
| 20, supply-chain optimisation | notebook 13, whose package docstring names it as REE Module 4's model |

**This shrinks the Module 4 split to almost nothing.** Its Part A sourcing LP is already notebook 13.
Only Part B, the material-intensity accounting, moves into the series, as Chapter 19's companion.
Chapter 15's transport problem also points sideways at notebook 04 for the method while keeping the
Texas crude case of its own.

## Placement rule

**Anchor at the last chapter whose material the notebook needs. Forward-reference it from the first
chapter that touches it.** A companion is only runnable once the reader has its prerequisites, so
anchoring at the first overlap puts code in front of someone who has not met the ideas in it.

One deliberate exception: a notebook whose job is to raise the question the chapters then answer
anchors at the first chapter. `model_boundary` is that case, which is why it sits at Chapter 1.

**Split a notebook when its halves have different methods and different prerequisites**, not merely
because it touches two chapters. Only Module 4 fails that test, and the split is nearly free because
half of it is already published here.

## Vendored data

Third-party files go in `data/vendor/`, never mixed with authored tables, each with a sidecar naming
source URL, retrieval date, licence and citation. **None of the current sources is MIT.**

| file | licence | note |
|---|---|---|
| TX-123BT, Lu and Li 2023 | CC BY 4.0 | DOI `10.6084/m9.figshare.22144616`, attribution required |
| PyPSA technology-data costs | **GPL-3.0** | keep its licence beside it, do not relicense |
| MATPOWER cases | BSD-3 in practice, no SPDX detected | confirm before vendoring |
| Open-Meteo archive | CC BY 4.0 under their terms | an API, cache a snapshot |
| TU Berlin cloud time series | **none stated** | replace, do not vendor |

The GPL-3.0 cost tables are the one thing in an MIT repository that will not be MIT. That is legal
so long as the file keeps its notice and is not relicensed, but it should be a conscious choice.
The TU Berlin file is unlicensed and sits behind a personal cloud share that can vanish, so it is
both unredistributable and unreproducible; regenerate that series or substitute an open one.

## Five new notebooks, and why each earns its place

Coverage today is about ten of the twenty-six chapter, case-study and appendix slots. These five
take it to roughly eighteen. Each is small, uses machinery already present in the two repositories,
and has an obvious agreement assertion.

**`screening_curves.ipynb`, Chapters 10–12.** Cost per MWh against capacity factor for gas, coal,
nuclear, solar and wind; the crossover points; the merit order falling out of them. Pure arithmetic,
no solver, so it is cheap. It is also the missing link between Chapter 9's LCOE and every capacity
model later in the book: it answers why baseload and peaker are different machines rather than
asserting it. Three chapters covered by one notebook.

**`cost_of_transit_by_mode.ipynb`, Chapters 13–14.** Dollars per MWh-mile for high-voltage
transmission, gas pipeline, LNG shipping, rail coal and diesel truck, with energy density beside it.
Order-of-magnitude reasoning, no solver. It gives the transport LP in Chapter 15 its motivation:
you move fuel rather than electrons over long distances, and here is the arithmetic that says so.

**`depot_charging.ipynb`, Chapter 8.** A vehicle fleet returning at known times with known energy
needs, a connection limit, and a site demand charge. Decide when to charge. The demand charge is
worth a notebook on its own: it is a cost on the peak, so it needs an auxiliary variable bounding
every hour, which is the first genuinely new modelling trick since the lifting in Chapter 4. Also
gives Case Study 1 something to stand on.

**`process_heat_electrification.ipynb`, Chapter 7.** An industrial site with process heat at
temperature, currently gas-fired, choosing between boiler, heat pump and resistance against an
hourly price. A heat pump's efficiency falls as the temperature lift rises, which is why industrial
electrification is harder than residential. Fills the one part of the book where the companions stop
halfway.

**`storage_duration_sizing.ipynb`, Chapter 18.** A wind profile with a multi-day lull, sized twice:
a battery with high round-trip efficiency and expensive energy capacity, and hydrogen with the
opposite. Teaches the power-versus-energy capacity split and why duration decides the technology.
It extends the battery already in notebook 12 rather than rebuilding it.

Case Study 2 stays without a companion. It is a scenario exercise rather than a modelling one, and
is better served as a closing exercise in the Chapter 20 material. Case Study 3 is a scenario sweep
over the Texas buildout instance, so it is a stage of that notebook rather than a new one.

## Build order

1. Repository, licences, README with the chapter map, builders and the existing drift checker.
2. Environment that runs all thirteen: PyPSA, Gurobi, PuLP, NetworkX, SciPy, Plotly, ipywidgets.
3. Execute everything as-is and record what breaks. Diagnostic only.
4. Vertical slice on `power_flow_and_lmp`: eighteen cells, two assertions already, no network fetch.
   It fixes the package shape, the table layout and the assertion pattern before twelve notebooks
   inherit them.
5. Tables out of the notebooks into `data/raw/`, then the package, then one agreement assertion each.
6. The two arithmetic newcomers, `screening_curves` and `cost_of_transit_by_mode`, next: they are the
   cheapest and cover four chapters between them.
7. The three modelling newcomers.
8. Conventions pass, execute, commit with defect records, push. Repoint the two READMEs here, and add
   the missing `LICENSE` to `teaching-code`.

## Open, still

- The static sweep that must go before the sliders in `pipeline_transport`, so the recorded output
  carries the lesson. Widgets render nothing when executed headlessly.
- Whether the graduate notebooks sit in `graduate/` or as advanced companions inside their chapters.
  `model_diversity` fits no chapter at all; `real_network_import` is Chapter 16 at real scale.
- Confirming the chapter map against the chapters themselves. It was built from the table of contents
  and the notebooks, not from the chapter text.

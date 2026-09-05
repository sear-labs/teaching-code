# Seeds

Each `seed_<name>.py` writes one notebook under `notebooks/` from scratch, without outputs. The
seeds are how those notebooks were authored and how they are edited: change the seed, run it, then
execute the notebook in place so it ships with outputs (standard Part 5).

```bash
python tools/seeds/seed_games.py
jupyter nbconvert --to notebook --execute --inplace notebooks/10_game_theory/zero_sum_game.ipynb
```

`dispatch_to_pypsa.ipynb` executes in the `orteach-energy` kernel (see
`notebooks/12_energy_systems_pypsa/README.md`); add `--ExecutePreprocessor.kernel_name=orteach-energy`.

A seed that is behind its notebook is a trap: running it would silently undo whatever was fixed in
the notebook since. So a seed is kept only while it reproduces the committed notebook cell for
cell, and `python tools/check_seeds.py` verifies that for every seed here. Six notebooks have no seed
because they were last edited in place and the notebook is their source: `04` transportation and
assignment, `05` facility_location, `07` newsvendor, `08` monte_carlo, `11` capital_budgeting.

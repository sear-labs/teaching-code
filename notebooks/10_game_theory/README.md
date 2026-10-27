# 10 — Game theory

`zero_sum_game.ipynb` — a two-person zero-sum game as a pair of dual LPs. Package: `orteach.games`.

`saddle_points.ipynb` — when a game needs an LP at all: the coin game, the flu-medicine advertising
game from Taha (a saddle point at TV against TV), and the same game with that one entry changed,
which removes the saddle point (value 42/17). Same package; tables `coin_2x2.csv` and
`flu_advertising_3x4.csv`.

## Non-zero-sum games with a planner are in the advopt repository

The planner-and-game sequence — a cooperative benchmark against competing firms, best response and
collusion — is the lithium supply-chain library's, and stays there:

    https://github.com/sear-labs/advopt-lithiumsc   → 04ab_planner_and_game, and lithium/games.py

`saddle_points.ipynb` migrates the three examples of `04_Zero_Sum_Game_LP.ipynb`, the notebook IE 3315
and IE 5301 use in 2026 (in each course's code folder): same games, same numbers, built by hand
and checked against `orteach.games` instead of by a helper defined before the narration.

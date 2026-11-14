# FAA attribution forecast program

`main.py` reads every `.in` case from `MAKEFUN_INPUT_DIR` (default `/input`) and writes a matching `.out` file to `MAKEFUN_OUTPUT_DIR` (default `/output`). Each market receives 240 forecast rows containing the 5%, 25%, 50%, 75%, and 95% price quantiles.

The program uses each market's latest price (or 0.5 when it has no prices) to form its share of the total. It measures recent one-minute volatility from up to 121 prices, then forecasts each minute with a gradual pull toward that share and a volatility-scaled spread. A sufficiently large latest rise is gradually given back, and the median has a sum-gated volatility decay. Values are clamped to `[0, 1]`, rounded to six decimals, adjusted by the median deadband rule, and sorted. If all latest prices sum to zero, each market keeps its own latest price as the target to avoid division by zero.

Output is deterministic for identical inputs and uses only the Python standard library.

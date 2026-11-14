# Version six of the FAA attribution forecaster.
# Volatility is the root mean square of one-minute changes over the last 120 minutes,
# clamped between 0.0009 and 0.01. The spread grows with the horizon to the power 0.35.
# The centre is pulled toward the consistency target with weight 0.60, phased in over
# 30 minutes. Only rises of at least 0.02 are given back over 90 minutes, while falls
# persist. The median decays by a sum-gated volatility term with constant 96. A deadband
# pins the median to the last price when it is within 0.0006 and shrinks the other
# quantiles twenty percent toward the last price.
#!/usr/bin/env python3
"""Generate deterministic 240-minute probability forecasts for each input case."""

import json
import math
import os
from pathlib import Path


HORIZON = 240
NORMAL_QUANTILES = (-1.644854, -0.67449, 0.0, 0.67449, 1.644854)
WIDTH_FACTORS = (1.0, 0.8, 1.0, 0.45, 1.2)


def clamp(value, low, high):
    return min(high, max(low, value))


def forecast_case(case):
    markets = case["markets"]
    prices = [market.get("prices", []) for market in markets]
    last_prices = [series[-1] if series else 0.5 for series in prices]
    total_last = sum(last_prices)
    if total_last:
        targets = [price / total_last for price in last_prices]
    else:
        # With no aggregate mass, preserve each last price rather than divide by zero.
        targets = list(last_prices)

    volatilities = []
    last_moves = []
    for series in prices:
        recent = series[-121:]
        differences = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
        rms = math.sqrt(sum(change * change for change in differences) / len(differences)) if differences else 0.0
        volatilities.append(clamp(rms, 0.0009, 0.01))
        last_moves.append(series[-1] - series[-2] if len(series) >= 2 else 0.0)

    gate = clamp((total_last - 0.8) / 0.25, 0.0, 1.0)
    forecast_items = []
    for index, market in enumerate(markets):
        last = last_prices[index]
        volatility = volatilities[index]
        move = last_moves[index]
        rows = []
        for h in range(1, HORIZON + 1):
            phase = 1.0 - math.exp(-h / 30.0)
            centre = last + 0.60 * phase * (targets[index] - last)
            if move >= 0.02:
                centre -= move * (1.0 - math.exp(-h / 90.0))
            spread = volatility * (h ** 0.35)
            values = [
                centre + spread * width * quantile
                for quantile, width in zip(NORMAL_QUANTILES, WIDTH_FACTORS)
            ]
            values[2] *= math.exp(-96.0 * gate * volatility * volatility * h / 2.0)
            values = [round(clamp(value, 0.0, 1.0), 6) for value in values]

            if abs(values[2] - last) <= 0.0006:
                values[2] = round(clamp(last, 0.0, 1.0), 6)
                for q in (0, 1, 3, 4):
                    values[q] = round(clamp(values[q] + 0.20 * (last - values[q]), 0.0, 1.0), 6)
            rows.append(sorted(values))
        forecast_items.append({"id": market["id"], "q": rows})
    return {"forecasts": forecast_items}


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in sorted(input_dir.glob("*.in")):
        with input_path.open("r", encoding="utf-8") as handle:
            case = json.load(handle)
        result = forecast_case(case)
        output_path = output_dir / (input_path.stem + ".out")
        with output_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            handle.write("\n")


if __name__ == "__main__":
    main()

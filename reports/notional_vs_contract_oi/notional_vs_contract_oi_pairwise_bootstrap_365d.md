## Pairwise bootstrap checks (clustered events)

Positive `abs` diff means first class has higher forward realized move than A_true_deleverage. CI is 2.5/50/97.5%.

### BTCUSDT
- Cluster counts: {'A_true_deleverage': 145, 'B_passive_notional_shrink': 85, 'C_short_build_or_sticky_leverage': 123, 'D_risk_on_leverage_build': 136}
- B_minus_A_abs_24h: diff mean `0.31%`, CI `[-0.17%, 0.30%, 0.80%]`
- B_minus_A_abs_48h: diff mean `0.31%`, CI `[-0.24%, 0.31%, 0.87%]`
- B_minus_A_ret_24h: diff mean `0.03%`, CI `[-0.69%, 0.04%, 0.71%]`
- C_minus_A_ret_24h: diff mean `-0.21%`, CI `[-0.75%, -0.20%, 0.34%]`
- D_minus_A_abs_24h: diff mean `-0.05%`, CI `[-0.40%, -0.05%, 0.30%]`

### ETHUSDT
- Cluster counts: {'A_true_deleverage': 203, 'B_passive_notional_shrink': 113, 'C_short_build_or_sticky_leverage': 160, 'D_risk_on_leverage_build': 192}
- B_minus_A_abs_24h: diff mean `-0.02%`, CI `[-0.53%, -0.02%, 0.52%]`
- B_minus_A_abs_48h: diff mean `-0.17%`, CI `[-0.92%, -0.17%, 0.59%]`
- B_minus_A_ret_24h: diff mean `-0.01%`, CI `[-0.79%, -0.01%, 0.78%]`
- C_minus_A_ret_24h: diff mean `-0.26%`, CI `[-0.97%, -0.26%, 0.46%]`
- D_minus_A_abs_24h: diff mean `0.14%`, CI `[-0.32%, 0.15%, 0.60%]`

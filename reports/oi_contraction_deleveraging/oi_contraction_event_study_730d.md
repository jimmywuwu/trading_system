# OI Contraction / Deleveraging Volatility Regime — 730d Rerun

## Data quality
- BTCUSDT: fixture_hours=17521, OI 5m rows=210240, hourly coverage=100.00%, max OI gap=5.0m
- ETHUSDT: fixture_hours=17521, OI 5m rows=210240, hourly coverage=100.00%, max OI gap=5.0m

## Bottom-decile 4h OI contraction summary
- BTCUSDT 4h: abs event 0.7583% vs matched 0.7198% vs baseline 0.6569%; RV event 0.9364% vs matched 0.8477% vs baseline 0.7793%; raw events 1746, 24h episodes 382
- BTCUSDT 24h: abs event 1.8592% vs matched 1.8171% vs baseline 1.7008%; RV event 2.4395% vs matched 2.3288% vs baseline 2.1507%; raw events 1746, 24h episodes 382
- BTCUSDT 48h: abs event 2.6607% vs matched 2.5184% vs baseline 2.4214%; RV event 3.3834% vs matched 3.3391% vs baseline 3.1314%; raw events 1746, 24h episodes 382
- ETHUSDT 4h: abs event 1.1671% vs matched 1.0205% vs baseline 0.9650%; RV event 1.4157% vs matched 1.2339% vs baseline 1.1393%; raw events 1746, 24h episodes 379
- ETHUSDT 24h: abs event 2.9157% vs matched 2.6587% vs baseline 2.5468%; RV event 3.6993% vs matched 3.3609% vs baseline 3.1528%; raw events 1746, 24h episodes 379
- ETHUSDT 48h: abs event 3.9304% vs matched 3.7967% vs baseline 3.6595%; RV event 5.1505% vs matched 4.8408% vs baseline 4.5882%; raw events 1746, 24h episodes 379

## Bootstrap event-minus-matched CI
- BTCUSDT abs 24h: [-0.0773%, 0.0421%, 0.1634%]
- BTCUSDT abs 48h: [-0.0115%, 0.1423%, 0.3011%]
- BTCUSDT rv 24h: [0.0281%, 0.1109%, 0.1984%]
- BTCUSDT rv 48h: [-0.0539%, 0.0459%, 0.1471%]
- ETHUSDT abs 24h: [0.0819%, 0.2548%, 0.4357%]
- ETHUSDT abs 48h: [-0.1075%, 0.1315%, 0.3649%]
- ETHUSDT rv 24h: [0.2152%, 0.3366%, 0.4548%]
- ETHUSDT rv 48h: [0.1563%, 0.3091%, 0.4477%]
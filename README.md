# PKR Historical to Present Value Converter (آج کے حساب سے)
This simple calculator estimates how much a past amount of Pakistani Rupees would be worth in today's Pakistani rupees in terms of equal purchasing power.

## Estimation Methodology
Conversion factors are based on historic local Gold-prices.  

For estimation of conversion factors, firstly, relative prices of historic Gold-prices with current (average of Oct - Dec 2024) price were calculated i.e `P(2024) / P(t)` . To ensure a declining function, the series was then monotonically smoothed (if `P(t) > P(t-1)`, then `P(t)` was set as `P(t-1)` ), and for every year (t) where `P(t)` or `P(t-1)` was monotonically smoothed, 3-year moving average was used instead i.e. `P(t)` is set as `{P(t-1) + P(t) +P(t+1)}/3` . This smoothed series of relative local gold-prices is used as conversion factor.  

Gold price data is sourced from [State Bank of Pakistan, Handbook of Statistics on Pakistan Economy 2020](https://www.sbp.org.pk/departments/stats/PakEconomy_Handbook/Chap-2.9.pdf)


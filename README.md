# PKR Historic to Present Value Converter (آج کے حساب سے)
This simple calculator estimates how much an amount of Pakistani Rupees from past would be worth in today's Pakistani Rupees in terms of equal purchasing power.

## Methodology
Conversions are based on historic local Gold-prices (slightly modified).

`Present PKR Value = Historic PKR Amount * Current Gold Price / Historic Gold Price`

Data series for yearly average of local Gold-prices published in [SBP Statistical Handbook 2020](https://www.sbp.org.pk/departments/stats/PakEconomy_Handbook/Chap-2.9.pdf) is used. To retain a declining trend, the data series is monotonically smoothed by using forward-looking minimum values `P*(t)` for conversion where: 

`P*(t) = Min[P(t),P(t+1),P(t+2),...,P(t+n)]`

Thus, the effect of fluctuations in gold prices (observed notably in FY59-64 and FY12-15) has been removed.  

![](plot.png)

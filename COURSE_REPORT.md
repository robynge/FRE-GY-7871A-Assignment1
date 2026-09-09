# Uncertainty and sentiment in financial reports

FRE-GY 7871 A · NLP and the Investment Process · Filing dates 2021-01-01 to 2025-12-31

[Research repository](https://github.com/robynge/FRE-GY-7871A-Assignment1)

1,655 filings from 91 companies enter the text analysis. The volatility analysis uses 1,437 filings and the return analysis uses 1,437. Negative words measure adverse language; uncertainty words measure imprecision and hedging. All results describe associations in companies selected from ARK holdings.

Within companies, annual-report negative-word shares change by +0.068 percentage points per year (p < 0.001); quarterly-report uncertainty changes by -0.019 points (p = 0.059). After controlling for prior volatility, 0 of 6 uncertainty specifications are significant at 5%. The pooled negative-tone return estimate is not significant at 5% (p = 0.206).

Filing coverage ends on 2025-12-31; market observations end on 2026-09-08. Recent filings remain in text analysis even when their future price windows are unavailable. Return and volatility samples are filtered separately; both volatility specifications use the same observations. The latest included filings are 2025-12-22 for returns and 2025-12-22 for volatility.

## Table 1. Sample construction

Panel A counts holding identifiers, then companies. The frozen six-fund holdings use January 2, 2026 for ARKF and ARKX and September 4, 2026 for the other four funds. Different share classes are combined by SEC company identifier. The holdings dates define a retrospective company universe.

| Company/security filter              | Removed   | Remaining   | Unit        |
|:-------------------------------------|:----------|:------------|:------------|
| Raw holding identifiers              | 0         | 130         | identifiers |
| Funds and non-company securities     | 4         | 126         | identifiers |
| Foreign local listings               | 8         | 118         | identifiers |
| Unresolved SEC identifiers           | 3         | 115         | identifiers |
| Combine share classes by company CIK | 1         | 114         | companies   |
| No 10-K/Q in selected period         | 6         | 108         | companies   |
| 20-F / 40-F reporting companies      | 17        | 91          | companies   |

Panel B — Text sample. Counts follow this panel’s filter order.

| Filing filter                        | Removed   | Remaining   | Companies   |
|:-------------------------------------|:----------|:------------|:------------|
| All 10-K/Q and amendments            | 0         | 1,709       | 91          |
| Remove amendments and parse failures | 46        | 1,663       | 91          |
| Minimum words: 2,000 K / 1,000 Q     | 0         | 1,663       | 91          |
| Earliest company filing each quarter | 8         | 1,655       | 91          |

Panel B — Volatility sample. Counts follow this panel’s filter order.

| Filing filter                            | Removed   | Remaining   | Companies   |
|:-----------------------------------------|:----------|:------------|:------------|
| Eligible text filings                    | 0         | 1,655       | 91          |
| Usable day 0 and prior price at least $3 | 108       | 1,547       | 91          |
| Outcome window elapsed by market cutoff  | 0         | 1,547       | 91          |
| 60 observed returns before and after     | 23        | 1,524       | 90          |
| Complete pre/post volatility windows     | 0         | 1,524       | 90          |
| Accession-matched outstanding shares     | 70        | 1,454       | 85          |
| Complete liquidity and model controls    | 17        | 1,437       | 84          |

Panel B — Return sample. Counts follow this panel’s filter order.

| Filing filter                            | Removed   | Remaining   | Companies   |
|:-----------------------------------------|:----------|:------------|:------------|
| Eligible text filings                    | 0         | 1,655       | 91          |
| Usable day 0 and prior price at least $3 | 108       | 1,547       | 91          |
| Outcome window elapsed by market cutoff  | 0         | 1,547       | 91          |
| 60 observed returns before filing        | 23        | 1,524       | 90          |
| Complete four-session return window      | 0         | 1,524       | 90          |
| Accession-matched outstanding shares     | 70        | 1,454       | 85          |
| Complete liquidity and model controls    | 17        | 1,437       | 84          |

46 amendments and 0 parse failures are recorded. All 1,663 successfully parsed original filings receive tone scores before analytical sample restrictions. Market-data restrictions do not determine the text sample.

## Table 2. Tone by report type

The text sample determines descriptive statistics and trends. Proportional scores are percentages; weighted scores are equation (1) sums. Document frequencies are fitted within each analytical sample and separately by report type.

| Form   | Measure               | N     | Mean    | SD     | P25    | Median   | P75     |
|:-------|:----------------------|:------|:--------|:-------|:-------|:---------|:--------|
| 10-K   | Negative words (%)    | 406   | 2.267   | 0.421  | 1.990  | 2.287    | 2.558   |
| 10-K   | Uncertainty words (%) | 406   | 1.943   | 0.239  | 1.797  | 1.963    | 2.116   |
| 10-K   | Negative tf.idf       | 406   | 100.618 | 36.957 | 72.126 | 93.781   | 127.176 |
| 10-K   | Uncertainty tf.idf    | 406   | 15.887  | 5.707  | 11.994 | 14.996   | 19.041  |
| 10-Q   | Negative words (%)    | 1,249 | 2.044   | 0.965  | 1.168  | 1.836    | 2.963   |
| 10-Q   | Uncertainty words (%) | 1,249 | 1.816   | 0.586  | 1.318  | 1.649    | 2.408   |
| 10-Q   | Negative tf.idf       | 1,249 | 92.616  | 78.211 | 26.592 | 60.803   | 155.600 |
| 10-Q   | Uncertainty tf.idf    | 1,249 | 15.931  | 8.606  | 9.006  | 13.969   | 22.249  |

Negative/uncertainty correlations (proportional, weighted): All: 0.849, 0.918; 10-K: 0.718, 0.821; 10-Q: 0.855, 0.925.

## Table 3. Most frequent dictionary words

Each percentage divides a word count by all token occurrences in its dictionary category across the text sample.

| Rank   | Negative word   | Share %   | Uncertainty word   | Share %    |
|:-------|:----------------|:----------|:-------------------|:-----------|
| 1      | LOSS            | 5.230     | MAY                | 35.412     |
| 2      | ADVERSELY       | 4.201     | COULD              | 18.439     |
| 3      | LOSSES          | 3.149     | RISK               | 4.954      |
| 4      | CLAIMS          | 3.095     | RISKS              | 4.479      |
| 5      | ADVERSE         | 2.823     | BELIEVE            | 2.932      |
| 6      | AGAINST         | 2.485     | APPROXIMATELY      | 2.553      |
| 7      | UNABLE          | 2.026     | ASSUMPTIONS        | 1.892      |
| 8      | LITIGATION      | 1.979     | INTANGIBLE         | 1.609      |
| 9      | HARM            | 1.892     | POSSIBLE           | 1.336      |
| 10     | FAILURE         | 1.842     | UNCERTAINTIES      | 1.156      |
| 11     | FAIL            | 1.365     | FLUCTUATIONS       | 1.107      |
| 12     | IMPAIRMENT      | 1.240     | MIGHT              | 1.072      |
| 13     | DIFFICULT       | 1.178     | UNCERTAIN          | 1.024      |
| 14     | NEGATIVELY      | 1.169     | ANTICIPATED        | 0.975      |
| 15     | PENALTIES       | 1.164     | PREDICT            | 0.938      |
| 16     | NEGATIVE        | 1.047     | VOLATILITY         | 0.935      |
| 17     | DELAYS          | 0.949     | DEPEND             | 0.927      |
| 18     | RESTATED        | 0.940     | UNCERTAINTY        | 0.886      |
| 19     | DECLINE         | 0.931     | DIFFER             | 0.855      |
| 20     | DAMAGES         | 0.926     | ANTICIPATE         | 0.801      |
| 21     | LIMITATIONS     | 0.869     | CONTINGENT         | 0.775      |
| 22     | DELAY           | 0.855     | EXPOSURE           | 0.758      |
| 23     | VOLATILITY      | 0.789     | DEPENDS            | 0.673      |
| 24     | CHALLENGES      | 0.770     | VARIABLE           | 0.667      |
| 25     | FINES           | 0.725     | PENDING            | 0.646      |
| 26     | DISRUPTIONS     | 0.699     | DEPENDENT          | 0.582      |
| 27     | HARMED          | 0.698     | CONTINGENCIES      | 0.548      |
| 28     | INVESTIGATIONS  | 0.671     | PROBABLE           | 0.506      |
| 29     | BREACH          | 0.668     | ASSUMED            | 0.496      |
| 30     | INFRINGEMENT    | 0.623     | VARY               | 0.478      |

The top ten words account for 28.7% of negative tokens and 74.8% of uncertainty tokens. The active dictionaries contain 2,345 negative and 297 uncertainty words, with 40 words in both categories.

## Tone measures

The Loughran–McDonald Master Dictionary, 1993–2025 release, was updated in March 2026. A positive category value identifies an active word; a negative value records removal from that category. Only active entries enter the scores. Thus the negative category contains 2,345 words; the 10 removed entries are excluded. The proportional score divides category occurrences by all tokens in a filing.

$$
P_{cj}=\frac{\sum_{i\in c}tf_{ij}}{W_j}
$$

Equation (1) applies logarithmic term frequency and inverse document frequency. The score sums weights over category words observed in a filing.

$$
\begin{aligned}
T_{cj}=\sum_{i\in c,\,tf_{ij}>0}\frac{1+\ln(tf_{ij})}{1+\ln(a_j)}\ln\!\left(\frac{N}{df_i}\right)\\
a_j=\frac{W_j}{V_j}
\end{aligned}
$$

W is total tokens, V is distinct tokens, N is documents in the relevant estimation corpus and df is document frequency. All logarithms are natural. The text, volatility and return samples each fit their own word weights; report-type analyses also refit within form. The weighted score is measured in score units rather than percentages.

An illustrative calculation uses “LOSS LOSS RISK GAIN”, “LOSS GAIN GAIN” and “RISK RISK RISK GAIN”, with category {LOSS, RISK}. Their weighted scores are 0.8480, 0.2885 and 0.5026. These constructed documents illustrate the formula.

Primary-document text retains visible XBRL facts and excludes hidden content, separate exhibits and tables with more than 15% digits among non-space characters. Alphabetic tokens contain at least two characters and retain apostrophes and hyphens. Incorporated-by-reference text is not recovered.

TSLA's 10-Q filed 2023-10-23 contains 2.72% negative words and 1.05% uncertainty words, at percentile ranks 72 and 4, respectively. It has the largest negative-minus-uncertainty percentile gap in the text sample. This selected contrast is not representative of all filings.

Selected filing language: On October 27, 2021, the Court approved the parties’ joint stipulation that, among other things, (a) all claims against Kimbal Musk and Steve Jurvetson …

Dictionary counts identify category vocabulary; they do not determine the direction or significance of the event described.

MAY and COULD account for 53.9% of uncertainty tokens. These counts do not distinguish recurring disclosure language from newly expressed uncertainty. High negative/uncertainty correlations also mean the two measures do not provide independent evidence.

MAY occurs in 100.0% of filings and APPROXIMATELY in 99.0%. Inverse document frequency gives less weight to words appearing in most documents.

## Figure 1. Quarterly tone and VIX

![Quarterly tone and VIX](outputs/course_2021_2025/figure1.png)

10-K: 1–78 filings per observed quarter; 10-Q: 7–90 filings per observed quarter. Sparse annual-report quarters may reflect only a few companies. Company-centered means reduce baseline composition differences, but entry and exit periods can still affect this unbalanced panel. The gray dashed series is quarterly average VIX on the right axes; the latest quarter is partial when indicated. Formal trend inference uses Table 4.

## Table 4. Annual tone trends

Quarter-level means estimate the aggregate trend. Filing-level models estimate change within companies:

$$
\begin{aligned}
\bar T_q=\alpha+\beta\tau_q+\sum_{s=2}^{4}\delta_sD_{sq}+\varepsilon_q\\
T_{iq}=\alpha_i+\beta\tau_q+\sum_{s=2}^{4}\delta_sD_{sq}+\theta K_{iq}+\varepsilon_{iq}
\end{aligned}
$$

Time is elapsed years from the first sample quarter. Seasonal indicators control the reporting quarter of the year. Company effects control company mean levels; K indicates a 10-K in the pooled sample and is omitted within each report type. Saturated calendar-quarter effects are excluded because they would absorb the trend. Aggregate inference shows ordinary OLS and Newey–West t-statistics with four lags. Within-company t and p use two-way company/calendar-quarter clustering.

| Sample   | Measure     | Agg. slope   | OLS t   | NW t   | Within slope   | Within t   | p                    |
|:---------|:------------|:-------------|:--------|:-------|:---------------|:-----------|:---------------------|
| All      | Neg. %      | 0.017        | 1.733   | 1.383  | 0.009          | 0.763      | 0.455                |
| All      | Unc. %      | -0.003       | -0.585  | -0.572 | -0.008         | -1.139     | 0.269                |
| All      | Neg. tf.idf | 0.994        | 1.261   | 1.067  | 0.093          | 0.106      | 0.917                |
| All      | Unc. tf.idf | -0.173       | -1.221  | -0.958 | -0.281         | -1.931     | 0.069                |
| 10-K     | Neg. %      | 0.056        | 8.856   | 9.915  | 0.068          | 6.833      | $1.60\times 10^{-6}$ |
| 10-K     | Unc. %      | 0.013        | 2.140   | 2.265  | 0.028          | 5.751      | $1.53\times 10^{-5}$ |
| 10-K     | Neg. tf.idf | 2.019        | 2.419   | 4.050  | 2.559          | 2.979      | 0.008                |
| 10-K     | Unc. tf.idf | -0.278       | -1.505  | -2.605 | 0.033          | 0.139      | 0.891                |
| 10-Q     | Neg. %      | -0.021       | -1.561  | -1.867 | -0.008         | -0.557     | 0.584                |
| 10-Q     | Unc. %      | -0.037       | -3.036  | -3.418 | -0.019         | -2.009     | 0.059                |
| 10-Q     | Neg. tf.idf | -1.745       | -2.342  | -2.620 | -1.652         | -1.401     | 0.177                |
| 10-Q     | Unc. tf.idf | -0.545       | -4.260  | -4.849 | -0.480         | -3.066     | 0.006                |

Proportional slopes are percentage points per year; weighted slopes are score units per year. All: 91 companies, 20 quarters, 19 inference degrees of freedom; 10-K: 88 companies, 20 quarters, 19 inference degrees of freedom; 10-Q: 91 companies, 20 quarters, 19 inference degrees of freedom.

10-K negative-word shares change by +0.068 percentage points per year (p < 0.001); uncertainty-word shares change by +0.028 points (p < 0.001). The corresponding weighted slopes are +2.559 (p = 0.008) and +0.033 (p = 0.891).

10-Q negative-word shares change by -0.008 percentage points per year (p = 0.584); uncertainty-word shares change by -0.019 points (p = 0.059). The corresponding weighted slopes are -1.652 (p = 0.177) and -0.480 (p = 0.006).

Within-company estimates receive more weight than aggregate slopes because they account for company levels and reporting season. Proportional and weighted measures capture related language and are not independent replications. Sparse annual-report quarters limit interpretation of individual points in the chart.

## Filing-event design

Day 0 is the first NYSE session on or after the later of the filing date and the Eastern acceptance date. Acceptance at or after the exchange’s actual close, including an early close, moves the event to the next session. Market data include only completed sessions through 2026-09-08.

$$
\begin{aligned}
R^{[0,3],\mathrm{excess}}=\frac{P^{\mathrm{adj}}_{+3}}{P^{\mathrm{adj}}_{-1}}-\frac{SPY^{\mathrm{adj}}_{+3}}{SPY^{\mathrm{adj}}_{-1}}\\
\sigma^{\mathrm{pre}}=\sqrt{252}\,\mathrm{SD}(r_{-60},\ldots,r_{-6})\\
\sigma^{\mathrm{post}}=\sqrt{252}\,\mathrm{SD}(r_{+4},\ldots,r_{+63})
\end{aligned}
$$

The event spans four daily return intervals. Pre-filing volatility uses 55 daily returns and post-filing volatility uses 60, with sample standard deviations. Adjusted closes measure returns; nominal closes determine the \$3 price filter and company size. Later splits are reversed for nominal price and volume histories. Future returns are not imputed.

Size is the day −1 nominal price times outstanding shares from the scored filing’s cover page. Same-date share classes are summed using one class price as a proxy; future or weighted-average shares are excluded. Liquidity is mean nominal dollar volume over days [−60,−6], and prior excess return is SPY-adjusted buy-and-hold return over that interval.

The outcome models use firm effects, calendar-quarter effects and the following controls:

$$
\begin{aligned}
C_{iq}=\gamma_1\ln(\mathrm{Size}_{iq})+\gamma_2\ln(\mathrm{DollarVolume}_{iq})\\
\qquad+\gamma_3R^{\mathrm{pre,excess}}_{iq}+\theta K_{iq}\\
\sigma^{\mathrm{post}}_{iq}=\alpha_i+\lambda_q+\beta U_{iq}+C_{iq}+[\rho\sigma^{\mathrm{pre}}_{iq}]+\varepsilon_{iq}\\
R^{[0,3],\mathrm{excess}}_{iq}=\alpha_i+\lambda_q+\beta N_{iq}+C_{iq}+\rho\sigma^{\mathrm{pre}}_{iq}+\varepsilon_{iq}
\end{aligned}
$$

U is uncertainty and N is negative tone, each estimated separately as a proportion and a weighted score. The bracketed pre-volatility term is included or omitted in the paired volatility tests; it is always included in the return tests. The 10-K indicator K applies only to the pooled sample. No winsorisation is applied.

## Table 5. Uncertainty and subsequent volatility

Dependent variable: annualised volatility as a fraction. Coefficients are per unit of uncertainty fraction or weighted score. Both specifications use the same complete observations within each sample. Two-way company/quarter clustering determines t and p. All: 84 companies, 20 quarters, 19 inference degrees of freedom; 10-K: 83 companies, 20 quarters, 19 inference degrees of freedom; 10-Q: 83 companies, 20 quarters, 19 inference degrees of freedom.

| Sample   | Measure   | Pre-vol   | Coefficient           | t      | p     | N     |
|:---------|:----------|:----------|:----------------------|:-------|:------|:------|
| All      | prop      | No        | -0.169                | -0.117 | 0.908 | 1,437 |
| All      | prop      | Yes       | -0.721                | -0.567 | 0.578 | 1,437 |
| All      | tfidf     | No        | $1.69\times 10^{-4}$  | 0.206  | 0.839 | 1,437 |
| All      | tfidf     | Yes       | $-1.49\times 10^{-4}$ | -0.199 | 0.844 | 1,437 |
| 10-K     | prop      | No        | -16.264               | -0.759 | 0.457 | 349   |
| 10-K     | prop      | Yes       | -24.921               | -1.033 | 0.315 | 349   |
| 10-K     | tfidf     | No        | 0.004                 | 0.555  | 0.586 | 349   |
| 10-K     | tfidf     | Yes       | 0.005                 | 0.905  | 0.377 | 349   |
| 10-Q     | prop      | No        | 3.207                 | 1.338  | 0.197 | 1,088 |
| 10-Q     | prop      | Yes       | 2.221                 | 0.975  | 0.342 | 1,088 |
| 10-Q     | tfidf     | No        | 0.003                 | 2.171  | 0.043 | 1,088 |
| 10-Q     | tfidf     | Yes       | 0.002                 | 1.602  | 0.126 | 1,088 |

Proportional uncertainty: a one-standard-deviation increase corresponds to -0.38 percentage points of annualised volatility after controlling for prior volatility (95% interval [-1.77, +1.01]). The uncontrolled effect is -0.09 points (p = 0.908), compared with p = 0.578 after control. Adding the control changes the estimated effect by -0.29 points. This comparison tests incremental association beyond existing volatility.

Weighted uncertainty: a one-standard-deviation increase corresponds to -0.14 percentage points of annualised volatility after controlling for prior volatility (95% interval [-1.63, +1.34]). The uncontrolled effect is +0.16 points (p = 0.839), compared with p = 0.844 after control. Adding the control changes the estimated effect by -0.30 points. This comparison tests incremental association beyond existing volatility.

For 10-Q weighted uncertainty, the effect per tone standard deviation changes from +2.21 to +1.60 volatility percentage points after adding prior volatility (p = 0.043 and = 0.126). The controlled proportional-score estimate has p = 0.342. Differences across weighting schemes and multiple unadjusted tests limit the strength of an isolated significant association.

## Table 6. Negative sentiment and filing-period excess return

Dependent variable: SPY-adjusted four-session buy-and-hold return as a fraction. All models include log size, log dollar volume, prior excess return, pre-filing volatility, company effects and calendar-quarter effects; pooled models also include the 10-K indicator. Coefficients are per unit of negative-word fraction or weighted score. t and p use two-way company/quarter clustering. All: 84 companies, 20 quarters, 19 inference degrees of freedom; 10-K: 83 companies, 20 quarters, 19 inference degrees of freedom; 10-Q: 83 companies, 20 quarters, 19 inference degrees of freedom.

| Sample   | Measure   | Coef.                 | t      | p     | Effect pp   | MDE pp   | N     |
|:---------|:----------|:----------------------|:-------|:------|:------------|:---------|:------|
| All      | prop      | -0.958                | -1.310 | 0.206 | -0.820      | 1.837    | 1,437 |
| All      | tfidf     | $-1.46\times 10^{-4}$ | -1.259 | 0.223 | -1.060      | 2.471    | 1,437 |
| 10-K     | prop      | -7.560                | -0.873 | 0.394 | -3.066      | 10.308   | 349   |
| 10-K     | tfidf     | $-8.16\times 10^{-4}$ | -1.074 | 0.296 | -3.107      | 8.490    | 349   |
| 10-Q     | prop      | -2.723                | -2.170 | 0.043 | -2.592      | 3.506    | 1,088 |
| 10-Q     | tfidf     | $-3.53\times 10^{-4}$ | -2.106 | 0.049 | -2.698      | 3.759    | 1,088 |

$$
\mathrm{MDE}^{\mathrm{pp}}_{80,1\mathrm{SD}}=100\left(t_{0.975,\nu}+\Phi^{-1}(0.8)\right)\mathrm{SE}(\hat\beta)\,s_{\mathrm{tone}}
$$

Effect and minimum detectable effect (MDE) are return percentage points per one tone standard deviation. MDE approximates 80% power for a two-sided 5% test using the stated inference degrees of freedom. It measures precision rather than observed power.

All: a one-standard-deviation increase in proportional negative tone corresponds to -0.82 return percentage points (p = 0.206), with an approximate detectable effect of 1.84 points. The weighted-score effect is -1.06 points (p = 0.223).

10-K: a one-standard-deviation increase in proportional negative tone corresponds to -3.07 return percentage points (p = 0.394), with an approximate detectable effect of 10.31 points. The weighted-score effect is -3.11 points (p = 0.296).

10-Q: a one-standard-deviation increase in proportional negative tone corresponds to -2.59 return percentage points (p = 0.043), with an approximate detectable effect of 3.51 points. The weighted-score effect is -2.70 points (p = 0.049).

Statistical insignificance does not establish zero price response. Earnings releases can overlap the filing window and drive the same returns. Correlated specifications and multiple unadjusted tests also limit the interpretation of isolated significant estimates.

## Report-type differences and limitations

The within-company trends supported by both weighting schemes at the 5% level are: 10-K negative tone increase. These receive more weight than results that depend on the weighting scheme, although the two measures are correlated. Volatility associations assess incremental information after existing risk is controlled; short-window returns have separate precision and earnings-overlap limitations.

Negative proportional-score SD is 0.421 percentage points for 10-Ks and 0.965 for 10-Qs. Report length, repeated language and changing content may affect dispersion; this analysis does not identify their separate contributions.

Uncertainty proportional-score SD is 0.239 percentage points for 10-Ks and 0.586 for 10-Qs. Report length, repeated language and changing content may affect dispersion; this analysis does not identify their separate contributions.

10-Ks provide annual business and risk disclosures, while 10-Qs provide quarterly updates. More words do not necessarily imply more new information. Different significance levels across forms do not establish that coefficients differ.

1 of 12 estimable within-company trend tests change 5% significance between company-only and two-way clustering. The two-way estimates use 20 time clusters across samples, so finite-sample inference remains approximate. All four tone trends, both volatility specifications and both return measures are reported for pooled and separate report-type samples.

Of 175 distinct securities held on May 6, 2021, 106 (60.6%) do not match the frozen 2026 holdings by normalized ticker or valid CUSIP. Identity changes, mergers and share classes mean these absences do not all represent company failures.

The 2026 holdings selection, mixed holdings dates and incomplete historical identifiers limit generalisation. Market-window and share-count availability impose additional selection on the outcome samples. Full-corpus word weights use later filings and the current dictionary is applied retrospectively. The estimates therefore describe retrospective conditional associations, not causal effects or an implementable live strategy.

## Sources

[Loughran and McDonald (2011), Journal of Finance 66(1), 35–65: When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks](https://doi.org/10.1111/j.1540-6261.2010.01625.x)

[Loughran–McDonald Master Dictionary, 1993–2025 release; updated March 2026; accessed September 9, 2026](https://sraf.nd.edu/loughranmcdonald-master-dictionary/)

[SEC EDGAR: filings and company facts](https://www.sec.gov/edgar)

[Yahoo Finance: price, volume, corporate actions and market indices](https://finance.yahoo.com/)

[ARK holdings archive](https://github.com/robynge/ark-routine)

[FRE-GY 7871 A course holdings and assignment materials](https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1)

[Illustrative SEC filing](https://www.sec.gov/Archives/edgar/data/1318605/000162828023034847/tsla-20230930.htm)

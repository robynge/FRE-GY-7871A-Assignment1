# Uncertainty and sentiment in financial reports

FRE-GY 7871 A · NLP and the Investment Process · Filing dates 2021-01-01 to 2025-12-31

[Research repository](https://github.com/robynge/FRE-GY-7871A-Assignment1)

This research asks whether financial-report language changes over time and helps explain subsequent stock volatility or filing-period returns. It follows 85 companies held by the six ARK ETFs on September 9, 2026, using 1,531 eligible historical filings. It is a study of today’s holdings through time, not the historical ARK portfolio.

Filings run from January 1, 2021 through December 31, 2025, the assignment window. Company selection still uses the six September 9, 2026 holdings lists.

## What the percentages mean

Uncertainty word share is the percentage of retained words that belong to the financial uncertainty dictionary, including MAY, COULD and APPROXIMATELY. If a filing has 10,000 words and these words occur 200 times, its share is 2%: two occurrences per 100 words. Repeated uses count each time. Negative word share counts adverse financial vocabulary in the same way.

These percentages describe the writing. They are not the chance of a loss, a business failure or a stock-price fall. Annual reports (10-K) and quarterly reports (10-Q) are kept separate because their contents differ. Risk-section changes and repeated text can move the shares.

## Observed word shares over time

| Filing year   | Annual negative share   | Annual uncertainty share   | Quarterly negative share   | Quarterly uncertainty share   |
|:--------------|:------------------------|:---------------------------|:---------------------------|:------------------------------|
| 2021          | 2.09%                   | 1.87%                      | 1.99%                      | 1.83%                         |
| 2022          | 2.20%                   | 1.92%                      | 2.07%                      | 1.86%                         |
| 2023          | 2.30%                   | 1.96%                      | 2.08%                      | 1.84%                         |
| 2024          | 2.35%                   | 1.98%                      | 2.00%                      | 1.77%                         |
| 2025          | 2.40%                   | 2.02%                      | 2.01%                      | 1.79%                         |

Each percentage is the equal-weighted average of individual filing shares in that calendar filing year. For example, 2% means an average of two category-word occurrences per 100 words in each filing. The companies and number of filings can vary by year; these observed averages alone do not prove a common company-level trend. 

## Question 1  Is the language changing

Annual-report negative word share averages 2.09% in 2021 and 2.40% in 2025. After allowing for company differences and reporting season, both scoring methods also support an upward annual-report trend. This concerns adverse vocabulary; it does not establish that operating conditions worsened.

## Question 2  Does uncertain language precede more volatile stock returns

We compare the language score with stock-price fluctuations over the following 60 trading days, starting on day +4 after the filing event. We run the comparison twice: first without accounting for the stock’s prior volatility, then with it. The second test asks whether language adds information beyond how volatile the stock already was.

After prior volatility is included, the tests support an association in 0 of 6 comparisons: 0 with higher volatility and 0 with lower volatility. The evidence does not support a consistent association across report types and scoring methods. The model-by-model comparison appears in Table 5. Retrospective associations do not establish a usable trading forecast.

## Question 3  Does negative language accompany weaker stock returns

We measure the stock’s return over four trading sessions beginning on the filing event day, minus the SPY return over the same sessions. For illustration, if the stock gains 1% while SPY gains 2%, it underperforms by one percentage point.

The return tests support an association in 2 of 6 comparisons: 2 with lower returns and 0 with higher returns. The supported estimates and their directions are shown separately in Table 6; a significant result is not proof that filing language caused the return. Earnings news can coincide with the filing, and the short return window limits the precision of the estimates.

## Detailed evidence and methods

The following six tables document sample selection, language levels, word frequencies and the three research questions. All means, trends and model estimates use the stated sample; the separate company-monitoring analysis uses same-company year-on-year comparisons.

Filing coverage ends on 2025-12-31; market observations end on 2026-09-08. Recent filings remain in text analysis even when their future price windows are unavailable. Return and volatility samples are filtered separately; both volatility specifications use the same observations. The latest included filings are 2025-12-22 for returns and 2025-12-22 for volatility.

## Table 1. Sample construction

Panel A counts holding identifiers, then companies. All six holdings lists are dated September 9, 2026. Different share classes are combined by SEC company identifier. The holdings date selects today’s company universe for retrospective analysis.

| Company/security filter                 | Removed   | Remaining   | Unit        |
|:----------------------------------------|:----------|:------------|:------------|
| Raw holding identifiers                 | 0         | 121         | identifiers |
| Funds and non-company securities        | 3         | 118         | identifiers |
| Foreign local listings                  | 5         | 113         | identifiers |
| Unresolved SEC identifiers              | 0         | 113         | identifiers |
| Combine share classes by company CIK    | 1         | 112         | companies   |
| No 10-K/Q in selected period            | 8         | 104         | companies   |
| 20-F / 40-F reporting companies         | 18        | 86          | companies   |
| No qualifying report evidence by cutoff | 1         | 85          | companies   |

Panel B — Text sample. Counts follow this panel’s filter order.

| Filing filter                        | Removed   | Remaining   | Companies   |
|:-------------------------------------|:----------|:------------|:------------|
| All 10-K/Q and amendments            | 0         | 1,581       | 85          |
| Remove amendments and parse failures | 41        | 1,540       | 85          |
| Minimum words: 2,000 K / 1,000 Q     | 0         | 1,540       | 85          |
| Earliest company filing each quarter | 9         | 1,531       | 85          |

Panel B — Volatility sample. Counts follow this panel’s filter order.

| Filing filter                            | Removed   | Remaining   | Companies   |
|:-----------------------------------------|:----------|:------------|:------------|
| Eligible text filings                    | 0         | 1,531       | 85          |
| Usable day 0 and prior price at least $3 | 116       | 1,415       | 85          |
| Outcome window elapsed by market cutoff  | 0         | 1,415       | 85          |
| 60 observed returns before and after     | 23        | 1,392       | 84          |
| Complete pre/post volatility windows     | 0         | 1,392       | 84          |
| Accession-matched outstanding shares     | 69        | 1,323       | 79          |
| Complete liquidity and model controls    | 17        | 1,306       | 78          |

Panel B — Return sample. Counts follow this panel’s filter order.

| Filing filter                            | Removed   | Remaining   | Companies   |
|:-----------------------------------------|:----------|:------------|:------------|
| Eligible text filings                    | 0         | 1,531       | 85          |
| Usable day 0 and prior price at least $3 | 116       | 1,415       | 85          |
| Outcome window elapsed by market cutoff  | 0         | 1,415       | 85          |
| 60 observed returns before filing        | 23        | 1,392       | 84          |
| Complete four-session return window      | 0         | 1,392       | 84          |
| Accession-matched outstanding shares     | 69        | 1,323       | 79          |
| Complete liquidity and model controls    | 17        | 1,306       | 78          |

41 amendments and 0 parse failures are recorded. All 1,540 successfully parsed original filings receive tone scores before analytical sample restrictions. Market-data restrictions do not determine the text sample.

## Table 2. Observed language levels by report type

The text sample determines descriptive statistics and trends. Proportional scores are percentages; weighted scores are equation (1) sums. Document frequencies are fitted within each analytical sample and separately by report type.

| Form   | Measure               | N     | Mean    | SD     | P25    | Median   | P75     |
|:-------|:----------------------|:------|:--------|:-------|:-------|:---------|:--------|
| 10-K   | Negative words (%)    | 375   | 2.279   | 0.427  | 1.999  | 2.295    | 2.571   |
| 10-K   | Uncertainty words (%) | 375   | 1.954   | 0.238  | 1.819  | 1.975    | 2.120   |
| 10-K   | Negative tf.idf       | 375   | 101.199 | 36.976 | 71.446 | 94.696   | 131.387 |
| 10-K   | Uncertainty tf.idf    | 375   | 16.043  | 5.671  | 12.198 | 15.221   | 18.963  |
| 10-Q   | Negative words (%)    | 1,156 | 2.028   | 0.976  | 1.157  | 1.755    | 2.977   |
| 10-Q   | Uncertainty words (%) | 1,156 | 1.818   | 0.582  | 1.326  | 1.648    | 2.406   |
| 10-Q   | Negative tf.idf       | 1,156 | 92.937  | 80.486 | 25.474 | 57.189   | 158.280 |
| 10-Q   | Uncertainty tf.idf    | 1,156 | 16.049  | 8.833  | 8.973  | 13.749   | 22.860  |

Average uncertainty word share is 1.95% in annual reports and 1.82% in quarterly reports. These are observed averages by report type, not a time-series increase or decrease.

Negative/uncertainty correlations (proportional, weighted): All: 0.852, 0.922; 10-K: 0.735, 0.816; 10-Q: 0.857, 0.931.

## Table 3. Most frequent dictionary words

Each percentage divides a word count by all token occurrences in its dictionary category across the text sample.

| Rank   | Negative word   | Share %   | Uncertainty word   | Share %    |
|:-------|:----------------|:----------|:-------------------|:-----------|
| 1      | LOSS            | 5.114     | MAY                | 35.555     |
| 2      | ADVERSELY       | 4.288     | COULD              | 18.503     |
| 3      | CLAIMS          | 3.087     | RISK               | 4.821      |
| 4      | LOSSES          | 2.993     | RISKS              | 4.407      |
| 5      | ADVERSE         | 2.884     | BELIEVE            | 2.915      |
| 6      | AGAINST         | 2.546     | APPROXIMATELY      | 2.571      |
| 7      | UNABLE          | 2.029     | ASSUMPTIONS        | 1.915      |
| 8      | LITIGATION      | 1.991     | INTANGIBLE         | 1.499      |
| 9      | FAILURE         | 1.882     | POSSIBLE           | 1.342      |
| 10     | HARM            | 1.730     | UNCERTAINTIES      | 1.144      |
| 11     | FAIL            | 1.366     | MIGHT              | 1.123      |
| 12     | IMPAIRMENT      | 1.186     | FLUCTUATIONS       | 1.076      |
| 13     | DIFFICULT       | 1.185     | UNCERTAIN          | 1.035      |
| 14     | PENALTIES       | 1.182     | ANTICIPATED        | 0.986      |
| 15     | NEGATIVELY      | 1.171     | PREDICT            | 0.947      |
| 16     | NEGATIVE        | 1.034     | DEPEND             | 0.932      |
| 17     | DELAYS          | 0.964     | VOLATILITY         | 0.913      |
| 18     | DAMAGES         | 0.953     | UNCERTAINTY        | 0.883      |
| 19     | RESTATED        | 0.939     | DIFFER             | 0.864      |
| 20     | DECLINE         | 0.908     | ANTICIPATE         | 0.814      |
| 21     | DELAY           | 0.895     | CONTINGENT         | 0.806      |
| 22     | LIMITATIONS     | 0.866     | EXPOSURE           | 0.733      |
| 23     | VOLATILITY      | 0.771     | VARIABLE           | 0.678      |
| 24     | CHALLENGES      | 0.770     | PENDING            | 0.657      |
| 25     | FINES           | 0.735     | DEPENDS            | 0.651      |
| 26     | DISRUPTIONS     | 0.681     | DEPENDENT          | 0.600      |
| 27     | BREACH          | 0.676     | CONTINGENCIES      | 0.523      |
| 28     | INVESTIGATIONS  | 0.668     | PROBABLE           | 0.499      |
| 29     | INFRINGEMENT    | 0.627     | ASSUMED            | 0.484      |
| 30     | HARMED          | 0.620     | VARY               | 0.481      |

The top ten words account for 28.5% of negative tokens and 74.7% of uncertainty tokens. The active dictionaries contain 2,345 negative and 297 uncertainty words, with 40 words in both categories.

Percentage points (pp) measure the difference between two percentages. A rise from 2.0% to 2.5% is +0.5 percentage points, equivalent to five more category-word occurrences per 1,000 words. It is a 25% relative increase, not a 0.5% relative increase. The separate weighted score reduces the contribution of vocabulary used in most filings; its unit is score units, not percent.

## Statistical comparisons

An estimated annual trend describes the average change per elapsed year after accounting for company differences and reporting season. It is not a specific company’s latest year-on-year change. A one-standard-deviation (1 SD) difference means a difference equal to the typical spread of language scores in that model’s sample. It is not a one-percentage-point increase in word share.

A p value assesses how incompatible the estimate is with a zero association under the model assumptions; below 0.05 is the conventional threshold used here. It is not the probability that a conclusion is true. A 95% confidence interval describes estimation uncertainty; an interval including zero permits either sign. Regression results are estimated associations, not observed before-and-after changes or proof of causality.

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

MAY and COULD account for 54.1% of uncertainty tokens. These counts do not distinguish recurring disclosure language from newly expressed uncertainty. High negative/uncertainty correlations also mean the two measures do not provide independent evidence.

MAY occurs in 100.000% of filings and APPROXIMATELY in 99.020%. MAY therefore has inverse-document-frequency weight ln(N/N) = 0: its count contributes to word share but contributes nothing to the weighted score. APPROXIMATELY receives a small positive weight. This removes vocabulary that provides little information about which document is being read; it does not determine whether the remaining language predicts stock outcomes.

## Effect of weighting on filing rankings

Across the same 1,531 filings with pooled text-sample weights, the rank correlation between word share and weighted score is 0.699 for uncertainty and 0.823 for negative language. A rank correlation of 1 means the methods order filings identically; lower values indicate greater reordering. This compares two ways of measuring the same category, not negative language against uncertainty.

The average absolute movement in percentile position is 17.87 points for uncertainty and 13.07 for negative language. Moving from the 80th to the 60th percentile would be a 20-point movement; these units describe rank position, not a change in word share. Weighting changes uncertainty rankings more in this sample. This compares ranking sensitivity and does not by itself demonstrate better prediction.

## Figure 1. Quarterly tone and VIX

![Quarterly tone and VIX](outputs/course_2021_2025/figure1.png)

10-K: 1–73 filings per observed quarter; 10-Q: 6–85 filings per observed quarter. Sparse annual-report quarters may reflect only a few companies. Company-centered means reduce baseline composition differences, but entry and exit periods can still affect this unbalanced panel. The gray dashed series is quarterly average VIX on the right axes; the latest quarter is partial when indicated. Formal trend inference uses Table 4.

## Table 4. Estimated language change per year

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
| All      | Neg. %      | 0.018        | 1.817   | 1.498  | 0.010          | 0.814      | 0.426                |
| All      | Unc. %      | -0.004       | -0.611  | -0.600 | -0.009         | -1.159     | 0.261                |
| All      | Neg. tf.idf | 1.004        | 1.168   | 0.989  | 0.050          | 0.053      | 0.959                |
| All      | Unc. tf.idf | -0.158       | -1.018  | -0.780 | -0.282         | -1.804     | 0.087                |
| 10-K     | Neg. %      | 0.054        | 7.444   | 7.540  | 0.071          | 6.949      | $6.77\times 10^{-6}$ |
| 10-K     | Unc. %      | 0.019        | 2.518   | 2.808  | 0.029          | 5.594      | $6.62\times 10^{-5}$ |
| 10-K     | Neg. tf.idf | 1.433        | 1.269   | 2.157  | 2.617          | 2.818      | 0.014                |
| 10-K     | Unc. tf.idf | -0.409       | -1.482  | -1.978 | 0.030          | 0.112      | 0.912                |
| 10-Q     | Neg. %      | -0.022       | -1.612  | -2.005 | -0.008         | -0.509     | 0.617                |
| 10-Q     | Unc. %      | -0.039       | -3.081  | -3.429 | -0.021         | -2.010     | 0.059                |
| 10-Q     | Neg. tf.idf | -1.978       | -2.427  | -2.627 | -1.734         | -1.371     | 0.186                |
| 10-Q     | Unc. tf.idf | -0.554       | -3.971  | -4.380 | -0.476         | -2.833     | 0.011                |

All combines annual and quarterly reports. Neg. and Unc. mean negative and uncertainty language; % identifies word share, and tf.idf identifies the weighted score. Agg. means the quarterly-average model; Within means the company-adjusted model. OLS and NW t are alternative statistical test values. Proportional slopes are percentage points per year; weighted slopes are score units per year. All: 85 companies, 20 quarters, 19 inference degrees of freedom; 10-K: 82 companies, 15 quarters, 14 inference degrees of freedom; 10-Q: 85 companies, 20 quarters, 19 inference degrees of freedom.

10-K negative-word shares change by +0.071 percentage points per year (p < 0.001); uncertainty-word shares change by +0.029 points (p < 0.001). The corresponding weighted slopes are +2.617 (p = 0.014) and +0.030 (p = 0.912).

10-Q negative-word shares change by -0.008 percentage points per year (p = 0.617); uncertainty-word shares change by -0.021 points (p = 0.059). The corresponding weighted slopes are -1.734 (p = 0.186) and -0.476 (p = 0.011).

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

## Comparison before and after controlling prior stock volatility

| Language measure   | Without prior volatility   | With prior volatility   |
|:-------------------|:---------------------------|:------------------------|
| Word share         | +0.01 pp; p = 0.992        | -0.29 pp; p = 0.689     |
| Weighted score     | +0.25 pp; p = 0.782        | -0.06 pp; p = 0.942     |

Each number is the estimated difference in annualised stock volatility associated with a 1 SD higher uncertainty score. The two columns compare model specifications, not earlier and later stock volatility. A +1 pp effect would mean, for example, an estimated 40% versus 41% annualised volatility, with other model variables held fixed; those levels are illustrative.

## Table 5. Uncertainty and subsequent volatility

All combines report types; prop means word share, tfidf means weighted score, and Pre-vol identifies whether prior volatility is controlled. N is the number of filings. The coefficient is the model slope, while t and p describe its statistical evidence. Dependent variable: annualised volatility as a fraction. Coefficients are per unit of uncertainty fraction or weighted score. Both specifications use the same complete observations within each sample. Two-way company/quarter clustering determines t and p. All: 78 companies, 20 quarters, 19 inference degrees of freedom; 10-K: 76 companies, 15 quarters, 14 inference degrees of freedom; 10-Q: 77 companies, 20 quarters, 19 inference degrees of freedom.

| Sample   | Measure   | Pre-vol   | Coefficient           | t      | p     | N     |
|:---------|:----------|:----------|:----------------------|:-------|:------|:------|
| All      | prop      | No        | 0.015                 | 0.010  | 0.992 | 1,306 |
| All      | prop      | Yes       | -0.555                | -0.407 | 0.689 | 1,306 |
| All      | tfidf     | No        | $2.61\times 10^{-4}$  | 0.280  | 0.782 | 1,306 |
| All      | tfidf     | Yes       | $-6.33\times 10^{-5}$ | -0.074 | 0.942 | 1,306 |
| 10-K     | prop      | No        | -18.600               | -0.807 | 0.433 | 317   |
| 10-K     | prop      | Yes       | -26.900               | -1.049 | 0.312 | 317   |
| 10-K     | tfidf     | No        | 0.003                 | 0.453  | 0.657 | 317   |
| 10-K     | tfidf     | Yes       | 0.005                 | 0.695  | 0.499 | 317   |
| 10-Q     | prop      | No        | 3.365                 | 1.365  | 0.188 | 989   |
| 10-Q     | prop      | Yes       | 2.361                 | 1.006  | 0.327 | 989   |
| 10-Q     | tfidf     | No        | 0.003                 | 2.250  | 0.036 | 989   |
| 10-Q     | tfidf     | Yes       | 0.002                 | 1.672  | 0.111 | 989   |

Proportional uncertainty: a one-standard-deviation increase corresponds to -0.29 percentage points of annualised volatility after controlling for prior volatility (95% interval [-1.77, +1.20]). The uncontrolled effect is +0.01 points (p = 0.992), compared with p = 0.689 after control. Adding the control changes the estimated effect by -0.30 points. This comparison tests incremental association beyond existing volatility.

Weighted uncertainty: a one-standard-deviation increase corresponds to -0.06 percentage points of annualised volatility after controlling for prior volatility (95% interval [-1.80, +1.67]). The uncontrolled effect is +0.25 points (p = 0.782), compared with p = 0.942 after control. Adding the control changes the estimated effect by -0.31 points. This comparison tests incremental association beyond existing volatility.

For 10-Q weighted uncertainty, the effect per tone standard deviation changes from +2.40 to +1.75 volatility percentage points after adding prior volatility (p = 0.036 and = 0.111). The controlled proportional-score estimate has p = 0.327. Differences across weighting schemes and multiple unadjusted tests limit the strength of an isolated significant association.

## Table 6. Negative sentiment and filing-period excess return

Dependent variable: SPY-adjusted four-session buy-and-hold return as a fraction. All models include log size, log dollar volume, prior excess return, pre-filing volatility, company effects and calendar-quarter effects; pooled models also include the 10-K indicator. Coefficients are per unit of negative-word fraction or weighted score. t and p use two-way company/quarter clustering. All: 78 companies, 20 quarters, 19 inference degrees of freedom; 10-K: 76 companies, 15 quarters, 14 inference degrees of freedom; 10-Q: 77 companies, 20 quarters, 19 inference degrees of freedom.

| Sample   | Measure   | Coef.                 | t      | p     | Effect pp   | MDE pp   | N     |
|:---------|:----------|:----------------------|:-------|:------|:------------|:---------|:------|
| All      | prop      | -1.022                | -1.319 | 0.203 | -0.887      | 1.974    | 1,306 |
| All      | tfidf     | $-1.56\times 10^{-4}$ | -1.338 | 0.197 | -1.169      | 2.564    | 1,306 |
| 10-K     | prop      | -5.210                | -0.624 | 0.543 | -2.139      | 10.236   | 317   |
| 10-K     | tfidf     | $-6.95\times 10^{-4}$ | -0.827 | 0.422 | -2.667      | 9.630    | 317   |
| 10-Q     | prop      | -3.152                | -2.614 | 0.017 | -3.039      | 3.411    | 989   |
| 10-Q     | tfidf     | $-3.72\times 10^{-4}$ | -2.275 | 0.035 | -2.925      | 3.774    | 989   |

$$
\mathrm{MDE}^{\mathrm{pp}}_{80,1\mathrm{SD}}=100\left(t_{0.975,\nu}+\Phi^{-1}(0.8)\right)\mathrm{SE}(\hat\beta)\,s_{\mathrm{tone}}
$$

All combines report types; prop means word share and tfidf means weighted score. N counts filings. Coef. is the model slope and t is its statistical test value. Effect and minimum detectable effect (MDE) are return percentage points per one tone standard deviation. MDE approximates 80% power for a two-sided 5% test using the stated inference degrees of freedom. It measures precision rather than observed power.

All: a one-standard-deviation increase in proportional negative tone corresponds to -0.89 return percentage points (p = 0.203), with an approximate detectable effect of 1.97 points. The weighted-score effect is -1.17 points (p = 0.197).

10-K: a one-standard-deviation increase in proportional negative tone corresponds to -2.14 return percentage points (p = 0.543), with an approximate detectable effect of 10.24 points. The weighted-score effect is -2.67 points (p = 0.422).

10-Q: a one-standard-deviation increase in proportional negative tone corresponds to -3.04 return percentage points (p = 0.017), with an approximate detectable effect of 3.41 points. The weighted-score effect is -2.93 points (p = 0.035).

Statistical insignificance does not establish zero price response. Earnings releases can overlap the filing window and drive the same returns. Correlated specifications and multiple unadjusted tests also limit the interpretation of isolated significant estimates.

## Report-type differences and limitations

The within-company trends supported by both weighting schemes at the 5% level are: 10-K negative tone increase. These receive more weight than results that depend on the weighting scheme, although the two measures are correlated. Volatility associations assess incremental information after existing risk is controlled; short-window returns have separate precision and earnings-overlap limitations.

10-Ks provide annual business and risk disclosures, while 10-Qs provide quarterly updates. More words do not necessarily imply more new information. Different significance levels across forms do not establish that coefficients differ.

1 of 12 estimable within-company trend tests change 5% significance between company-only and two-way clustering. The two-way estimates use 15, 20 time clusters across samples, so finite-sample inference remains approximate. All four tone trends, both volatility specifications and both return measures are reported for pooled and separate report-type samples.

Selection from September 9, 2026 holdings limits generalisation beyond today’s selected companies. Market-window and share-count availability impose additional selection on the outcome samples. Full-corpus word weights use later filings and the current dictionary is applied retrospectively. The estimates therefore describe retrospective conditional associations, not causal effects or an implementable live strategy.

## Sources

[Loughran and McDonald (2011), Journal of Finance 66(1), 35–65: When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks](https://doi.org/10.1111/j.1540-6261.2010.01625.x)

[Loughran–McDonald Master Dictionary, 1993–2025 release; updated March 2026; accessed September 9, 2026](https://sraf.nd.edu/loughranmcdonald-master-dictionary/)

[SEC EDGAR: filings and company facts](https://www.sec.gov/edgar)

[Yahoo Finance: price, volume, corporate actions and market indices](https://finance.yahoo.com/)

[ARK holdings archive](https://github.com/robynge/ark-routine)

[FRE-GY 7871 A course holdings and assignment materials](https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1)

[Illustrative SEC filing](https://www.sec.gov/Archives/edgar/data/1318605/000162828023034847/tsla-20230930.htm)

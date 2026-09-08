# Uncertainty and sentiment in financial reports

FRE-GY 7871 A · NLP and the Investment Process · Filing dates 2021–2025

GitHub: https://github.com/robynge/FRE-GY-7871A-Assignment1

1,437 filings from 84 companies enter the common analysis sample. Negative-word frequency measures adverse language; uncertainty-word frequency measures imprecision and hedging. The tests examine changes within companies, subsequent realised volatility and four-session excess returns around filing.

## Table 1. Sample construction

Panel A counts holding identifiers, then companies. The frozen six-fund snapshot contains 130 raw tickers, rather than the approximately 124 companies in the assignment description. ARKF and ARKX are dated January 2, 2026; the other four funds are dated September 4, 2026. The separate September 4 holdings snapshot contains 121 raw tickers. The frozen classroom sample is retained; different share classes are combined by SEC company identifier.

| Company/security filter              | Removed   | Remaining   | Unit        |
|:-------------------------------------|:----------|:------------|:------------|
| Raw holding identifiers              | 0         | 130         | identifiers |
| Funds and non-company securities     | 4         | 126         | identifiers |
| Foreign local listings               | 8         | 118         | identifiers |
| Unresolved SEC identifiers           | 3         | 115         | identifiers |
| Combine share classes by company CIK | 1         | 114         | companies   |
| First 10-K/Q after 2025              | 6         | 108         | companies   |
| 20-F / 40-F reporting companies      | 17        | 91          | companies   |

Panel B counts filings. Company exclusions above have no observed 10-K/Q count to subtract from this panel.

| Filing filter                            | Removed   | Remaining   | Companies   |
|:-----------------------------------------|:----------|:------------|:------------|
| All 10-K/Q and amendments                | 0         | 1,709       | 91          |
| Remove amendments and parse failures     | 46        | 1,663       | 91          |
| Minimum words: 2,000 K / 1,000 Q         | 0         | 1,663       | 91          |
| Earliest company filing each quarter     | 8         | 1,655       | 91          |
| Usable day 0 and prior price at least $3 | 108       | 1,547       | 91          |
| 60 observed returns before and after     | 23        | 1,524       | 90          |
| Complete event and volatility windows    | 0         | 1,524       | 90          |
| Accession-matched outstanding shares     | 70        | 1,454       | 85          |
| Complete liquidity and model controls    | 17        | 1,437       | 84          |

46 amendments and 0 parse failures are recorded. The acceptance-time rule moves 938 events before market filters and 789 in the final sample. All models use the same complete observations within each stated sample.

## Table 2. Tone by report type

Proportional scores are percentages; weighted scores are equation (1) sums. Document frequencies are fitted separately within each form here, in Figure 1 and in form-specific regressions. Full-sample regressions fit the pooled corpus.

| Form   | Measure               | N     | Mean    | SD     | P25    | Median   | P75     |
|:-------|:----------------------|:------|:--------|:-------|:-------|:---------|:--------|
| 10-K   | Negative words (%)    | 349   | 2.321   | 0.401  | 2.067  | 2.348    | 2.580   |
| 10-K   | Uncertainty words (%) | 349   | 1.939   | 0.243  | 1.794  | 1.968    | 2.118   |
| 10-K   | Negative tf.idf       | 349   | 100.634 | 38.306 | 71.369 | 92.346   | 127.874 |
| 10-K   | Uncertainty tf.idf    | 349   | 15.788  | 5.821  | 11.705 | 14.647   | 18.971  |
| 10-Q   | Negative words (%)    | 1,088 | 2.118   | 0.942  | 1.260  | 1.970    | 2.994   |
| 10-Q   | Uncertainty words (%) | 1,088 | 1.817   | 0.581  | 1.326  | 1.664    | 2.408   |
| 10-Q   | Negative tf.idf       | 1,088 | 92.773  | 76.745 | 28.443 | 64.511   | 148.036 |
| 10-Q   | Uncertainty tf.idf    | 1,088 | 15.827  | 8.462  | 9.274  | 14.092   | 21.343  |

Sentiment/uncertainty correlations (proportional, weighted): 10-K: 0.724, 0.838; 10-Q: 0.839, 0.922.

## Table 3. Most frequent dictionary words

Each percentage divides a word count by the total token count in that dictionary category across the final sample.

| Rank   | Negative word   | Share %   | Uncertainty word   | Share %    |
|:-------|:----------------|:----------|:-------------------|:-----------|
| 1      | LOSS            | 5.138     | MAY                | 34.642     |
| 2      | ADVERSELY       | 3.934     | COULD              | 18.251     |
| 3      | LOSSES          | 3.218     | RISK               | 5.124      |
| 4      | CLAIMS          | 2.925     | RISKS              | 4.529      |
| 5      | ADVERSE         | 2.757     | BELIEVE            | 2.925      |
| 6      | AGAINST         | 2.427     | APPROXIMATELY      | 2.690      |
| 7      | LITIGATION      | 1.953     | ASSUMPTIONS        | 1.919      |
| 8      | UNABLE          | 1.932     | INTANGIBLE         | 1.759      |
| 9      | HARM            | 1.902     | POSSIBLE           | 1.276      |
| 10     | FAILURE         | 1.773     | UNCERTAINTIES      | 1.163      |
| 11     | FAIL            | 1.306     | FLUCTUATIONS       | 1.143      |
| 12     | IMPAIRMENT      | 1.256     | MIGHT              | 1.124      |
| 13     | NEGATIVELY      | 1.150     | UNCERTAIN          | 1.034      |
| 14     | PENALTIES       | 1.141     | ANTICIPATED        | 0.978      |
| 15     | DIFFICULT       | 1.129     | VOLATILITY         | 0.961      |
| 16     | CRITICAL        | 1.032     | PREDICT            | 0.953      |
| 17     | NEGATIVE        | 0.991     | DEPEND             | 0.946      |
| 18     | DAMAGES         | 0.947     | UNCERTAINTY        | 0.900      |
| 19     | DELAYS          | 0.936     | DIFFER             | 0.847      |
| 20     | DECLINE         | 0.916     | CONTINGENT         | 0.795      |
| 21     | LIMITATIONS     | 0.846     | ANTICIPATE         | 0.788      |
| 22     | RESTATED        | 0.844     | EXPOSURE           | 0.777      |
| 23     | DELAY           | 0.831     | VARIABLE           | 0.697      |
| 24     | VOLATILITY      | 0.792     | DEPENDS            | 0.684      |
| 25     | CHALLENGES      | 0.752     | PENDING            | 0.666      |
| 26     | HARMED          | 0.723     | DEPENDENT          | 0.584      |
| 27     | FINES           | 0.717     | CONTINGENCIES      | 0.574      |
| 28     | DISRUPTIONS     | 0.704     | ASSUMED            | 0.523      |
| 29     | CLOSING         | 0.689     | PROBABLE           | 0.515      |
| 30     | INVESTIGATIONS  | 0.663     | VARY               | 0.492      |

The ten most frequent words account for 28.0% of negative tokens and 74.3% of uncertainty tokens. The dictionaries contain 2,355 and 297 words; 40 words overlap, so the two scores are not mechanically independent.

## Measures and filing-event design

For a category, the proportional score is its token count divided by all tokens. The weighted score sums w_ij = [(1 + ln tf_ij)/(1 + ln a_j)] ln(N/df_i) over observed category words, where a_j is total tokens divided by distinct tokens within document j. N and document frequency df_i refer to the exact estimation corpus. Natural logs give 0.8480, 0.2885 and 0.5026 for documents “LOSS LOSS RISK GAIN”, “LOSS GAIN GAIN” and “RISK RISK RISK GAIN”, using category {LOSS, RISK}. This implements Loughran and McDonald (2011), equation (1).

Primary-document text retains visible XBRL facts and excludes hidden scaffolding, separate exhibits and tables with more than 15% digits among non-space characters. Uppercase alphabetic tokens have at least two characters and retain apostrophes and hyphens. Incorporated-by-reference text is not recovered.

Day 0 follows the NYSE calendar and the later of filing date or Eastern acceptance date, advanced one day for acceptance at or after 16:00. SPY-adjusted buy-and-hold returns run from day -1 close to +3 close. Volatility is daily-return sample SD times sqrt(252), using 55 returns over [-60,-6] and 60 over [+4,+63].

Size uses day -1 nominal price and accession-matched cover shares; separately tagged same-date classes are summed, using one class price as a proxy for all classes. Future or weighted-average shares are excluded. Subsequent splits are reversed for nominal prices and volumes; adjusted closes measure returns. Liquidity and prior excess return use [-60,-6]. Regression controls are listed with the tables.

Full-sample sentiment/uncertainty correlations are 0.834 for proportions and 0.919 for weighted scores. TSLA's 10-Q filed 2023-10-23 has 2.77% negative words and 1.05% uncertainty words (percentile ranks 72 and 5). This is a relative contrast; it is not an upper-quartile negative-tone case. The high correlations indicate substantial common variation, so the two measures do not provide independent evidence.

Selected filing language: On October 27, 2021, the Court approved the parties’ joint stipulation that, among other things, (a) all claims against Kimbal Musk and Steve Jurvetson …

This passage concerns litigation. Dictionary counts register the legal vocabulary but do not determine whether a ruling was favorable.

MAY and COULD account for more than half of uncertainty tokens. These modal terms often qualify routine risk and contingency language. This concentration and their widespread occurrence support a large template component, although counts alone cannot establish copied text or changes in management beliefs. Earlier same-form filings would be needed for that distinction.

MAY appears in 100.0% of filings and APPROXIMATELY in 99.5%. Their prevalence limits their ability to distinguish documents; inverse document frequency reduces their contribution accordingly.

## Figure 1. Quarterly tone and VIX

![Quarterly tone and VIX](outputs/figure1.png)

## Table 4. Annual tone trends

Aggregate models include seasonal indicators and show both ordinary and Newey–West t-statistics (four lags). Within-company models include company effects, seasonal indicators and, in the pooled sample, report type. They exclude saturated calendar-quarter effects, which would absorb time. The main within-company inference clusters by company and calendar quarter, with min(company clusters, quarter clusters) minus one degrees of freedom.

| Sample   | Measure     | Agg. slope   | OLS t   | NW t   | Within slope   | Within t   | p        |
|:---------|:------------|:-------------|:--------|:-------|:---------------|:-----------|:---------|
| All      | Neg. %      | 0.011        | 1.030   | 0.826  | 0.004          | 0.336      | 0.741    |
| All      | Unc. %      | -0.008       | -1.275  | -1.306 | -0.015         | -1.996     | 0.060    |
| All      | Neg. tf.idf | 0.738        | 0.797   | 0.646  | -0.187         | -0.223     | 0.826    |
| All      | Unc. tf.idf | -0.222       | -1.540  | -1.171 | -0.422         | -3.705     | 0.002    |
| 10-K     | Neg. %      | 0.054        | 10.306  | 11.967 | 0.056          | 8.191      | 1.18e-07 |
| 10-K     | Unc. %      | 0.015        | 2.389   | 2.307  | 0.022          | 5.570      | 2.26e-05 |
| 10-K     | Neg. tf.idf | 2.166        | 2.907   | 5.405  | 2.426          | 4.876      | 1.05e-04 |
| 10-K     | Unc. tf.idf | -0.274       | -1.533  | -2.399 | -0.165         | -1.307     | 0.207    |
| 10-Q     | Neg. %      | -0.018       | -1.460  | -1.502 | -0.011         | -0.725     | 0.478    |
| 10-Q     | Unc. %      | -0.039       | -3.448  | -3.878 | -0.026         | -2.524     | 0.021    |
| 10-Q     | Neg. tf.idf | -2.074       | -2.550  | -2.710 | -1.929         | -1.585     | 0.129    |
| 10-Q     | Unc. tf.idf | -0.608       | -4.269  | -4.661 | -0.582         | -3.720     | 0.001    |

Proportional slopes are percentage points per year; tf.idf slopes are weighted-score units per year. The aggregate series has at most 20 quarters. A low HAC p-value alone is insufficient evidence of a persistent economic trend.

All denotes pooled 10-K and 10-Q reports. Within-company cluster counts: All: 84 companies / 20 quarters; 10-K: 83 companies / 20 quarters; 10-Q: 83 companies / 20 quarters.

The form-specific within-company results differ: annual-report negative tone rises 0.056 percentage points per year (t = 8.19) and annual uncertainty rises 0.022 (t = 5.57), while quarterly uncertainty falls 0.026 (t = -2.52). A single pooled trend would conceal this difference.

Negative tone changes by +0.004 percentage points per year within companies (two-way clustered t = 0.34, p = 0.741); this estimate is not statistically distinguishable from zero at 5%. Company effects and reporting-season controls make this more informative than the aggregate slope.

Uncertainty changes by -0.015 percentage points per year within companies (two-way clustered t = -2.00, p = 0.060); this estimate is not statistically distinguishable from zero at 5%. Company effects and reporting-season controls make this more informative than the aggregate slope.

Weighted negative tone changes by -0.187 score units per year (t = -0.22, p = 0.826). Weighted and proportional results are different measurements and should not be treated as independent replications.

Weighted uncertainty changes by -0.422 score units per year (t = -3.70, p = 0.002). Weighted and proportional results are different measurements and should not be treated as independent replications.

The chart separates form types and removes company mean levels. In this unbalanced panel, company means reflect different entry and exit periods; the chart therefore does not fully remove selection over time. The within-company regression, rather than visual slope alone, determines the trend interpretation.

## Table 5. Uncertainty and subsequent volatility

Dependent variable: annualised post-filing volatility. Coefficients use uncertainty fractions or tf.idf units. All models include company and quarter effects, size, liquidity, prior excess return and report type where applicable. Both specifications use identical observations. t and p use two-way company/quarter clustering.

| Sample   | Measure   | Pre-vol   | Coefficient   | t      | p     | N     |
|:---------|:----------|:----------|:--------------|:-------|:------|:------|
| All      | prop      | No        | -0.169        | -0.117 | 0.908 | 1,437 |
| All      | prop      | Yes       | -0.721        | -0.567 | 0.578 | 1,437 |
| All      | tfidf     | No        | 1.69e-04      | 0.206  | 0.839 | 1,437 |
| All      | tfidf     | Yes       | -1.49e-04     | -0.199 | 0.844 | 1,437 |
| 10-K     | prop      | No        | -16.264       | -0.759 | 0.457 | 349   |
| 10-K     | prop      | Yes       | -24.921       | -1.033 | 0.315 | 349   |
| 10-K     | tfidf     | No        | 0.004         | 0.555  | 0.586 | 349   |
| 10-K     | tfidf     | Yes       | 0.005         | 0.905  | 0.377 | 349   |
| 10-Q     | prop      | No        | 3.207         | 1.338  | 0.197 | 1,088 |
| 10-Q     | prop      | Yes       | 2.221         | 0.975  | 0.342 | 1,088 |
| 10-Q     | tfidf     | No        | 0.003         | 2.171  | 0.043 | 1,088 |
| 10-Q     | tfidf     | Yes       | 0.002         | 1.602  | 0.126 | 1,088 |

Proportional uncertainty: the coefficient changes from -0.169 (t = -0.12) to -0.721 (t = -0.57) after controlling for pre-filing volatility, a difference of -0.552. The controlled association is not statistically distinguishable from zero at 5%. A one-standard-deviation increase corresponds to -0.38 percentage points of annualised volatility. The controlled model asks whether tone adds information beyond existing volatility; the unadjusted model can reflect persistence in company risk.

Weighted uncertainty: the coefficient changes from 1.69e-04 (t = 0.21) to -1.49e-04 (t = -0.20) after controlling for pre-filing volatility, a difference of -3.18e-04. The controlled association is not statistically distinguishable from zero at 5%. A one-standard-deviation increase corresponds to -0.14 percentage points of annualised volatility. The controlled model asks whether tone adds information beyond existing volatility; the unadjusted model can reflect persistence in company risk.

## Table 6. Negative sentiment and filing-period excess return

The four-session event can coincide with earnings news. Approximate 80% minimum detectable effects (MDE) are computed as (two-sided 5% t critical value + 0.842) times the coefficient standard error, then scaled by tone SD. Effect and MDE columns are percentage points of return per one tone SD; these describe precision, not observed power.

| Sample   | Measure   | Coef.     | t      | p     | Effect pp   | MDE pp   | N     |
|:---------|:----------|:----------|:-------|:------|:------------|:---------|:------|
| All      | prop      | -1.022    | -1.366 | 0.188 | -0.866      | 1.860    | 1,437 |
| All      | tfidf     | -1.46e-04 | -1.267 | 0.220 | -1.070      | 2.479    | 1,437 |
| 10-K     | prop      | -6.782    | -0.799 | 0.434 | -2.718      | 9.983    | 349   |
| 10-K     | tfidf     | -7.90e-04 | -1.045 | 0.309 | -3.025      | 8.495    | 349   |
| 10-Q     | prop      | -2.920    | -2.299 | 0.033 | -2.751      | 3.512    | 1,088 |
| 10-Q     | tfidf     | -3.54e-04 | -2.114 | 0.048 | -2.715      | 3.770    | 1,088 |

The proportional sentiment return coefficient is -1.022 (t = -1.37, p = 0.188). Its approximate detectable effect is 1.86 return percentage points per tone SD. A null at this precision does not establish zero price response. Event overlap and the short window make this test less decisive than a within-company language trend or a volatility association.

The 10-Q-only return estimates have t = -2.30 (proportional, p = 0.033) and t = -2.11 (weighted, p = 0.048). These subgroup results must be distinguished from the pooled null. They are tentative because the specifications are correlated, multiple tests are reported without multiplicity adjustment, and nearby earnings releases can drive the same return window.

## Report-type differences

Negative proportional-tone SD is 0.401 percentage points for 10-Ks and 0.942 for 10-Qs. Shorter reports can increase sampling noise in a ratio, while repeated templates can suppress variation; the observed variance reflects both mechanisms and report content.

Uncertainty proportional-tone SD is 0.243 percentage points for 10-Ks and 0.581 for 10-Qs. Shorter reports can increase sampling noise in a ratio, while repeated templates can suppress variation; the observed variance reflects both mechanisms and report content.

For 10-Ks, the uncertainty trend is +0.022 percentage points per year (t = 5.57); the volatility coefficient with pre-volatility is -24.921 (t = -1.03). These are separate within-form estimates; differing significance alone is not a formal test of coefficient equality.

For 10-Qs, the uncertainty trend is -0.026 percentage points per year (t = -2.52); the volatility coefficient with pre-volatility is 2.221 (t = 0.97). These are separate within-form estimates; differing significance alone is not a formal test of coefficient equality.

For quarterly weighted uncertainty, adding pre-volatility reduces the volatility coefficient from 0.002615 (p = 0.043) to 0.001893 (p = 0.126). The apparent association is no longer significant once existing volatility is controlled. This supports interpreting the uncontrolled association cautiously.

10-Ks contain fuller annual business and risk disclosures, but more words need not imply more new information. 10-Qs can contain timely updates, yet their proximity to earnings announcements prevents a clean attribution of the filing-window return to textual tone alone. Novel changes relative to the previous same-form filing would better distinguish signal from templates.

## Interpretation and limitations

The annual negative-tone increase and quarterly uncertainty decline receive the most weight: both persist within companies under proportional and weighted measurement. The annual uncertainty increase is less robust because its weighted trend is insignificant. The controlled volatility models provide no convincing positive incremental association. The quarterly return association remains tentative given event contamination and multiple tests. These are conditional associations, not causal effects or a live trading strategy.

For pooled proportional uncertainty, the controlled 95% interval is [-1.77, 1.01] percentage points of annualised volatility per tone SD. This bounds the incremental association under the specification. The null should not be dismissed with a blanket claim that every test lacks power.

0 of 12 within-company trend tests change 5% significance when moving from company-only to two-way clustering. The main tables use the latter to allow shared quarterly shocks. Only 20 time clusters remain, so even corrected inference is approximate. All estimated specifications are retained in the notebook: four tone trends, two uncertainty-volatility measures with both controls specifications, and two sentiment-return measures, pooled and by form, with both clustering choices. There is no winsorisation or selective removal of inconvenient estimates.

Of 175 distinct securities in the May 6, 2021 holdings, 106 (60.6%) do not match the frozen 2026 holdings by either normalized ticker or valid CUSIP. The universe is selected using 2026 holdings, so every company in the study survived this selection rule. Identity changes, mergers and share classes mean these security absences cannot all be interpreted as failed companies.

Selection can exclude firms with deteriorating outcomes and distort measured trends. The mixed holdings dates, incomplete historical identifiers, strict share-count coverage, common-case filters and benchmark choice further limit generalisation. Full-corpus tf.idf uses later filings to estimate word weights; it is a descriptive retrospective measure, not a live forecasting protocol.

## Next step

Reconstruct a point-in-time holdings universe and score only language newly introduced since the previous comparable filing. Combine that design with earnings timestamps and forward-only dictionary weights. This requires historical identifier mapping and additional text alignment, but directly addresses selection, template repetition and event contamination.

## Sources

Loughran, T. and B. McDonald (2011), “When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks,” Journal of Finance 66(1), 35–65. https://doi.org/10.1111/j.1540-6261.2010.01625.x. SEC EDGAR filings and company facts: https://www.sec.gov/edgar. Market series: Yahoo Finance via yfinance. Loughran–McDonald Master Dictionary: https://sraf.nd.edu/loughranmcdonald-master-dictionary/. Holdings: https://github.com/robynge/ark-routine and the course starter repository.

Illustrative filing: https://www.sec.gov/Archives/edgar/data/1318605/000162828023034847/tsla-20230930.htm

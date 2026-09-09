"""Create a standalone report from a chosen set of computed exhibits."""
from pathlib import Path
import argparse
import json
import os
import sys
from html import escape

import pandas as pd
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.report_math import format_number, formula_image

REPO = 'https://github.com/robynge/FRE-GY-7871A-Assignment1'
BLUE = colors.HexColor('#174A72')
FORMS = ['All', '10-K', '10-Q']
TONES = ['Negative_prop', 'Uncertainty_prop', 'Negative_tfidf', 'Uncertainty_tfidf']


def p_value(value):
    if not np.isfinite(value):
        return 'not estimable'
    return '< 0.001' if value < .001 else f'= {value:.3f}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs')
    parser.add_argument('--report-path', type=Path, default=ROOT / 'REPORT.md')
    args = parser.parse_args()
    out, report_path = args.output_dir.resolve(), args.report_path.resolve()
    audit = json.loads((out / 'audit.json').read_text())
    tables = {i: pd.read_csv(out / f'table{i}.csv') for i in range(1, 7)}
    universe = pd.read_csv(out / 'table1_universe.csv')
    start, end = audit['sample_start'], audit['sample_end']
    last_market = audit['market_last_date']
    period = f'{start} to {end}'
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodySmall', fontName='Helvetica', fontSize=9, leading=12, spaceAfter=7))
    styles.add(ParagraphStyle(name='NoteSmall', fontName='Helvetica', fontSize=8, leading=10.3, spaceAfter=6, textColor=colors.HexColor('#444444')))
    styles.add(ParagraphStyle(name='TableSmall', fontName='Helvetica', fontSize=7.5, leading=9.3))
    styles['Title'].fontSize = 19
    styles['Title'].leading = 23
    styles['Title'].textColor = BLUE
    styles['Heading2'].fontSize = 11
    styles['Heading2'].leading = 14
    styles['Heading2'].textColor = BLUE
    styles['Heading2'].keepWithNext = True
    story, md = [], []

    def p(text, note=False):
        story.append(Paragraph(escape(text), styles['NoteSmall' if note else 'BodySmall']))
        md.append(text.replace('$', r'\$') + '\n')

    def link(label, url):
        story.append(Paragraph(f'<link href="{escape(url, quote=True)}" color="#174A72">{escape(label)}</link>', styles['NoteSmall']))
        md.append(f'[{label}]({url})\n')

    def h(text):
        story.append(Paragraph(escape(text), styles['Heading2']))
        md.append('## ' + text + '\n')

    def equation(*lines):
        for line in lines:
            story.extend([formula_image(line), Spacer(1, 7)])
        md.append('$$\n' + (lines[0] if len(lines) == 1 else '\\begin{aligned}\n' + '\\\\\n'.join(lines) + '\n\\end{aligned}') + '\n$$\n')

    def table(df, widths=None):
        rows = [[Paragraph(escape(str(c)), styles['TableSmall']) for c in df.columns]]
        rows += [[Paragraph(format_number(v, target='pdf'), styles['TableSmall']) for v in row]
                 for row in df.itertuples(index=False, name=None)]
        t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E7EEF3')),
            ('LINEBELOW', (0, 0), (-1, 0), .6, BLUE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6F8FA')])]))
        story.extend([KeepTogether([t]) if len(rows) <= 15 else t, Spacer(1, 7)])
        md.append(df.map(lambda x: format_number(x, target='markdown')).to_markdown(index=False, disable_numparse=True) + '\n')

    def page():
        story.append(Spacer(1, 5))

    def row(number, form='All', measure=None, model=None, inference='firm_quarter_cluster'):
        data = tables[number]
        mask = data['sample'].eq(form) & data.inference.eq(inference)
        if measure:
            mask &= data.measure.eq(measure)
        if model:
            mask &= data.model.eq(model)
        selected = data.loc[mask]
        if len(selected) != 1:
            raise ValueError(f'Expected one result: table {number}, {form}, {measure}, {model}, {inference}')
        return selected.iloc[0]

    def strength(r):
        if not np.isfinite(r.p):
            return 'cannot be evaluated with the stated inference'
        return 'is significant at 5%' if r.p < .05 else 'is not significant at 5%'

    def cluster_note(number, model, tone):
        values = []
        for form in FORMS:
            r = row(number, form, tone, model)
            values.append(f'{form}: {int(r.firm_clusters)} companies, {int(r.quarter_clusters)} quarters, {int(r.df_inference)} inference degrees of freedom')
        return '; '.join(values) + '.'

    story.append(Paragraph('Uncertainty and sentiment in financial reports', styles['Title']))
    p('FRE-GY 7871 A · NLP and the Investment Process · Filing dates ' + period)
    link('Research repository', REPO)
    p(f"{audit['final_filings']:,} filings from {audit['final_companies']} companies enter the text analysis. "
      f"The volatility analysis uses {audit['volatility_filings']:,} filings and the return analysis uses {audit['return_filings']:,}. "
      'Negative words measure adverse language; uncertainty words measure imprecision and hedging. '
      'All results describe associations in companies selected from ARK holdings.')
    an = row(4, '10-K', 'Negative_prop', 'within_firm_trend')
    qu = row(4, '10-Q', 'Uncertainty_prop', 'within_firm_trend')
    controlled = tables[5].query("inference == 'firm_quarter_cluster' and model == 'volatility_with_prevol'")
    significant = int(controlled.p.lt(.05).sum())
    rr = row(6, 'All', 'Negative_prop', 'filing_return')
    p(f'Within companies, annual-report negative-word shares change by {100*an.coef:+.3f} percentage points per year '
      f'(p {p_value(an.p)}); quarterly-report uncertainty changes by {100*qu.coef:+.3f} points (p {p_value(qu.p)}). '
      f'After controlling for prior volatility, {significant} of {len(controlled)} uncertainty specifications are significant at 5%. '
      f'The pooled negative-tone return estimate {strength(rr)} (p {p_value(rr.p)}).')
    p(f'Filing coverage ends on {end}; market observations end on {last_market}. '
      'Recent filings remain in text analysis even when their future price windows are unavailable. '
      'Return and volatility samples are filtered separately; both volatility specifications use the same observations. '
      f"The latest included filings are {audit['return_last_filing_date']} for returns and {audit['volatility_last_filing_date']} for volatility.", note=True)
    if audit.get('period_incomplete'):
        p(f'The final calendar quarter is incomplete as of {end}. Its filing counts, tone averages and VIX average are partial-quarter observations; '
          'they should not be compared with completed quarters as if coverage were equal.', note=True)

    h('Table 1. Sample construction')
    p('Panel A counts holding identifiers, then companies. The frozen six-fund holdings use January 2, 2026 for ARKF and ARKX '
      'and September 4, 2026 for the other four funds. Different share classes are combined by SEC company identifier. '
      'The holdings dates define a retrospective company universe.', note=True)
    u = universe.copy()
    u['filter'] = u['filter'].replace({'foreign_reporting_forms': '20-F / 40-F reporting companies',
                                      'first_10x_after_sample': f'First 10-K/Q after {end}'})
    table(u.rename(columns={'filter': 'Company/security filter', 'removed': 'Removed', 'remaining': 'Remaining', 'unit': 'Unit'}), [286, 57, 62, 110])
    for label, data in tables[1].groupby('sample', sort=False):
        p(f'Panel B — {label} sample. Counts follow this panel’s filter order.', note=True)
        table(data.drop(columns='sample').rename(columns={'filter': 'Filing filter', 'removed': 'Removed', 'remaining': 'Remaining', 'companies': 'Companies'}), [299, 64, 76, 76])
    p(f"{audit['amendments']} amendments and {audit['parse_failures']} parse failures are recorded. "
      f"All {audit['all_scored_filings']:,} successfully parsed original filings receive tone scores before analytical sample restrictions. "
      'Market-data restrictions do not determine the text sample.', note=True)
    page()

    h('Table 2. Tone by report type')
    p('The text sample determines descriptive statistics and trends. Proportional scores are percentages; weighted scores are equation (1) sums. '
      'Document frequencies are fitted within each analytical sample and separately by report type.', note=True)
    table(tables[2][['form', 'measure', 'n', 'mean', 'sd', 'p25', 'median', 'p75']].rename(columns={
        'form': 'Form', 'measure': 'Measure', 'n': 'N', 'mean': 'Mean', 'sd': 'SD', 'p25': 'P25', 'median': 'Median', 'p75': 'P75'}),
        [38, 137, 43, 59, 59, 59, 60, 60])
    p('Negative/uncertainty correlations (proportional, weighted): ' + '; '.join(
      f"{r['form']}: {r['prop']:.3f}, {r['tfidf']:.3f}" for r in audit['correlations']) + '.', note=True)
    h('Table 3. Most frequent dictionary words')
    p('Each percentage divides a word count by all token occurrences in its dictionary category across the text sample.', note=True)
    neg = tables[3][tables[3].category.eq('Negative')].reset_index(drop=True)
    unc = tables[3][tables[3].category.eq('Uncertainty')].reset_index(drop=True)
    table(pd.DataFrame({'Rank': neg['rank'], 'Negative word': neg.word, 'Share %': neg.share_pct,
                       'Uncertainty word': unc.word, 'Share % ': unc.share_pct}), [35, 163, 65, 182, 70])
    p(f"The top ten words account for {audit['top10_shares']['Negative']:.1f}% of negative tokens and "
      f"{audit['top10_shares']['Uncertainty']:.1f}% of uncertainty tokens. "
      f"The active dictionaries contain {audit['lexicon_counts']['Negative']:,} negative and {audit['lexicon_counts']['Uncertainty']:,} uncertainty words, "
      f"with {audit['lexicon_overlap']} words in both categories.", note=True)
    page()

    h('Tone measures')
    p('The Loughran–McDonald Master Dictionary, 1993–2025 release, was updated in March 2026. '
      'A positive category value identifies an active word; a negative value records removal from that category. '
      'Only active entries enter the scores. Thus the negative category contains 2,345 words; the 10 removed entries are excluded. '
      'The proportional score divides category occurrences by all tokens in a filing.')
    equation(r'P_{cj}=\frac{\sum_{i\in c}tf_{ij}}{W_j}')
    p('Equation (1) applies logarithmic term frequency and inverse document frequency. The score sums weights over category words observed in a filing.')
    equation(r'T_{cj}=\sum_{i\in c,\,tf_{ij}>0}\frac{1+\ln(tf_{ij})}{1+\ln(a_j)}\ln\!\left(\frac{N}{df_i}\right)',
             r'a_j=\frac{W_j}{V_j}')
    p('W is total tokens, V is distinct tokens, N is documents in the relevant estimation corpus and df is document frequency. '
      'All logarithms are natural. The text, volatility and return samples each fit their own word weights; report-type analyses also refit within form. '
      'The weighted score is measured in score units rather than percentages.')
    p('An illustrative calculation uses “LOSS LOSS RISK GAIN”, “LOSS GAIN GAIN” and “RISK RISK RISK GAIN”, '
      'with category {LOSS, RISK}. Their weighted scores are 0.8480, 0.2885 and 0.5026. These constructed documents illustrate the formula.')
    p('Primary-document text retains visible XBRL facts and excludes hidden content, separate exhibits and tables with more than 15% digits '
      'among non-space characters. Alphabetic tokens contain at least two characters and retain apostrophes and hyphens. Incorporated-by-reference text is not recovered.')
    ex = audit['example']
    p(f"{ex['ticker']}'s {ex['form']} filed {ex['filing_date']} contains {ex['negative_pct']:.2f}% negative words and "
      f"{ex['uncertainty_pct']:.2f}% uncertainty words, at percentile ranks {100*ex['negative_percentile']:.0f} and "
      f"{100*ex['uncertainty_percentile']:.0f}, respectively. It has the largest negative-minus-uncertainty percentile gap in the text sample. "
      'This selected contrast is not representative of all filings.')
    p('Selected filing language: ' + ex['sentence'], note=True)
    p('Dictionary counts identify category vocabulary; they do not determine the direction or significance of the event described.', note=True)
    modal_share = float(unc.loc[unc.word.isin(['MAY', 'COULD']), 'share_pct'].sum())
    p(f'MAY and COULD account for {modal_share:.1f}% of uncertainty tokens. '
      'These counts do not distinguish recurring disclosure language from newly expressed uncertainty. '
      'High negative/uncertainty correlations also mean the two measures do not provide independent evidence.')
    p(f"MAY occurs in {audit['uncertainty_word_document_pct']['MAY']:.1f}% of filings and APPROXIMATELY in "
      f"{audit['uncertainty_word_document_pct']['APPROXIMATELY']:.1f}%. Inverse document frequency gives less weight to words appearing in most documents.", note=True)

    h('Figure 1. Quarterly tone and VIX')
    image = Image(str(out / 'figure1.png'))
    image.drawHeight = 515 * image.imageHeight / image.imageWidth
    image.drawWidth = 515
    story.append(KeepTogether([story.pop(), image]))
    md.append('![Quarterly tone and VIX](' + Path(os.path.relpath(out / 'figure1.png', report_path.parent)).as_posix() + ')\n')
    counts = pd.DataFrame(audit['quarter_counts'])
    count_notes = []
    for form in ['10-K', '10-Q']:
        data = counts[counts.form.eq(form)]
        count_notes.append(f"{form}: {int(data.n.min())}–{int(data.n.max())} filings per observed quarter")
    p('; '.join(count_notes) + '. Sparse annual-report quarters may reflect only a few companies. '
      'Company-centered means reduce baseline composition differences, but entry and exit periods can still affect this unbalanced panel. '
      'The gray dashed series is quarterly average VIX on the right axes; the latest quarter is partial when indicated. '
      'Formal trend inference uses Table 4.', note=True)
    page()

    h('Table 4. Annual tone trends')
    p('Quarter-level means estimate the aggregate trend. Filing-level models estimate change within companies:')
    equation(r'\bar T_q=\alpha+\beta\tau_q+\sum_{s=2}^{4}\delta_sD_{sq}+\varepsilon_q',
             r'T_{iq}=\alpha_i+\beta\tau_q+\sum_{s=2}^{4}\delta_sD_{sq}+\theta K_{iq}+\varepsilon_{iq}')
    p('Time is elapsed years from the first sample quarter. Seasonal indicators control the reporting quarter of the year. '
      'Company effects control company mean levels; K indicates a 10-K in the pooled sample and is omitted within each report type. '
      'Saturated calendar-quarter effects are excluded because they would absorb the trend. '
      'Aggregate inference shows ordinary OLS and Newey–West t-statistics with four lags. Within-company t and p use two-way company/calendar-quarter clustering.', note=True)
    trendrows = []
    for form in FORMS:
        for tone in TONES:
            within = row(4, form, tone, 'within_firm_trend')
            ols = row(4, form, tone, 'aggregate_trend', 'OLS')
            hac = row(4, form, tone, 'aggregate_trend', 'HAC4')
            mult = 100 if tone.endswith('prop') else 1
            trendrows.append({'Sample': form, 'Measure': tone.replace('Negative', 'Neg.').replace('Uncertainty', 'Unc.').replace('_prop', ' %').replace('_tfidf', ' tf.idf'),
                              'Agg. slope': ols.coef*mult, 'OLS t': ols.t, 'NW t': hac.t, 'Within slope': within.coef*mult, 'Within t': within.t, 'p': within.p})
    table(pd.DataFrame(trendrows), [39, 86, 70, 52, 52, 83, 68, 65])
    p('Proportional slopes are percentage points per year; weighted slopes are score units per year. ' + cluster_note(4, 'within_firm_trend', 'Negative_prop'), note=True)
    for form in ['10-K', '10-Q']:
        n = row(4, form, 'Negative_prop', 'within_firm_trend')
        u = row(4, form, 'Uncertainty_prop', 'within_firm_trend')
        nw = row(4, form, 'Negative_tfidf', 'within_firm_trend')
        uw = row(4, form, 'Uncertainty_tfidf', 'within_firm_trend')
        p(f'{form} negative-word shares change by {100*n.coef:+.3f} percentage points per year (p {p_value(n.p)}); '
          f'uncertainty-word shares change by {100*u.coef:+.3f} points (p {p_value(u.p)}). '
          f'The corresponding weighted slopes are {nw.coef:+.3f} (p {p_value(nw.p)}) and {uw.coef:+.3f} (p {p_value(uw.p)}).')
    p('Within-company estimates receive more weight than aggregate slopes because they account for company levels and reporting season. '
      'Proportional and weighted measures capture related language and are not independent replications. '
      'Sparse annual-report quarters limit interpretation of individual points in the chart.'
      + (' The final quarter also has incomplete filing coverage.' if audit.get('period_incomplete') else ''))
    page()

    h('Filing-event design')
    p('Day 0 is the first NYSE session on or after the later of the filing date and the Eastern acceptance date. '
      'Acceptance at or after the exchange’s actual close, including an early close, moves the event to the next session. '
      'Market data include only completed sessions through ' + last_market + '.')
    equation(r'R^{[0,3],\mathrm{excess}}=\frac{P^{\mathrm{adj}}_{+3}}{P^{\mathrm{adj}}_{-1}}-\frac{SPY^{\mathrm{adj}}_{+3}}{SPY^{\mathrm{adj}}_{-1}}',
             r'\sigma^{\mathrm{pre}}=\sqrt{252}\,\mathrm{SD}(r_{-60},\ldots,r_{-6})',
             r'\sigma^{\mathrm{post}}=\sqrt{252}\,\mathrm{SD}(r_{+4},\ldots,r_{+63})')
    p('The event spans four daily return intervals. Pre-filing volatility uses 55 daily returns and post-filing volatility uses 60, '
      'with sample standard deviations. Adjusted closes measure returns; nominal closes determine the $3 price filter and company size. '
      'Later splits are reversed for nominal price and volume histories. Future returns are not imputed.')
    p('Size is the day −1 nominal price times outstanding shares from the scored filing’s cover page. '
      'Same-date share classes are summed using one class price as a proxy; future or weighted-average shares are excluded. '
      'Liquidity is mean nominal dollar volume over days [−60,−6], and prior excess return is SPY-adjusted buy-and-hold return over that interval.')
    p('The outcome models use firm effects, calendar-quarter effects and the following controls:')
    equation(r'C_{iq}=\gamma_1\ln(\mathrm{Size}_{iq})+\gamma_2\ln(\mathrm{DollarVolume}_{iq})',
             r'\qquad+\gamma_3R^{\mathrm{pre,excess}}_{iq}+\theta K_{iq}',
             r'\sigma^{\mathrm{post}}_{iq}=\alpha_i+\lambda_q+\beta U_{iq}+C_{iq}+[\rho\sigma^{\mathrm{pre}}_{iq}]+\varepsilon_{iq}',
             r'R^{[0,3],\mathrm{excess}}_{iq}=\alpha_i+\lambda_q+\beta N_{iq}+C_{iq}+\rho\sigma^{\mathrm{pre}}_{iq}+\varepsilon_{iq}')
    p('U is uncertainty and N is negative tone, each estimated separately as a proportion and a weighted score. '
      'The bracketed pre-volatility term is included or omitted in the paired volatility tests; it is always included in the return tests. '
      'The 10-K indicator K applies only to the pooled sample. No winsorisation is applied.', note=True)

    h('Table 5. Uncertainty and subsequent volatility')
    p('Dependent variable: annualised volatility as a fraction. Coefficients are per unit of uncertainty fraction or weighted score. '
      'Both specifications use the same complete observations within each sample. Two-way company/quarter clustering determines t and p. '
      + cluster_note(5, 'volatility_with_prevol', 'Uncertainty_prop'), note=True)
    vol = tables[5][tables[5].inference.eq('firm_quarter_cluster')].copy()
    vol['Measure'] = vol.measure.str.replace('Uncertainty_', '', regex=False)
    vol['Pre-vol'] = vol.model.eq('volatility_with_prevol').map({True: 'Yes', False: 'No'})
    table(vol[['sample', 'Measure', 'Pre-vol', 'coef', 't', 'p', 'n']].rename(columns={'sample': 'Sample', 'coef': 'Coefficient', 'n': 'N'}), [49, 64, 54, 116, 70, 80, 82])
    for tone, label in [('Uncertainty_prop', 'Proportional'), ('Uncertainty_tfidf', 'Weighted')]:
        a = row(5, 'All', tone, 'volatility_without_prevol')
        b = row(5, 'All', tone, 'volatility_with_prevol')
        p(f'{label} uncertainty: a one-standard-deviation increase corresponds to {100*b.effect_1sd:+.2f} percentage points '
          f'of annualised volatility after controlling for prior volatility (95% interval '
          f'[{100*b.ci_low*b.tone_sd:+.2f}, {100*b.ci_high*b.tone_sd:+.2f}]). '
          f'The uncontrolled effect is {100*a.effect_1sd:+.2f} points (p {p_value(a.p)}), compared with p {p_value(b.p)} after control. '
          f'Adding the control changes the estimated effect by {100*(b.effect_1sd-a.effect_1sd):+.2f} points. '
          'This comparison tests incremental association beyond existing volatility.')
    q0 = row(5, '10-Q', 'Uncertainty_tfidf', 'volatility_without_prevol')
    q1 = row(5, '10-Q', 'Uncertainty_tfidf', 'volatility_with_prevol')
    qp = row(5, '10-Q', 'Uncertainty_prop', 'volatility_with_prevol')
    p(f'For 10-Q weighted uncertainty, the effect per tone standard deviation changes from {100*q0.effect_1sd:+.2f} '
      f'to {100*q1.effect_1sd:+.2f} volatility percentage points after adding prior volatility '
      f'(p {p_value(q0.p)} and {p_value(q1.p)}). The controlled proportional-score estimate has p {p_value(qp.p)}. '
      'Differences across weighting schemes and multiple unadjusted tests limit the strength of an isolated significant association.')
    page()

    h('Table 6. Negative sentiment and filing-period excess return')
    p('Dependent variable: SPY-adjusted four-session buy-and-hold return as a fraction. All models include log size, log dollar volume, '
      'prior excess return, pre-filing volatility, company effects and calendar-quarter effects; pooled models also include the 10-K indicator. '
      'Coefficients are per unit of negative-word fraction or weighted score. t and p use two-way company/quarter clustering. '
      + cluster_note(6, 'filing_return', 'Negative_prop'), note=True)
    ret = tables[6][tables[6].inference.eq('firm_quarter_cluster')].copy()
    ret['Measure'] = ret.measure.str.replace('Negative_', '', regex=False)
    ret['Effect pp'] = 100*ret.effect_1sd
    ret['MDE pp'] = 100*ret.mde80_1sd
    table(ret[['sample', 'Measure', 'coef', 't', 'p', 'Effect pp', 'MDE pp', 'n']].rename(columns={'sample': 'Sample', 'coef': 'Coef.', 'n': 'N'}), [43, 55, 83, 52, 69, 74, 74, 65])
    equation(r'\mathrm{MDE}^{\mathrm{pp}}_{80,1\mathrm{SD}}=100\left(t_{0.975,\nu}+\Phi^{-1}(0.8)\right)\mathrm{SE}(\hat\beta)\,s_{\mathrm{tone}}')
    p('Effect and minimum detectable effect (MDE) are return percentage points per one tone standard deviation. '
      'MDE approximates 80% power for a two-sided 5% test using the stated inference degrees of freedom. '
      'It measures precision rather than observed power.', note=True)
    for form in FORMS:
        r = row(6, form, 'Negative_prop', 'filing_return')
        w = row(6, form, 'Negative_tfidf', 'filing_return')
        p(f'{form}: a one-standard-deviation increase in proportional negative tone corresponds to {100*r.effect_1sd:+.2f} '
          f'return percentage points (p {p_value(r.p)}), with an approximate detectable effect of {100*r.mde80_1sd:.2f} points. '
          f'The weighted-score effect is {100*w.effect_1sd:+.2f} points (p {p_value(w.p)}).')
    p('Statistical insignificance does not establish zero price response. Earnings releases can overlap the filing window and drive the same returns. '
      'Correlated specifications and multiple unadjusted tests also limit the interpretation of isolated significant estimates.')

    h('Report-type differences and limitations')
    supported = []
    for form in ['10-K','10-Q']:
        for category,label in [('Negative','negative tone'),('Uncertainty','uncertainty')]:
            a = row(4,form,category+'_prop','within_firm_trend')
            b = row(4,form,category+'_tfidf','within_firm_trend')
            if a.p < .05 and b.p < .05 and np.sign(a.coef)==np.sign(b.coef):
                supported.append(form+' '+label+(' increase' if a.coef>0 else ' decrease'))
    p('The within-company trends supported by both weighting schemes at the 5% level are: '
      + (', '.join(supported) if supported else 'none') + '. '
      'These receive more weight than results that depend on the weighting scheme, although the two measures are correlated. '
      'Volatility associations assess incremental information after existing risk is controlled; short-window returns have separate precision and earnings-overlap limitations.')

    for label, tone in [('Negative', 'Negative words (%)'), ('Uncertainty', 'Uncertainty words (%)')]:
        vals = tables[2][tables[2].measure.eq(tone)].set_index('form')
        p(f"{label} proportional-score SD is {vals.loc['10-K', 'sd']:.3f} percentage points for 10-Ks and "
          f"{vals.loc['10-Q', 'sd']:.3f} for 10-Qs. Report length, repeated language and changing content may affect dispersion; "
          'this analysis does not identify their separate contributions.')
    p('10-Ks provide annual business and risk disclosures, while 10-Qs provide quarterly updates. '
      'More words do not necessarily imply more new information. Different significance levels across forms do not establish that coefficients differ.')
    one = tables[4][tables[4].inference.eq('firm_cluster')]
    two = tables[4][tables[4].inference.eq('firm_quarter_cluster')]
    compare = one.merge(two, on=['sample', 'measure', 'model'], suffixes=('_firm', '_two'))
    eligible = compare.p_firm.notna() & compare.p_two.notna()
    changed = int(((compare.loc[eligible, 'p_firm'] < .05) != (compare.loc[eligible, 'p_two'] < .05)).sum())
    n_quarters = sorted(two.quarter_clusters.astype(int).unique())
    p(f'{changed} of {int(eligible.sum())} estimable within-company trend tests change 5% significance between company-only and two-way clustering. '
      f"The two-way estimates use {', '.join(map(str, n_quarters))} time clusters across samples, so finite-sample inference remains approximate. "
      'All four tone trends, both volatility specifications and both return measures are reported for pooled and separate report-type samples.')
    survivor_path = out / 'survivorship.json'
    if not survivor_path.exists():
        survivor_path = ROOT / 'outputs' / 'survivorship.json'
    if survivor_path.exists():
        s = json.loads(survivor_path.read_text())
        p(f"Of {s['early_unique_security_keys']} distinct securities held on May 6, 2021, {s['absent_security_keys']} "
          f"({100*s['absent_security_keys']/s['early_unique_security_keys']:.1f}%) do not match the frozen 2026 holdings by normalized ticker or valid CUSIP. "
          'Identity changes, mergers and share classes mean these absences do not all represent company failures.')
    p('The 2026 holdings selection, mixed holdings dates and incomplete historical identifiers limit generalisation. '
      'Market-window and share-count availability impose additional selection on the outcome samples. '
      'Full-corpus word weights use later filings and the current dictionary is applied retrospectively. '
      'The estimates therefore describe retrospective conditional associations, not causal effects or an implementable live strategy.')
    h('Sources')
    link('Loughran and McDonald (2011), Journal of Finance 66(1), 35–65: When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks', 'https://doi.org/10.1111/j.1540-6261.2010.01625.x')
    link('Loughran–McDonald Master Dictionary, 1993–2025 release; updated March 2026; accessed September 9, 2026', 'https://sraf.nd.edu/loughranmcdonald-master-dictionary/')
    link('SEC EDGAR: filings and company facts', 'https://www.sec.gov/edgar')
    link('Yahoo Finance: price, volume, corporate actions and market indices', 'https://finance.yahoo.com/')
    link('ARK holdings archive', 'https://github.com/robynge/ark-routine')
    link('FRE-GY 7871 A course holdings and assignment materials', 'https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1')
    link('Illustrative SEC filing', ex['doc_url'])

    def footer(canvas, doc):
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(40, 22, 'Uncertainty and sentiment · ' + period)
        canvas.drawRightString(A4[0]-40, 22, str(doc.page))

    doc = SimpleDocTemplate(str(out / 'report.pdf'), pagesize=A4, rightMargin=40, leftMargin=40,
                            topMargin=34, bottomMargin=35, title='Uncertainty and sentiment in financial reports', author='')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('# Uncertainty and sentiment in financial reports\n\n' + '\n'.join(md))
    print(out / 'report.pdf')


if __name__ == '__main__':
    main()

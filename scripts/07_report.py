"""Create a concise, standalone report from actual computed exhibits."""
from pathlib import Path
import json
import sys
from html import escape
import pandas as pd
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
REPO='https://github.com/robynge/FRE-GY-7871A-Assignment1'
BLUE=colors.HexColor('#174A72')


def fmt(value, digits=3):
    if isinstance(value,(int,np.integer)): return f'{value:,}'
    if isinstance(value,(float,np.floating)):
        if not np.isfinite(value): return '—'
        return f'{value:.2e}' if 0 < abs(value) < .001 else f'{value:.{digits}f}'
    return str(value)


def main():
    audit=json.loads((OUT/'audit.json').read_text())
    tables={i:pd.read_csv(OUT/f'table{i}.csv') for i in range(1,7)}
    universe=pd.read_csv(OUT/'table1_universe.csv')
    sample=pd.read_csv(ROOT/'data/interim/analysis_sample.csv',dtype={'cik':str})
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodySmall',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=7))
    styles.add(ParagraphStyle(name='NoteSmall',fontName='Helvetica',fontSize=7.6,leading=9.4,spaceAfter=6,textColor=colors.HexColor('#444444')))
    styles.add(ParagraphStyle(name='TableSmall',fontName='Helvetica',fontSize=7.4,leading=9))
    styles['Title'].fontSize=19;styles['Title'].leading=23;styles['Title'].textColor=BLUE
    styles['Heading2'].fontSize=11;styles['Heading2'].leading=14;styles['Heading2'].textColor=BLUE
    story=[];md=[]
    def p(text,note=False):
        story.append(Paragraph(escape(text),styles['NoteSmall' if note else 'BodySmall']))
        md.append(text+'\n')
    def h(text):
        story.append(Paragraph(escape(text),styles['Heading2']));md.append('## '+text+'\n')
    def table(df,widths=None):
        rows=[[Paragraph(escape(str(c)),styles['TableSmall']) for c in df.columns]]
        rows += [[Paragraph(escape(fmt(v)),styles['TableSmall']) for v in row] for row in df.itertuples(index=False,name=None)]
        t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7EEF3')),
           ('LINEBELOW',(0,0),(-1,0),.6,BLUE),('VALIGN',(0,0),(-1,-1),'TOP'),
           ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
           ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
           ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F8FA')])]))
        story.extend([t,Spacer(1,7)])
        md.append(df.map(fmt).to_markdown(index=False,disable_numparse=True)+'\n')
    def page(): story.append(PageBreak())
    def row(number, sample_name='All', measure=None, model=None,inference='firm_quarter_cluster'):
        d=tables[number]; mask=d['sample'].eq(sample_name)&d.inference.eq(inference)
        if measure: mask &=d.measure.eq(measure)
        if model: mask &=d.model.eq(model)
        return d.loc[mask].iloc[0]
    def strength(r):
        if not np.isfinite(r.p): return 'not estimable with the stated inference'
        return 'statistically distinguishable from zero at 5%' if r.p<.05 else 'not statistically distinguishable from zero at 5%'

    story.append(Paragraph('Uncertainty and sentiment in financial reports',styles['Title']))
    p('FRE-GY 7871 A · NLP and the Investment Process · Filing dates 2021–2025')
    p('GitHub: '+REPO,note=True)
    p(f"{audit['final_filings']:,} filings from {audit['final_companies']} companies enter the common analysis sample. "
      'Negative-word frequency measures adverse language; uncertainty-word frequency measures imprecision and hedging. '
      'The tests examine changes within companies, subsequent realised volatility and four-session excess returns around filing.')
    h('Table 1. Sample construction')
    p('Panel A counts holding identifiers, then companies. The frozen six-fund snapshot contains 130 raw tickers, '
      'rather than the approximately 124 companies in the assignment description. ARKF and ARKX are dated January 2, 2026; '
      'the other four funds are dated September 4, 2026. The separate September 4 holdings snapshot contains 121 raw tickers. '
      'The frozen classroom sample is retained; different share classes are combined by SEC company identifier.',note=True)
    u=universe.copy()
    u['filter']=u['filter'].replace({'foreign_reporting_forms':'20-F / 40-F reporting companies',
             'first_10x_after_sample':'First 10-K/Q after 2025','first_10x_after_2025':'First 10-K/Q after 2025'})
    table(u.rename(columns={'filter':'Company/security filter','removed':'Removed','remaining':'Remaining','unit':'Unit'}),[286,57,62,110])
    p('Panel B counts filings. Company exclusions above have no observed 10-K/Q count to subtract from this panel.',note=True)
    table(tables[1].rename(columns={'filter':'Filing filter','removed':'Removed','remaining':'Remaining','companies':'Companies'}),[319,60,68,68])
    p(f"{audit['amendments']} amendments and {audit['parse_failures']} parse failures are recorded. "
      f"The acceptance-time rule moves {audit['day0_moved_before_market_filters']} events before market filters and "
      f"{audit['day0_moved_final']} in the final sample. All models use the same complete observations within each stated sample.",note=True)
    page()

    h('Table 2. Tone by report type')
    p('Proportional scores are percentages; weighted scores are equation (1) sums. Document frequencies are fitted '
      'separately within each form here, in Figure 1 and in form-specific regressions. Full-sample regressions fit the pooled corpus.',note=True)
    table(tables[2][['form','measure','n','mean','sd','p25','median','p75']].rename(columns={
        'form':'Form','measure':'Measure','n':'N','mean':'Mean','sd':'SD','p25':'P25','median':'Median','p75':'P75'}),[38,137,43,59,59,59,60,60])
    p('Sentiment/uncertainty correlations (proportional, weighted): '+ '; '.join(
      f"{r['form']}: {r['prop']:.3f}, {r['tfidf']:.3f}" for r in audit['correlations'][1:])+'.',note=True)
    h('Table 3. Most frequent dictionary words')
    p('Each percentage divides a word count by the total token count in that dictionary category across the final sample.',note=True)
    neg=tables[3][tables[3].category.eq('Negative')].reset_index(drop=True)
    unc=tables[3][tables[3].category.eq('Uncertainty')].reset_index(drop=True)
    wordtable=pd.DataFrame({'Rank':neg['rank'],'Negative word':neg.word,'Share %':neg.share_pct,
                          'Uncertainty word':unc.word,'Share % ':unc.share_pct})
    table(wordtable,[35,163,65,182,70])
    p(f"The ten most frequent words account for {audit['top10_shares']['Negative']:.1f}% of negative tokens and "
      f"{audit['top10_shares']['Uncertainty']:.1f}% of uncertainty tokens. The dictionaries contain 2,355 and 297 words; "
      '40 words overlap, so the two scores are not mechanically independent.',note=True)
    page()

    h('Measures and filing-event design')
    p('For a category, the proportional score is its token count divided by all tokens. The weighted score sums '
      'w_ij = [(1 + ln tf_ij)/(1 + ln a_j)] ln(N/df_i) over observed category words, where a_j is total tokens divided by distinct tokens '
      'within document j. N and document frequency df_i refer to the exact estimation corpus. Natural logs give '
      '0.8480, 0.2885 and 0.5026 for documents “LOSS LOSS RISK GAIN”, “LOSS GAIN GAIN” and “RISK RISK RISK GAIN”, '
      'using category {LOSS, RISK}. This implements Loughran and McDonald (2011), equation (1).')
    p('Primary-document text retains visible XBRL facts and excludes hidden scaffolding, separate exhibits and tables with '
      'more than 15% digits among non-space characters. Uppercase alphabetic tokens have at least two characters and retain '
      'apostrophes and hyphens. Incorporated-by-reference text is not recovered.')
    p('Day 0 follows the NYSE calendar and the later of filing date or Eastern acceptance date, advanced one day for acceptance '
      'at or after 16:00. SPY-adjusted buy-and-hold returns run from day -1 close to +3 close. Volatility is daily-return sample '
      'SD times sqrt(252), using 55 returns over [-60,-6] and 60 over [+4,+63].')
    p('Size uses day -1 nominal price and accession-matched cover shares; separately tagged same-date classes are summed, '
      'using one class price as a proxy for all classes. Future or weighted-average shares are excluded. '
      'Subsequent splits are reversed for nominal prices and volumes; adjusted closes measure returns. '
      'Liquidity and prior excess return use [-60,-6]. Regression controls are listed with the tables.')
    corr=audit['correlations'][0]
    ex=audit['example']
    p(f"Full-sample sentiment/uncertainty correlations are {corr['prop']:.3f} for proportions and {corr['tfidf']:.3f} for weighted scores. "
      f"{ex['ticker']}'s {ex['form']} filed {ex['filing_date']} has {ex['negative_pct']:.2f}% negative words "
      f"and {ex['uncertainty_pct']:.2f}% uncertainty words (percentile ranks {100*ex['negative_percentile']:.0f} and "
      f"{100*ex['uncertainty_percentile']:.0f}). This is a relative contrast; it is not an upper-quartile negative-tone case. "
      'The high correlations indicate substantial common variation, so the two measures do not provide independent evidence.')
    p('Selected filing language: '+ex['sentence'],note=True)
    p('This passage concerns litigation. Dictionary counts register the legal vocabulary but do not determine whether a ruling was favorable.',note=True)
    p('MAY and COULD account for more than half of uncertainty tokens. These modal terms often qualify routine risk and contingency language. '
      'This concentration and their widespread occurrence support a large template component, although counts alone cannot establish copied text '
      'or changes in management beliefs. Earlier same-form filings would be needed for that distinction.')
    p(f"MAY appears in {audit['uncertainty_word_document_pct']['MAY']:.1f}% of filings and APPROXIMATELY in "
      f"{audit['uncertainty_word_document_pct']['APPROXIMATELY']:.1f}%. Their prevalence limits their ability to distinguish documents; "
      'inverse document frequency reduces their contribution accordingly.',note=True)
    h('Figure 1. Quarterly tone and VIX')
    story.append(Image(str(OUT/'figure1.png'),width=515,height=328))
    md.append('![Quarterly tone and VIX](outputs/figure1.png)\n')
    page()

    h('Table 4. Annual tone trends')
    p('Aggregate models include seasonal indicators and show both ordinary and Newey–West t-statistics (four lags). '
      'Within-company models include company effects, seasonal indicators and, in the pooled sample, report type. '
      'They exclude saturated calendar-quarter effects, which would absorb time. The main within-company inference clusters '
      'by company and calendar quarter, with min(company clusters, quarter clusters) minus one degrees of freedom.',note=True)
    trendrows=[]
    for sample_name in ['All','10-K','10-Q']:
        for tone in ['Negative_prop','Uncertainty_prop','Negative_tfidf','Uncertainty_tfidf']:
            within=row(4,sample_name,tone,'within_firm_trend')
            ols=row(4,sample_name,tone,'aggregate_trend','OLS')
            hac=row(4,sample_name,tone,'aggregate_trend','HAC4')
            mult=100 if tone.endswith('prop') else 1
            trendrows.append({'Sample':sample_name,'Measure':tone.replace('Negative','Neg.').replace('Uncertainty','Unc.').replace('_prop',' %').replace('_tfidf',' tf.idf'),
                 'Agg. slope':ols.coef*mult,'OLS t':ols.t,'NW t':hac.t,'Within slope':within.coef*mult,'Within t':within.t,'p':within.p})
    table(pd.DataFrame(trendrows),[39,86,70,52,52,83,68,65])
    p('Proportional slopes are percentage points per year; tf.idf slopes are weighted-score units per year. '
      'The aggregate series has at most 20 quarters. A low HAC p-value alone is insufficient evidence of a persistent economic trend.',note=True)
    p('All denotes pooled 10-K and 10-Q reports. Within-company cluster counts: '+ '; '.join(
       f"{name}: {int(row(4,name,'Negative_prop','within_firm_trend').firm_clusters)} companies / "
       f"{int(row(4,name,'Negative_prop','within_firm_trend').quarter_clusters)} quarters" for name in ['All','10-K','10-Q'])+'.',note=True)
    annual_neg=row(4,'10-K','Negative_prop','within_firm_trend')
    annual_unc=row(4,'10-K','Uncertainty_prop','within_firm_trend')
    quarterly_unc=row(4,'10-Q','Uncertainty_prop','within_firm_trend')
    p(f"The form-specific within-company results differ: annual-report negative tone rises {100*annual_neg.coef:.3f} "
      f"percentage points per year (t = {annual_neg.t:.2f}) and annual uncertainty rises {100*annual_unc.coef:.3f} "
      f"(t = {annual_unc.t:.2f}), while quarterly uncertainty falls {abs(100*quarterly_unc.coef):.3f} "
      f"(t = {quarterly_unc.t:.2f}). A single pooled trend would conceal this difference.")
    for tone,label in [('Negative_prop','Negative tone'),('Uncertainty_prop','Uncertainty')]:
        r=row(4,'All',tone,'within_firm_trend')
        p(f"{label} changes by {100*r.coef:+.3f} percentage points per year within companies "
          f"(two-way clustered t = {r.t:.2f}, p = {r.p:.3f}); this estimate is {strength(r)}. "
          'Company effects and reporting-season controls make this more informative than the aggregate slope.')
    for tone,label in [('Negative_tfidf','Weighted negative tone'),('Uncertainty_tfidf','Weighted uncertainty')]:
        r=row(4,'All',tone,'within_firm_trend')
        p(f"{label} changes by {r.coef:+.3f} score units per year (t = {r.t:.2f}, p = {r.p:.3f}). "
          'Weighted and proportional results are different measurements and should not be treated as independent replications.')
    p('The chart separates form types and removes company mean levels. In this unbalanced panel, company means reflect '
      'different entry and exit periods; the chart therefore does not fully remove selection over time. '
      'The within-company regression, rather than visual slope alone, determines the trend interpretation.')
    page()

    h('Table 5. Uncertainty and subsequent volatility')
    p('Dependent variable: annualised post-filing volatility. Coefficients use uncertainty fractions or tf.idf units. '
      'All models include company and quarter effects, size, liquidity, prior excess return and report type where applicable. '
      'Both specifications use identical observations. t and p use two-way company/quarter clustering.',note=True)
    v=tables[5][tables[5].inference.eq('firm_quarter_cluster')].copy()
    v['Measure']=v.measure.str.replace('Uncertainty_','',regex=False)
    v['Pre-vol']=v.model.eq('volatility_with_prevol').map({True:'Yes',False:'No'})
    vt=v[['sample','Measure','Pre-vol','coef','t','p','n']].rename(columns={'sample':'Sample','coef':'Coefficient','t':'t','p':'p','n':'N'})
    table(vt,[49,64,54,116,70,80,82])
    for tone,label in [('Uncertainty_prop','Proportional uncertainty'),('Uncertainty_tfidf','Weighted uncertainty')]:
        a=row(5,'All',tone,'volatility_without_prevol');b=row(5,'All',tone,'volatility_with_prevol')
        p(f"{label}: the coefficient changes from {fmt(a.coef)} (t = {a.t:.2f}) to {fmt(b.coef)} "
          f"(t = {b.t:.2f}) after controlling for pre-filing volatility, a difference of {fmt(b.coef-a.coef)}. "
          f"The controlled association is {strength(b)}. A one-standard-deviation increase corresponds to "
          f"{100*b.effect_1sd:+.2f} percentage points of annualised volatility. The controlled model asks whether tone adds information "
          'beyond existing volatility; the unadjusted model can reflect persistence in company risk.')
    h('Table 6. Negative sentiment and filing-period excess return')
    p('The four-session event can coincide with earnings news. Approximate 80% minimum detectable effects (MDE) are '
      'computed as (two-sided 5% t critical value + 0.842) times the coefficient standard error, then scaled by tone SD. '
      'Effect and MDE columns are percentage points of return per one tone SD; these describe precision, not observed power.',note=True)
    ret=tables[6][tables[6].inference.eq('firm_quarter_cluster')].copy()
    ret['Measure']=ret.measure.str.replace('Negative_','',regex=False)
    ret['Effect pp']=100*ret.effect_1sd;ret['MDE pp']=100*ret.mde80_1sd
    table(ret[['sample','Measure','coef','t','p','Effect pp','MDE pp','n']].rename(columns={'sample':'Sample','coef':'Coef.','n':'N'}),[43,55,71,58,63,78,78,69])
    r=row(6,'All','Negative_prop','filing_return')
    p(f"The proportional sentiment return coefficient is {r.coef:.3f} (t = {r.t:.2f}, p = {r.p:.3f}). "
      f"Its approximate detectable effect is {100*r.mde80_1sd:.2f} return percentage points per tone SD. "
      'A null at this precision does not establish zero price response. Event overlap and the short window make this test '
      'less decisive than a within-company language trend or a volatility association.')
    q=row(6,'10-Q','Negative_prop','filing_return')
    qw=row(6,'10-Q','Negative_tfidf','filing_return')
    p(f"The 10-Q-only return estimates have t = {q.t:.2f} (proportional, p = {q.p:.3f}) and "
      f"t = {qw.t:.2f} (weighted, p = {qw.p:.3f}). These subgroup results must be distinguished from the pooled null. "
      'They are tentative because the specifications are correlated, multiple tests are reported without multiplicity adjustment, '
      'and nearby earnings releases can drive the same return window.')
    page()

    h('Report-type differences')
    for label,tone in [('Negative','Negative words (%)'),('Uncertainty','Uncertainty words (%)')]:
        vals=tables[2][tables[2].measure.eq(tone)].set_index('form')
        p(f"{label} proportional-tone SD is {vals.loc['10-K','sd']:.3f} percentage points for 10-Ks and "
          f"{vals.loc['10-Q','sd']:.3f} for 10-Qs. Shorter reports can increase sampling noise in a ratio, while repeated "
          'templates can suppress variation; the observed variance reflects both mechanisms and report content.')
    for form in ['10-K','10-Q']:
        t=row(4,form,'Uncertainty_prop','within_firm_trend');v=row(5,form,'Uncertainty_prop','volatility_with_prevol')
        p(f"For {form}s, the uncertainty trend is {100*t.coef:+.3f} percentage points per year (t = {t.t:.2f}); "
          f"the volatility coefficient with pre-volatility is {v.coef:.3f} (t = {v.t:.2f}). "
          'These are separate within-form estimates; differing significance alone is not a formal test of coefficient equality.')
    va=row(5,'10-Q','Uncertainty_tfidf','volatility_without_prevol')
    vb=row(5,'10-Q','Uncertainty_tfidf','volatility_with_prevol')
    p(f"For quarterly weighted uncertainty, adding pre-volatility reduces the volatility coefficient from {va.coef:.6f} "
      f"(p = {va.p:.3f}) to {vb.coef:.6f} (p = {vb.p:.3f}). The apparent association is no longer significant "
      'once existing volatility is controlled. This supports interpreting the uncontrolled association cautiously.')
    p('10-Ks contain fuller annual business and risk disclosures, but more words need not imply more new information. '
      '10-Qs can contain timely updates, yet their proximity to earnings announcements prevents a clean attribution of the '
      'filing-window return to textual tone alone. Novel changes relative to the previous same-form filing would better distinguish signal from templates.')
    h('Interpretation and limitations')
    p('The annual negative-tone increase and quarterly uncertainty decline receive the most weight: both persist within companies under proportional '
      'and weighted measurement. The annual uncertainty increase is less robust because its weighted trend is insignificant. '
      'The controlled volatility models provide no convincing positive incremental association. The quarterly return association remains tentative '
      'given event contamination and multiple tests. These are conditional associations, not causal effects or a live trading strategy.')
    vc=row(5,'All','Uncertainty_prop','volatility_with_prevol')
    p(f"For pooled proportional uncertainty, the controlled 95% interval is [{100*vc.ci_low*vc.tone_sd:.2f}, "
      f"{100*vc.ci_high*vc.tone_sd:.2f}] percentage points of annualised volatility per tone SD. "
      'This bounds the incremental association under the specification. The null should not be dismissed with a blanket claim that every test lacks power.')
    one=tables[4][tables[4].inference.eq('firm_cluster')]
    two=tables[4][tables[4].inference.eq('firm_quarter_cluster')]
    compare=one.merge(two,on=['sample','measure','model'],suffixes=('_firm','_two'))
    changed=int(((compare.p_firm<.05)!=(compare.p_two<.05)).sum())
    p(f"{changed} of {len(compare)} within-company trend tests change 5% significance when moving from company-only to two-way clustering. "
      'The main tables use the latter to allow shared quarterly shocks. Only 20 time clusters remain, so even corrected inference is approximate. '
      'All estimated specifications are retained in the notebook: four tone trends, two uncertainty-volatility measures with both controls specifications, '
      'and two sentiment-return measures, pooled and by form, with both clustering choices. There is no winsorisation or selective removal of inconvenient estimates.')
    if (OUT/'survivorship.json').exists():
        s=json.loads((OUT/'survivorship.json').read_text())
        p(f"Of {s['early_unique_security_keys']} distinct securities in the May 6, 2021 holdings, "
          f"{s['absent_security_keys']} ({100*s['absent_security_keys']/s['early_unique_security_keys']:.1f}%) "
          'do not match the frozen 2026 holdings by either normalized ticker or valid CUSIP. '
          'The universe is selected using 2026 holdings, so every company in the study survived this selection rule. '
          'Identity changes, mergers and share classes mean these security absences cannot all be interpreted as failed companies.')
    p('Selection can exclude firms with deteriorating outcomes and distort measured trends. The mixed holdings dates, incomplete historical identifiers, '
      'strict share-count coverage, common-case filters and benchmark choice further limit generalisation. Full-corpus tf.idf uses later filings '
      'to estimate word weights; it is a descriptive retrospective measure, not a live forecasting protocol.')
    h('Next step')
    p('Reconstruct a point-in-time holdings universe and score only language newly introduced since the previous comparable filing. '
      'Combine that design with earnings timestamps and forward-only dictionary weights. This requires historical identifier mapping and additional text alignment, '
      'but directly addresses selection, template repetition and event contamination.')
    h('Sources')
    p('Loughran, T. and B. McDonald (2011), “When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks,” '
      'Journal of Finance 66(1), 35–65. https://doi.org/10.1111/j.1540-6261.2010.01625.x. '
      'SEC EDGAR filings and company facts: https://www.sec.gov/edgar. Market series: Yahoo Finance via yfinance. '
      'Loughran–McDonald Master Dictionary: https://sraf.nd.edu/loughranmcdonald-master-dictionary/. '
      'Holdings: https://github.com/robynge/ark-routine and the course starter repository.',note=True)
    p('Illustrative filing: '+ex['doc_url'],note=True)
    def footer(canvas,doc):
        canvas.setFont('Helvetica',7);canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(40,22,'Uncertainty and sentiment · 2021–2025')
        canvas.drawRightString(A4[0]-40,22,str(doc.page))
    doc=SimpleDocTemplate(str(OUT/'report.pdf'),pagesize=A4,rightMargin=40,leftMargin=40,
                         topMargin=34,bottomMargin=35,title='Uncertainty and sentiment in financial reports',author='')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    (ROOT/'REPORT.md').write_text('# Uncertainty and sentiment in financial reports\n\n'+'\n'.join(md))
    print(OUT/'report.pdf')


if __name__=='__main__': main()

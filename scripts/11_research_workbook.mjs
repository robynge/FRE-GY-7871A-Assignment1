// Run from the repository root with the bundled Node runtime.
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

// Stdlib CSV parsing preserves quoted fields and identifiers; no model is refitted.
const python='/Users/mfr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const files=['table1_universe','table1','table2','table3','table4','table5','table6','text_sample','volatility_sample','return_sample'];
const input=JSON.parse(execFileSync(python,['-c',`import csv,json,sys
print(json.dumps({name:list(csv.DictReader(open('outputs/'+name+'.csv'))) for name in sys.argv[1:]}))`,...files],{maxBuffer:20*1024*1024,encoding:'utf8'}));
const meta=JSON.parse(await fs.readFile('outputs/audit.json','utf8'));
const wb=Workbook.create();
const sheets=Object.fromEntries(['Summary','Sample','Tone','Dictionary','Trends','Volatility','Returns','Filings','Method'].map(n=>[n,wb.worksheets.add(n)]));
const ink='#0A0A23',accent='#8264FF',tint='#F0ECFF',muted='#676777';
const col=n=>{let s='';for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const num=x=>x===''||x===undefined?null:Number(x);
const date=x=>x?new Date(x+'T12:00:00Z'):null;
const val=(s,c,v)=>s.getRange(c).values=[[v]];
const formula=(s,c,f)=>s.getRange(c).formulas=[[f]];
const dec='0.000;-0.000;0.000',sci='0.000E+00',pct='0.00%;-0.00%;0.00%';
function base(s,last,row,title,subtitle){
  s.showGridLines=false;
  s.getRange(`A1:${last}${row}`).format={font:{name:'Arial',size:10,color:ink},rowHeight:22,columnWidth:17,verticalAlignment:'center'};
  val(s,'A2',title);s.getRange('A2').format.font={size:15,bold:true,color:ink};
  val(s,'A3',subtitle);s.getRange('A3').format.font={color:muted};
  s.getRange(`A4:${last}4`).format.borders={bottom:{style:'thin',color:accent}};
  s.freezePanes.freezeRows(6);s.freezePanes.freezeColumns(2);
}
function table(s,row,labels,rows,name){
  s.getRange(`A${row}:${col(labels.length)}${row}`).values=[labels];
  if(rows.length)s.getRange(`A${row+1}:${col(labels.length)}${row+rows.length}`).values=rows;
  const t=s.tables.add(`A${row}:${col(labels.length)}${row+rows.length}`,true,name);t.style='TableStyleLight1';
  s.getRange(`A${row}:${col(labels.length)}${row}`).format={fill:tint,font:{bold:true,color:ink},wrapText:true,rowHeight:46,horizontalAlignment:'center'};
}
function widths(s,rows,pairs){for(const [c,w]of pairs)s.getRange(`${c}1:${c}${rows}`).format.columnWidth=w;}
const measure=x=>x.replace('_prop',' word share').replace('_tfidf',' weighted score');
const inference=x=>({firm_quarter_cluster:'Company + calendar-quarter clusters',firm_cluster:'Company clusters',HAC4:'Newey–West, 4 lags',OLS:'Ordinary OLS'})[x];

const f=sheets.Filings, end=input.text_sample.length+6;
const vm=new Map(input.volatility_sample.map(r=>[r.accession,r])),rm=new Map(input.return_sample.map(r=>[r.accession,r]));
base(f,'AC',end,'Filing observations','Text-sample word weights are pooled; outcome-sample weights are fitted separately. Shares are fractions displayed as percentages.');
table(f,6,['Ticker','Company','CIK','Form','Filed','Period end','Trading day 0','Words','Distinct words','Negative share','Uncertainty share','Negative weighted score','Uncertainty weighted score','Volatility sample','Return sample','Prior annualized volatility','Subsequent annualized volatility','Four-session excess return','Prior excess return','Log company size','Log dollar volume','Prior nominal price USD','Outstanding shares','Volatility-sample uncertainty score','Return-sample negative score','SEC filing source','Accession','Filing calendar quarter','Acceptance timestamp UTC'],input.text_sample.map(r=>{
  const v=vm.get(r.accession),q=rm.get(r.accession);
  return [r.ticker,r.company,r.cik,r.form,date(r.filing_date),date(r.report_date),date(r.day0),num(r.n_words),num(r.n_distinct),num(r.Negative_prop),num(r.Uncertainty_prop),num(r.Negative_tfidf),num(r.Uncertainty_tfidf),v?'Yes':'No',q?'Yes':'No',num(r.pre_vol),num(r.post_vol),num(r.event_excess),num(r.pre_excess),num(r.log_size),num(r.log_dollar_volume),num(r.price_minus1),num(r.shares_outstanding),v?num(v.Uncertainty_tfidf):null,q?num(q.Negative_tfidf):null,r.doc_url,r.accession,r.quarter,r.acceptance_datetime];
}),'ResearchFilings');
widths(f,end,[['A',12],['B',49],['C',17],['D',10],['Z',80],['AA',29],['AB',21],['AC',31],['X',27],['Y',27]]);f.getRange(`C7:C${end}`).setNumberFormat('0000000000');
f.getRange(`E7:G${end}`).setNumberFormat('yyyy-mm-dd');f.getRange(`H7:I${end}`).setNumberFormat('#,##0');
f.getRange(`J7:K${end}`).setNumberFormat(pct);f.getRange(`L7:M${end}`).setNumberFormat(dec);f.getRange(`P7:S${end}`).setNumberFormat(pct);f.getRange(`T7:V${end}`).setNumberFormat(dec);f.getRange(`W7:W${end}`).setNumberFormat('#,##0');f.getRange(`X7:Y${end}`).setNumberFormat(dec);

const a=sheets.Sample;
base(a,'E',51,'Sample construction','Holdings identify a retrospective company universe; text, volatility and return filters are separate.');
table(a,6,['Universe filter','Removed','Remaining','Unit'],input.table1_universe.map(r=>[r.filter==='foreign_reporting_forms'?'20-F / 40-F reporting companies':r.filter==='no_report_evidence'?'No qualifying report evidence by cutoff':r.filter,num(r.removed),num(r.remaining),r.unit]),'CompanySelection');
table(a,16,['Sample','Filing filter','Removed','Remaining','Companies'],input.table1.map(r=>[r.sample,r.filter,num(r.removed),num(r.remaining),num(r.companies)]),'FilingSelection');
widths(a,51,[['A',47],['B',60],['C',18],['D',18],['E',18]]);
val(a,'A38','Holdings date: September 9, 2026 for ARKK, ARKQ, ARKW, ARKF, ARKG and ARKX.');
val(a,'A39','Company identity uses SEC CIK; different share classes are combined. Original forms only enter text analysis.');
val(a,'A41','Filing cutoff');val(a,'C41',date(meta.sample_end));val(a,'A42','Completed market sessions through');val(a,'C42',date(meta.market_last_date));
val(a,'A43','Latest volatility-sample filing');val(a,'C43',date(meta.volatility_last_filing_date));val(a,'A44','Latest return-sample filing');val(a,'C44',date(meta.return_last_filing_date));a.getRange('C41:C44').setNumberFormat('yyyy-mm-dd');
val(a,'A46','2026 Q3 is incomplete. Recent filings remain in text analysis when future market windows are unavailable.');

const tone=sheets.Tone;
base(tone,'J',70,'Tone by report type','Word-share statistics are percentage units; weighted statistics are score units fitted within each form.');
table(tone,6,['Form','Measure','Filings','Mean','SD','25th percentile','Median','75th percentile','Minimum','Maximum'],input.table2.map(r=>[r.form,r.measure,num(r.n),...['mean','sd','p25','median','p75','min','max'].map(k=>num(r[k]))]),'ToneStatistics');
widths(tone,70,[['A',14],['B',32]]);tone.getRange('D7:J14').setNumberFormat(dec);tone.getRange('C7:C14').setNumberFormat('#,##0');
table(tone,18,['Sample','Share correlation','Weighted correlation'],meta.correlations.map(r=>[r.form,r.prop,r.tfidf]),'ToneCorrelations');tone.getRange('B19:C21').setNumberFormat(dec);
table(tone,25,['Form','Filing quarter','Filings'],meta.quarter_counts.map(r=>[r.form,r.quarter,r.n]),'QuarterlyCoverage');
val(tone,'E26','Correlations compare negative and uncertainty language.');val(tone,'E27','Annual and quarterly reports differ in content and length.');val(tone,'E28','Sparse annual-report quarters can represent very few companies.');

const rankStats=JSON.parse(execFileSync(python,['-c',`import json,pandas as pd
x=pd.read_csv('outputs/text_sample.csv');out=[]
for c in ['Negative','Uncertainty']:
 a=x[c+'_prop'].rank(pct=True);b=x[c+'_tfidf'].rank(pct=True)
 out.append([c,float(a.corr(b)),float(abs(a-b).mean()*100)])
print(json.dumps(out))`],{encoding:'utf8'}));
tone.getRange('E31:G31').values=[['Category','Share vs weighted\nrank correlation','Mean absolute\npercentile movement']];
tone.getRange('E32:G33').values=rankStats;tone.getRange('E31:G31').format={fill:tint,font:{bold:true,color:ink},wrapText:true,rowHeight:58};tone.getRange('F32:G33').setNumberFormat(dec);
for(const [i,text]of [
 [35,'The two scores rank the same filings within each category, using pooled text-sample weights.'],
 [36,'Correlation 1 means identical ordering. Lower correlation means more reordering.'],
 [37,'Percentile movement is rank-position points, not a word-share percentage-point change.'],
 [38,rankStats[1][2]>rankStats[0][2]?'Weighting changes uncertainty rankings more; that alone does not establish better forecasting.':'Weighting does not change uncertainty rankings more; ranking changes do not establish forecasting performance.'],
 [39,`MAY appears in ${meta.uncertainty_word_document_pct.MAY.toFixed(3)}% of filings. APPROXIMATELY appears in ${meta.uncertainty_word_document_pct.APPROXIMATELY.toFixed(3)}%.`]]){tone.getRange(`E${i}:J${i}`).merge();val(tone,`E${i}`,text);tone.getRange(`E${i}:J${i}`).format={wrapText:true,rowHeight:35};}

const d=sheets.Dictionary;
base(d,'F',80,'Dictionary frequencies','Active Loughran–McDonald categories | 1993–2025 dictionary, updated March 2026');
table(d,6,['Category','Rank','Word','Occurrences','Category-token share','Cumulative share'],input.table3.map(r=>[r.category,num(r.rank),r.word,num(r.count),num(r.share_pct)/100,null]),'DictionaryFrequencies');
input.table3.forEach((r,i)=>formula(d,`F${i+7}`,`=SUMIFS($E$7:E${i+7},$A$7:A${i+7},A${i+7})`));
d.getRange('D7:D66').setNumberFormat('#,##0');d.getRange('E7:F66').setNumberFormat(pct);widths(d,80,[['A',19],['B',12],['C',27],['D',20],['E',25],['F',23]]);
table(d,70,['Category','Active words','Top 10 token share'],[['Negative',meta.lexicon_counts.Negative,null],['Uncertainty',meta.lexicon_counts.Uncertainty,null]],'DictionaryScope');
formula(d,'C71','=SUMIFS(E7:E66,A7:A66,A71,B7:B66,"<=10")');formula(d,'C72','=SUMIFS(E7:E66,A7:A66,A72,B7:B66,"<=10")');d.getRange('C71:C72').setNumberFormat(pct);
val(d,'A74','40 words belong to both categories. Category shares are not shares of total document words.');
val(d,'A75','A positive dictionary flag identifies an active word; 10 removed negative entries are excluded.');
val(d,'A77','Source: https://sraf.nd.edu/loughranmcdonald-master-dictionary/');

const tr=sheets.Trends;
const trends=[...input.table4].sort((a,b)=>(a.inference!=='firm_quarter_cluster')-(b.inference!=='firm_quarter_cluster'));
base(tr,'P',trends.length+11,'Annual tone trends','Primary inference: within-company estimates with company/calendar-quarter clustering.');
table(tr,6,['Sample','Measure','Model','Inference','Slope units per year','Slope','Standard error','t statistic','p value','95% lower','95% upper','Observations','Company clusters','Quarter clusters','Inference df','R squared'],trends.map(r=>{
  const scale=r.measure.endsWith('_prop')?100:1;
  return [r.sample,measure(r.measure),r.model==='within_firm_trend'?'Within company':'Quarter means',inference(r.inference),scale===100?'Percentage points':'Weighted-score units',num(r.coef)*scale,num(r.se)*scale,num(r.t),num(r.p),num(r.ci_low)*scale,num(r.ci_high)*scale,num(r.n),num(r.firm_clusters),num(r.quarter_clusters),num(r.df_inference),num(r.r_squared)];
}),'TrendEstimates');
widths(tr,trends.length+11,[['A',12],['B',30],['C',21],['D',41],['E',25]]);tr.getRange(`F7:H${trends.length+6}`).setNumberFormat(dec);tr.getRange(`I7:I${trends.length+6}`).setNumberFormat(sci);tr.getRange(`J7:K${trends.length+6}`).setNumberFormat(dec);tr.getRange(`P7:P${trends.length+6}`).setNumberFormat(dec);
val(tr,`A${trends.length+8}`,'Models control reporting season; within-company models include company effects and a pooled 10-K indicator.');
val(tr,`A${trends.length+9}`,'Calendar-quarter fixed effects are excluded from trend models because they would absorb the linear trend.');

const resultRows={};
for(const [name,key]of [['Volatility','table5'],['Returns','table6']]){
  const s=sheets[name],rows=[...input[key]].sort((a,b)=>(a.inference!=='firm_quarter_cluster')-(b.inference!=='firm_quarter_cluster'));resultRows[name]=rows;
  base(s,'R',rows.length+13,name==='Volatility'?'Uncertainty and subsequent volatility':'Negative language and filing returns','Primary inference: company/calendar-quarter clusters | estimates and intervals retain full numerical precision.');
  table(s,6,['Sample','Tone measure','Prior volatility control','Inference','Coefficient','Standard error','t statistic','p value','Filings','Tone SD','Effect of 1 SD, percentage points','95% lower, pp','95% upper, pp','80% detectable effect, pp','Company clusters','Quarter clusters','Inference df','R squared'],rows.map(r=>[r.sample,measure(r.measure),r.model==='volatility_without_prevol'?'No':'Yes',inference(r.inference),num(r.coef),num(r.se),num(r.t),num(r.p),num(r.n),num(r.tone_sd),null,null,null,num(r.mde80_1sd)*100,num(r.firm_clusters),num(r.quarter_clusters),num(r.df_inference),num(r.r_squared)]),'Research'+name);
  rows.forEach((r,i)=>{const j=i+7;formula(s,`K${j}`,`=E${j}*J${j}*100`);val(s,`L${j}`,num(r.ci_low)*num(r.tone_sd)*100);val(s,`M${j}`,num(r.ci_high)*num(r.tone_sd)*100);});
  widths(s,rows.length+13,[['A',12],['B',30],['C',23],['D',41],['K',24],['L',22],['M',22],['N',25]]);
  for(const c of ['E','F','H','J'])s.getRange(`${c}7:${c}${rows.length+6}`).setNumberFormat(sci);
  s.getRange(`K7:N${rows.length+6}`).setNumberFormat(dec);s.getRange(`G7:G${rows.length+6}`).setNumberFormat(dec);s.getRange(`R7:R${rows.length+6}`).setNumberFormat(dec);
  val(s,`A${rows.length+8}`,'Coefficient units: outcome fraction per one-unit tone fraction, or per one weighted-score unit. SD uses the same tone units.');
  val(s,`A${rows.length+9}`,'Effect of 1 SD = coefficient × tone SD × 100. Intervals and detectable effects are in outcome percentage points (pp).');
  val(s,`A${rows.length+10}`,name==='Volatility'?'Both specifications use identical observations within each sample. Post-filing volatility is annualized.':'Return outcome is SPY-adjusted buy-and-hold return across four sessions [0,+3].');
  val(s,`A${rows.length+11}`,'Models include company and calendar-quarter effects, log size, log dollar volume, prior excess return and a pooled 10-K indicator.');
}

const m=sheets.Method;
base(m,'B',42,'Definitions and sources','Retrospective associations in a holdings-selected company universe');m.freezePanes.unfreeze();
const notes=[
 ['Dictionary','Loughran–McDonald Master Dictionary 1993–2025, updated March 2026. Active category flags greater than zero.'],
 ['Proportional score','Category-word occurrences / all retained words. Example: 200 uncertainty occurrences / 10,000 words = 2%, or 2 per 100 words. Repeated uses count each time.'],
 ['Weighted score','Score units, not percentages; common vocabulary receives less weight. For each observed category word: (1 + ln term count) / (1 + ln average term count) × ln(documents / document frequency); sum across words.'],
 ['Weighting corpus','Word weights are fitted separately in text, volatility and return samples, and separately within report type for form-specific analysis.'],
 ['Text extraction','Primary visible document; hidden text, exhibits and tables with more than 15% digits among non-space characters excluded.'],
 ['Tokenization','Alphabetic tokens have at least two characters; apostrophes and hyphens retained. Incorporated-by-reference text is not recovered.'],
 ['Text selection','At least 2,000 words for 10-K / 1,000 for 10-Q. Earliest company filing per calendar quarter; amendments excluded.'],
 ['Trading day 0','First NYSE session on or after the later of filing date and Eastern acceptance date; acceptance at/after actual close moves to next session.'],
 ['Market windows','Pre-volatility: sample SD of returns [-60,-6]; post-volatility: sample SD [+4,+63]. Multiply by square root of 252.'],
 ['Returns','Adjusted-price buy-and-hold return from day -1 through +3, less corresponding SPY return. No future returns imputed.'],
 ['Company size','Day -1 nominal price × accession-matched outstanding shares. Same-date classes use one class price as proxy.'],
 ['Liquidity','Mean nominal dollar volume over [-60,-6]. Prior excess return uses the same window; all logarithms are natural.'],
 ['Outcome selection','Day 0 and prior price at least $3, elapsed future window, complete history, outstanding shares and model controls. No winsorisation.'],
 ['Inference','A p value measures incompatibility with zero association under model assumptions; p < 0.05 is the conventional threshold. It is not the probability a conclusion is true.'],
 ['Percentage points','pp = percentage points. A share rising from 2.0% to 2.5% rises by 0.5 pp (25% relative growth). It does not rise by 0.5% relative to its earlier value.'],
 ['Annual trend','Estimated average change per elapsed year after controlling company levels and reporting season; not a specific company’s latest year-on-year change.'],
 ['Standard deviation','SD describes the typical spread of scores. A 1 SD higher score is not a one-percentage-point higher word share. Effect estimates are model comparisons, not actual before/after changes.'],
 ['Confidence interval','95% intervals describe estimation uncertainty. An interval crossing zero permits either sign; failure to meet the p < 0.05 threshold does not establish zero effect.'],
 ['Missing observations','Blank observations are unavailable, not zero. Volatility and return inclusion indicators identify usable model observations.'],
 ['Interpretation','Dictionary language is not default probability. Disclosure length, recurring language and section changes can alter scores.'],
 ['Selection','September 9, 2026 holdings select today’s companies. Identifier gaps limit generalisation; full-corpus weights use later filings.'],
 ['Causality','Earnings releases can coincide with filing windows. Multiple correlated unadjusted tests limit isolated significance claims.'],
 ['Estimates','Model estimates are fixed research results, not regressions recalculated by editing observations in Excel.'],
 ['Dictionary source','https://sraf.nd.edu/loughranmcdonald-master-dictionary/'],
 ['Method paper','https://doi.org/10.1111/j.1540-6261.2010.01625.x'],
 ['Filings','https://www.sec.gov/edgar — individual primary-document links accompany observations.'],
 ['Market data','https://finance.yahoo.com/ — adjusted and nominal price histories, volumes and corporate actions.'],
 ['Holdings archive','https://github.com/robynge/ark-routine'],
 ['Course materials','https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1']
];
table(m,6,['Topic','Definition or source'],notes,'ResearchDefinitions');widths(m,42,[['A',25],['B',120]]);m.getRange(`B7:B${notes.length+6}`).format.wrapText=true;m.getRange(`A7:B${notes.length+6}`).format.rowHeight=40;

const s=sheets.Summary;
base(s,'E',44,'ARK holdings: financial-report language','Companies appearing across six ARK ETF holdings lists dated September 9, 2026 | historical filings from 2021 through the cutoff');s.freezePanes.unfreeze();s.tabColor=accent;
table(s,6,['Sample','Filings','Companies','Latest eligible filing'],[['Text',null,meta.final_companies,null],['Volatility',null,meta.volatility_companies,date(meta.volatility_last_filing_date)],['Returns',null,meta.return_companies,date(meta.return_last_filing_date)]],'ResearchSummary');
formula(s,'D7',`=MAX(Filings!E7:E${end})`);formula(s,'B7',`=COUNTA(Filings!A7:A${end})`);formula(s,'B8',`=COUNTIFS(Filings!N7:N${end},"Yes")`);formula(s,'B9',`=COUNTIFS(Filings!O7:O${end},"Yes")`);s.getRange('D7:D9').setNumberFormat('yyyy-mm-dd');
widths(s,44,[['A',25],['B',26],['C',26],['D',28],['E',28]]);s.getRange('B7:C9').setNumberFormat('#,##0');
s.getRange('A10:E11').merge();val(s,'A10','Uncertainty word share means uncertainty-word occurrences divided by all retained words. 200 uses in 10,000 words = 2%, or two per 100 words. Negative share counts adverse vocabulary in the same way. These shares are not the probability of a loss.');s.getRange('A10:E11').format={wrapText:true,rowHeight:32};
const years=[...new Set(input.text_sample.map(r=>Number(r.filing_date.slice(0,4))))].sort();
table(s,12,['Filing year','Annual negative share','Annual uncertainty share','Quarterly negative share','Quarterly uncertainty share'],years.map(y=>[y===2026?'2026 partial':y,null,null,null,null]),'ObservedAnnualShares');
years.forEach((year,i)=>{const rr=i+13;[['B','10-K','J'],['C','10-K','K'],['D','10-Q','J'],['E','10-Q','K']].forEach(([dest,form,src])=>formula(s,`${dest}${rr}`,`=AVERAGEIFS(Filings!${src}7:${src}${end},Filings!D7:D${end},"${form}",Filings!E7:E${end},">="&DATE(${year},1,1),Filings!E7:E${end},"<"&DATE(${year+1},1,1))`));});
s.getRange(`B13:E${years.length+12}`).setNumberFormat(pct);
const annualNeg=input.table4.filter(r=>r.sample==='10-K'&&r.model==='within_firm_trend'&&r.inference==='firm_quarter_cluster'&&r.measure.startsWith('Negative'));
const controlled=input.table5.filter(r=>r.inference==='firm_quarter_cluster'&&r.model==='volatility_with_prevol');const significant=controlled.filter(r=>num(r.p)<.05).length;
const returns=input.table6.filter(r=>r.inference==='firm_quarter_cluster');const returnSignificant=returns.filter(r=>num(r.p)<.05).length;
const summaryNotes=[
 [20,'Each percentage averages individual filing word shares in that filing year. It is an observed level, not a model coefficient.'],
 [21,'2026 is partial through September 9. Company composition and filing counts vary, so annual averages alone do not prove a within-company trend.'],
 [23,'Question 1: Is the language changing?'],
 [24,annualNeg.every(r=>num(r.coef)>0&&num(r.p)<.05)?'Both scoring methods support an upward annual-report negative-language trend after company differences and reporting season are considered.':'The adjusted tests do not establish an upward annual-report negative-language trend under both scoring methods.'],
 [25,'The percentages above show the observed history. Language changes do not establish that operating conditions improved or worsened.'],
 [27,'Question 2: Does uncertainty language precede larger stock-price fluctuations?'],
 [28,`${significant} of ${controlled.length} tests meet the statistical threshold after accounting for prior stock volatility. The model comparison tests information beyond how volatile the stock already was.`],
 [29,'Future volatility covers 60 trading days beginning on day +4 after the filing event. The detailed estimates compare models, not observed before-and-after volatility.'],
 [31,'Question 3: Does negative language accompany weaker stock returns?'],
 [32,`${returnSignificant} of ${returns.length} return tests meet the statistical threshold. The return is the stock’s four-session gain or loss minus SPY over the same sessions.`],
 [33,'A result below the evidence threshold does not prove zero response. Earnings news can overlap the filing and the short window limits precision.'],
 [35,'A second score gives less weight to words used in almost every filing. Both scoring methods are reported to assess whether conclusions depend on word weighting.'],
 [37,'Company selection uses only September 9, 2026 holdings. Historical prices and filings describe today’s companies, not the historical ARK portfolio.'],
 [38,'The course-period 2021–2025 analysis is separate. This workbook contains the extended sample through September 9, 2026.'],
 [40,'Dictionary shares measure financial-report vocabulary. Risk-section additions, omissions and repeated wording can change a share without an equivalent change in operating risk.']
];
for(const [r,text]of summaryNotes){s.getRange(`A${r}:E${r}`).merge();val(s,`A${r}`,text);s.getRange(`A${r}:E${r}`).format={wrapText:true,rowHeight:36};if([23,27,31].includes(r))s.getRange(`A${r}`).format.font={bold:true,size:12,color:ink};}

wb.recalculate();
const get=(name,cell)=>sheets[name].getRange(cell).values[0][0];
assert.equal(get('Summary','B7'),meta.final_filings);assert.equal(get('Summary','B8'),meta.volatility_filings);assert.equal(get('Summary','B9'),meta.return_filings);
years.forEach((year,i)=>{[['B','10-K','Negative_prop'],['C','10-K','Uncertainty_prop'],['D','10-Q','Negative_prop'],['E','10-Q','Uncertainty_prop']].forEach(([cell,form,key])=>{const rows=input.text_sample.filter(r=>r.form===form&&Number(r.filing_date.slice(0,4))===year);assert.ok(Math.abs(get('Summary',`${cell}${i+13}`)-rows.reduce((a,r)=>a+num(r[key]),0)/rows.length)<1e-12);});});
for(const [name,rows]of Object.entries(resultRows))rows.forEach((r,i)=>assert.ok(Math.abs(get(name,`K${i+7}`)-num(r.effect_1sd)*100)<1e-9));
const before=get('Volatility','E7'),effect=get('Volatility','K7');val(sheets.Volatility,'E7',before*2);wb.recalculate();assert.ok(Math.abs(get('Volatility','K7')-effect*2)<1e-10);val(sheets.Volatility,'E7',before);wb.recalculate();
assert.ok(Math.abs(get('Dictionary','C71')-meta.top10_shares.Negative/100)<1e-12);assert.ok(Math.abs(get('Dictionary','C72')-meta.top10_shares.Uncertainty/100)<1e-12);
const preview='outputs/research_workbook_preview';await fs.mkdir(preview,{recursive:true});
const checks=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'Formula error scan'});await fs.writeFile(`${preview}/inspection.json`,JSON.stringify(checks));
for(const [sheetName,range]of [['Summary','A1:E21'],['Summary','A23:E40'],['Sample','A1:E35'],['Tone','A1:J21'],['Tone','E25:J39'],['Dictionary','A1:F20'],['Trends','A1:K18'],['Volatility','A1:N19'],['Returns','A1:N19'],['Filings','A1:M16'],['Method','A1:B35']]){
  const png=await wb.render({sheetName,range,scale:1.2,format:'png'});await fs.writeFile(`${preview}/${sheetName}_${range.replace(':','-')}.png`,new Uint8Array(await png.arrayBuffer()));
}
const output=`outputs/ARK_Holdings_Sentiment_and_Uncertainty_Data_${meta.as_of_date}.xlsx`;
await(await SpreadsheetFile.exportXlsx(wb)).save(output);
console.log(JSON.stringify({output,sheets:Object.keys(sheets),filings:input.text_sample.length,modelRows:trends.length+input.table5.length+input.table6.length,checks:'Counts, all 1-SD effects, dictionary totals and live recalculation passed.'}));

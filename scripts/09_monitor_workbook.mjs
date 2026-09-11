// Run from the repository root with the bundled artifact-tool dependency available.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const out = 'outputs/company_monitor';
const data = JSON.parse(await fs.readFile(`${out}/data.json`, 'utf8'));
const holdings = JSON.parse(await fs.readFile('outputs/current_holdings/data.json', 'utf8'));
assert.ok(data.current_companies?.length, 'Current company universe is required');
const currentCompanies=data.current_companies.filter(r=>r.ticker||r.company||r.sec_name);
const quarters=[];for(let year=2021;year<=2026;year++)for(let q=1;q<=4;q++)if(`${year}Q${q}`<='2026Q3')quarters.push(`${year}Q${q}`);
const cikKey=v=>String(v??'').replace(/^0+/,'');
const tickerKey=v=>String(v??'').toUpperCase().replace(/[^A-Z0-9]/g,'');
const byCik=new Map(currentCompanies.filter(r=>r.cik).map(r=>[cikKey(r.cik),r]));
const byTicker=new Map(currentCompanies.flatMap(r=>[r.ticker,...String(r.tickers??'').split('|')].filter(Boolean).map(t=>[tickerKey(t),r])));
const nameKey=v=>String(v??'').toUpperCase().replace(/[^A-Z0-9]/g,'');
const byName=new Map(currentCompanies.filter(r=>r.company??r.sec_name).map(r=>[nameKey(r.company??r.sec_name),r]));
const bySecurity=new Map(holdings.latest_holdings.map(r=>[r.security_key,byTicker.get(tickerKey(r.normalized_ticker??r.ticker))??byName.get(nameKey(r.company))]));
const companyFor=r=>byCik.get(cikKey(r.cik))??bySecurity.get(r.security_key)??byTicker.get(tickerKey(r.normalized_ticker??r.ticker))??byName.get(nameKey(r.company));
const filingCoverage=r=>({no_10x_filings:'No 10-K or 10-Q filings',foreign_local_listing:'Foreign listing; no scored 10-Q',foreign_reporting_forms:'Foreign reporting forms; no 10-Q',unresolved:'No matched SEC company identifier'})[r.coverage_status]??String(r.coverage_status??r.sec_status??r.status??'No eligible 10-Q').replaceAll('_',' ');
function reportQuarter(period){
  const d=new Date(`${period}T12:00:00Z`);let closest=null;
  for(let year=d.getUTCFullYear()-1;year<=d.getUTCFullYear()+1;year++)for(let q=1;q<=4;q++){
    const end=new Date(Date.UTC(year,q*3,0,12)),gap=Math.abs(d-end)/86400000;
    if(gap<=7&&(!closest||gap<closest.gap))closest={gap,quarter:`${year}Q${q}`};
  }
  return closest?.quarter??`${d.getUTCFullYear()}Q${Math.floor(d.getUTCMonth()/3)+1}`;
}
const wb = Workbook.create();
const sheets = Object.fromEntries(['Research findings','Summary','Negative History','Uncertainty History','ETF Weights','Entry Dates','Annual Filings','Filings','Weight Inputs','Coverage','Sections'].map(n=>[n,wb.worksheets.add(n)]));
const navy='#23384D', blue='#235A81', gray='#F0F3F5';
const pct='0.00%;-0.00%;0.00%', pp='+0.000;-0.000;0.000';
const column = n => {let s=''; for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const date = s => s ? new Date(`${s}T12:00:00Z`) : null;
const formula=(s,cell,value)=>s.getRange(cell).formulas=[[value]];
const value=(s,cell,v)=>s.getRange(cell).values=[[v]];
function base(s,lastCol,lastRow,title,subtitle,header=6) {
  s.showGridLines=false;
  const body=s.getRange(`A1:${lastCol}${lastRow}`);
  body.format.font={name:'Arial',size:10,color:'#202A33'};
  body.format.rowHeight=21;
  body.format.columnWidth=15;
  body.format.verticalAlignment='center';
  value(s,'A2',title); s.getRange('A2').format.font={size:15,bold:true,color:'#111111'};
  value(s,'A3',subtitle); s.getRange('A3').format.font={size:10,color:'#586675'};
  if(header){s.freezePanes.freezeRows(header);s.freezePanes.freezeColumns(2);}
}
function headers(s,row,labels) {
  const r=s.getRange(`A${row}:${column(labels.length)}${row}`);r.values=[labels];
  r.format={fill:navy,font:{color:'#FFFFFF',bold:true},wrapText:true,horizontalAlignment:'center',rowHeight:43};
}
function table(s,row,labels,rows,name) {
  headers(s,row,labels);
  if(rows.length)s.getRange(`A${row+1}:${column(labels.length)}${row+rows.length}`).values=rows;
  const t=s.tables.add(`A${row}:${column(labels.length)}${row+rows.length}`,true,name);t.style='TableStyleLight1';
}
// Raw observations and transparent arithmetic retain every original filing.
const h=sheets.Filings, hstart=7, hend=data.history.length+6;
base(h,'X',hend,'SEC filing language observations','Original filings from January 2021 to September 2026 | active Loughran–McDonald categories');
const hlabels=['Ticker','CIK','Form','Report period end','Filing date','Total words','Negative words','Uncertainty words','Negative words / total words (%)','Uncertainty words / total words (%)','Prior report period','Prior filing date','Prior total words','Word count YoY','Prior negative share','Prior uncertainty share','Negative YoY pp','Uncertainty YoY pp','Anniversary gap days','SEC filing source','Prior SEC source','Company','Current ARK funds','Accession'];
table(h,6,hlabels,data.history.map(r=>[r.ticker,r.cik,r.form,date(r.report_date),date(r.filing_date),r.n_words,r.Negative_tokens,r.Uncertainty_tokens,null,null,null,null,null,null,null,null,null,null,r.match_gap_days,r.doc_url,null,r.company,r.funds,r.accession]),'FilingObservations');
for(const r of data.history){const i=r.history_index+7;formula(h,`I${i}`,`=G${i}/F${i}`);formula(h,`J${i}`,`=H${i}/F${i}`);
  if(r.matched_history_index!==null){const p=r.matched_history_index+7;
    for(const [dest,src] of [['K','D'],['L','E'],['M','F'],['O','I'],['P','J'],['U','T']])formula(h,`${dest}${i}`,`=${src}${p}`);
    formula(h,`N${i}`,`=F${i}/M${i}-1`);formula(h,`Q${i}`,`=(I${i}-O${i})*100`);formula(h,`R${i}`,`=(J${i}-P${i})*100`);
  }
}
for(const c of ['D','E','K','L'])h.getRange(`${c}7:${c}${hend}`).setNumberFormat('yyyy-mm-dd');
for(const c of ['I','J','N','O','P'])h.getRange(`${c}7:${c}${hend}`).setNumberFormat(pct);
for(const c of ['Q','R'])h.getRange(`${c}7:${c}${hend}`).setNumberFormat(pp);
for(const c of ['F','G','H','M'])h.getRange(`${c}7:${c}${hend}`).setNumberFormat('#,##0');
h.getRange(`B7:B${hend}`).setNumberFormat('0000000000');
for(const [c,w] of [['A',11],['B',15],['C',10],['T',62],['U',62],['V',36],['W',28],['X',29]])h.getRange(`${c}1:${c}${hend}`).format.columnWidth=w;
h.getRange(`I1:J${hend}`).format.columnWidth=29;

const annual=sheets['Annual Filings'],annualRows=data.history.filter(r=>r.form==='10-K'),annualEnd=annualRows.length+6;
base(annual,'J',annualEnd,'Annual filing word shares','10-K reports only | category words divided by total words in each report');
table(annual,6,['Ticker','Company','Report period end','Filed','Total words','Negative words','Uncertainty words','Negative words / total words (%)','Uncertainty words / total words (%)','SEC source'],annualRows.map(r=>[r.ticker,r.company,null,null,null,null,null,null,null,null]),'AnnualFilingWordShares');
annualRows.forEach((r,j)=>{const i=j+7,p=r.history_index+7;for(const [to,from] of [['C','D'],['D','E'],['E','F'],['F','G'],['G','H'],['H','I'],['I','J'],['J','T']])formula(annual,`${to}${i}`,`=Filings!${from}${p}`);});
annual.getRange(`C7:D${annualEnd}`).setNumberFormat('yyyy-mm-dd');annual.getRange(`E7:G${annualEnd}`).setNumberFormat('#,##0');annual.getRange(`H7:I${annualEnd}`).setNumberFormat(pct);
for(const [c,w] of [['A',12],['B',50],['C',20],['D',20],['H',29],['I',29],['J',70]])annual.getRange(`${c}1:${c}${annualEnd}`).format.columnWidth=w;

const s=sheets.Summary,summaryEnd=currentCompanies.length+6;
base(s,'L',summaryEnd+7,'Current ARK companies: financial-report word shares','Held on September 9, 2026 | Percentages count category words divided by all document words',0);s.tabColor=navy;
value(s,'A4','As of');value(s,'B4',date(data.metadata.as_of_date));s.getRange('B4').setNumberFormat('yyyy-mm-dd');
table(s,6,['Ticker','Company','Current ETF holdings','Latest 10-Q period end','Negative words / total words (%)','Uncertainty words / total words (%)','2025 Q2 negative words / total words (%)','2026 Q2 negative words / total words (%)','2025 Q2 uncertainty words / total words (%)','2026 Q2 uncertainty words / total words (%)','First observed ARK holding date','Filing coverage'],currentCompanies.map(r=>[r.ticker,r.company??r.sec_name,r.funds,null,null,null,null,null,null,null,null,null]),'CurrentCompanySummary');
currentCompanies.forEach((r,j)=>{
  const i=j+7,reports=data.history.filter(q=>q.form==='10-Q'&&r.cik&&cikKey(q.cik)===cikKey(r.cik)).sort((a,b)=>b.report_date.localeCompare(a.report_date)),q=reports[0];
  if(q)for(const [to,from] of [['D','D'],['E','I'],['F','J']])formula(s,`${to}${i}`,`=Filings!${from}${q.history_index+7}`);
  for(const [to,sheet,quarter] of [['G','Negative History','2025Q2'],['H','Negative History','2026Q2'],['I','Uncertainty History','2025Q2'],['J','Uncertainty History','2026Q2']]){
    const source=`'${sheet}'!${column(quarters.indexOf(quarter)+4)}${i}`;formula(s,`${to}${i}`,`=IF(ISNUMBER(${source}),${source},"")`);
  }
  value(s,`L${i}`,q?`${reports.length} quarterly filings available`:filingCoverage(r));
});
s.getRange(`D7:D${summaryEnd}`).setNumberFormat('yyyy-mm-dd');s.getRange(`E7:J${summaryEnd}`).setNumberFormat(pct);s.getRange(`K7:K${summaryEnd}`).setNumberFormat('yyyy-mm-dd');
for(const [c,w] of [['A',12],['B',50],['C',29],['D',21],['E',29],['F',29],['G',29],['H',29],['I',29],['J',29],['K',26],['L',62]])s.getRange(`${c}1:${c}${summaryEnd+7}`).format.columnWidth=w;
value(s,`A${summaryEnd+2}`,'The 2025 Q2 and 2026 Q2 columns show the actual report-period word shares for those named quarters. Blank means no eligible report.');
value(s,`A${summaryEnd+3}`,'Historical percentages cover all available 10-Q reports. Annual reports remain separate; a missing Q4 is not filled with a 10-K.');
value(s,`A${summaryEnd+4}`,'Language shares describe disclosures, not the probability of a loss, default or another business event.');
value(s,`A${summaryEnd+5}`,'Loughran–McDonald 1993–2025 dictionary, March 2026: 2,345 active negative words and 297 active uncertainty words.');
value(s,`A${summaryEnd+6}`,'Source: https://sraf.nd.edu/loughranmcdonald-master-dictionary/ | SEC original filings linked with every observation.');

const display={quarters,companies:[]};
for(const [sheetName,category,countCol] of [['Negative History','Negative','G'],['Uncertainty History','Uncertainty','H']]){
  const sh=sheets[sheetName],last=column(quarters.length+3);
  base(sh,last,summaryEnd+6,`${category} words / total words (%)`,'Current companies | 10-Q only | report-period quarters, with period ends within 7 days aligned to the nearest quarter end');
  table(sh,6,['Ticker','Company','10-Q coverage',...quarters],currentCompanies.map(r=>[r.ticker,r.company??r.sec_name,null,...quarters.map(()=>null)]),`${category}QuarterlyHistory`);
  sh.getRange(`A1:A${summaryEnd+6}`).format.columnWidth=12;sh.getRange(`B1:B${summaryEnd+6}`).format.columnWidth=50;sh.getRange(`C1:C${summaryEnd+6}`).format.columnWidth=35;
  sh.getRange(`D7:${last}${summaryEnd}`).setNumberFormat(pct);
  currentCompanies.forEach((r,j)=>{
    const histories=data.history.filter(x=>x.form==='10-Q'&&r.cik&&cikKey(x.cik)===cikKey(r.cik)),i=j+7;
    value(sh,`C${i}`,histories.length?`${histories.length} quarterly filings`:filingCoverage(r));
    let record=display.companies[j];if(!record){record={ticker:r.ticker,company:r.company??r.sec_name,cik:r.cik,negative_pct:{},uncertainty_pct:{},filings_by_quarter:{}};display.companies.push(record);}
    quarters.forEach((quarter,k)=>{
      const reports=histories.filter(x=>reportQuarter(x.report_date)===quarter),key=category.toLowerCase()+'_pct';record[key][quarter]=null;
      if(reports.length){
        const numerator=reports.map(x=>`Filings!${countCol}${x.history_index+7}`).join(','),denominator=reports.map(x=>`Filings!F${x.history_index+7}`).join(',');
        formula(sh,`${column(k+4)}${i}`,`=SUM(${numerator})/SUM(${denominator})`);
        record[key][quarter]=100*reports.reduce((sum,x)=>sum+x[category+'_tokens'],0)/reports.reduce((sum,x)=>sum+x.n_words,0);
        record.filings_by_quarter[quarter]=reports.map(x=>({report_date:x.report_date,form:x.form,doc_url:x.doc_url,accession:x.accession}));
      }
    });
  });
  value(sh,`A${summaryEnd+2}`,'Blank = no eligible 10-Q for that report-period quarter. It does not mean zero negative or uncertainty words.');
  value(sh,`A${summaryEnd+3}`,'Fiscal period ends up to seven days from a calendar quarter end are aligned to that quarter; actual dates remain with the filings.');
  value(sh,`A${summaryEnd+4}`,'If a company has several reports in one displayed quarter, category word counts and total words are summed before division.');
  value(sh,`A${summaryEnd+5}`,'2026 Q3 is incomplete. Earlier periods may precede the first observed ARK holding date.');
}
await fs.writeFile(`${out}/quarterly_display.json`,JSON.stringify(display,null,2));
execFileSync('/Users/mfr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',['scripts/17_monitor_answers.py'],{stdio:'pipe'});
const answers=JSON.parse(await fs.readFile(`${out}/research_answers.json`,'utf8'));
const findings=sheets['Research findings'];
base(findings,'F',67,'Current ARK holdings: research findings','Holdings on September 9, 2026 | Each percentage is category-word occurrences divided by all words in a filing',0);findings.tabColor=navy;
for(const [c,w] of [['A',12],['B',23],['C',58],['D',27],['E',27],['F',75]])findings.getRange(`${c}1:${c}67`).format.columnWidth=w;
const section=(row,text)=>{value(findings,`A${row}`,text);findings.getRange(`A${row}`).format.font={size:12,bold:true};};
const overviewChecks=[];
function ranking(row,list,category,name){
  table(findings,row,['Rank','Ticker','Company',`${answers.base_quarter} words / total words (%)`,`${answers.end_quarter} words / total words (%)`],list.map((r,i)=>[i+1,r.ticker,r.company,null,null]),name);
  list.forEach((r,j)=>{
    const companyRow=currentCompanies.findIndex(c=>tickerKey(c.ticker)===tickerKey(r.ticker))+7;assert.ok(companyRow>=7,`${r.ticker} current-company source`);
    for(const [dest,quarter,key] of [['D',answers.base_quarter,'base_pct'],['E',answers.end_quarter,'end_pct']]){
      const cell=`${dest}${row+j+1}`;formula(findings,cell,`='${category} History'!${column(quarters.indexOf(quarter)+4)}${companyRow}`);overviewChecks.push([cell,r[key]/100]);
    }
  });
  findings.getRange(`D${row+1}:E${row+list.length}`).setNumberFormat(pct);
}
section(5,'1. Negative language declines');
table(findings,6,['Companies','Lower negative share','Higher negative share',`${answers.base_quarter} company average`,`${answers.end_quarter} company average`],[[answers.negative.companies,answers.negative.decreased,answers.negative.increased,answers.negative.base_company_average_pct/100,answers.negative.end_company_average_pct/100]],'NegativeLanguageAnswer');
findings.getRange('D7:E7').setNumberFormat('0.000%');
ranking(9,answers.negative_declines,'Negative','LargestNegativeWordDeclines');
value(findings,'A16','Company averages give equal weight to each company in the same named quarter. Each ranking compares the two displayed quarters.');

section(18,'2. Uncertainty over time');
value(findings,'A19',`${answers.uncertainty.increased} of ${answers.uncertainty.companies} companies have a higher uncertainty-word share in ${answers.end_quarter}; ${answers.uncertainty.decreased} have a lower share.`);
table(findings,21,['Companies','Comparison group','Measure',answers.base_quarter,answers.end_quarter],[[answers.uncertainty.companies,'Same companies','Average uncertainty words / total words (%)',answers.uncertainty.base_company_average_pct/100,answers.uncertainty.end_company_average_pct/100],[answers.uncertainty_excluding_kdk.companies,'Excluding KDK','Average uncertainty words / total words (%)',answers.uncertainty_excluding_kdk.base_company_average_pct/100,answers.uncertainty_excluding_kdk.end_company_average_pct/100]],'UncertaintyQuarterComparison');
findings.getRange('D22:E23').setNumberFormat('0.000%');
table(findings,25,['Report quarter','Same companies','Average uncertainty words / total words (%)'],answers.long_term.quarters.map((q,i)=>[q,answers.long_term.companies,answers.long_term.company_average_pct[i]/100]),'FixedCompanyAnnualQ2Path');
findings.getRange('C26:C31').setNumberFormat('0.000%');
value(findings,'A33','The fixed-company Q2 averages show a recent increase, but the 2026 level remains below 2021. KDK changed from a SPAC to an operating company.');
section(35,'Largest increases in uncertainty words between the named quarters');
ranking(36,answers.uncertainty_increases,'Uncertainty','LargestUncertaintyWordIncreases');

section(44,'3. Highest latest uncertainty-word shares');
value(findings,'A45','Latest available 10-Q for each company; report-period dates differ. Word shares do not measure the probability of a loss or default.');
table(findings,46,['Rank','Ticker','Company','Report period end','Uncertainty words / total words (%)','SEC filing source'],answers.highest_latest_uncertainty.map((r,i)=>[i+1,r.ticker,r.company,date(r.report_date),null,r.source]),'HighestLatestUncertaintyWords');
answers.highest_latest_uncertainty.forEach((r,j)=>{
  const filing=data.history.find(f=>f.doc_url===r.source);assert.ok(filing,`${r.ticker} latest filing source`);formula(findings,`E${j+47}`,`=Filings!J${filing.history_index+7}`);overviewChecks.push([`E${j+47}`,r.uncertainty_pct/100]);
});
findings.getRange('D47:D51').setNumberFormat('yyyy-mm-dd');findings.getRange('E47:E51').setNumberFormat(pct);

section(54,'4. Largest declines in uncertainty words');
value(findings,'A55','The ranking uses the absolute difference between the two reported percentages, with the largest decrease first.');
ranking(56,answers.uncertainty_declines,'Uncertainty','LargestUncertaintyWordDeclines');
value(findings,'A63','Coinbase shortened its risk-factor disclosures; Canton changed business composition. Lower word shares do not establish lower operating risk.');
value(findings,'A64','The company universe is selected from holdings on September 9, 2026. Historical observations may precede ARK ownership.');
value(findings,'A65','Matched-quarter comparisons require an available 10-Q in both quarters. Missing observations remain blank in the complete histories.');
value(findings,'A66','Fiscal period ends within seven days of a calendar quarter end are aligned to that quarter; original dates and sources accompany each filing.');
value(findings,'A67','The rankings are descriptive. ETFs have different holdings weights; equal-company averages are not portfolio-weighted statistics.');

const fundQuarter=new Map(holdings.fund_quarter_coverage.map(r=>[`${r.fund}|${r.quarter}`,r]));
const securityRows=[...new Map(holdings.latest_holdings.filter(r=>companyFor(r)).map(r=>[r.security_key,r])).values()];
const currentPositions=new Map(holdings.latest_holdings.map(r=>[`${r.security_key}|${r.fund}`,r]));
const entryMap=new Map(holdings.entry_dates.map(r=>[`${r.security_key}|${r.fund}`,r]));
const securities=new Set(securityRows.map(r=>r.security_key));
const weights=holdings.quarterly_weights.filter(r=>securities.has(r.security_key)&&quarters.includes(r.quarter));
const wi=sheets['Weight Inputs'],weightEnd=weights.length+6;
base(wi,'Q',weightEnd+5,'ETF quarterly-average weight inputs','Each weight is a percentage of that ETF net assets. Observed dates without the security contribute zero.');
table(wi,6,['Security identifier','Ticker','Company','ETF','Quarter','Sum of observed daily weights, % units','Observed ETF dates','Dates held','Quarterly average ETF weight (%)','Missing ETF sessions','Current quarter incomplete','Archive start quarter incomplete','First observed date in quarter','Last observed date in quarter','Snapshot coverage','Identifier history flags','Dates with unresolved security identity'],weights.map(r=>{
  const c=companyFor(r),coverage=fundQuarter.get(`${r.fund}|${r.quarter}`),entry=entryMap.get(`${r.security_key}|${r.fund}`);
  return [r.security_key,r.normalized_ticker,c?.company??c?.sec_name,r.fund,r.quarter,r.sum_daily_weight_pct,r.observed_snapshot_days,r.held_snapshot_days,null,r.missing_snapshot_days,r.partial_current_quarter?'Yes':'No',r.partial_archive_start_quarter?'Yes':'No',date(coverage?.first_snapshot_date),date(coverage?.last_snapshot_date),coverage?.coverage_fraction??null,r.unresolved_identity?'Unknown exposure: security identity unresolved':entry?.identity_conflict_requires_review?'Different security identifiers not combined':entry?.has_provisional_ticker_matches?'Some missing identifiers matched provisionally by ticker':'Source identifier matched',r.unresolved_identity_days??0];
}),'ETFQuarterlyWeightInputs');
const weightRow=new Map();
weights.forEach((r,j)=>{const i=j+7;formula(wi,`I${i}`,`=IF(Q${i}>0,"",IF(G${i}>0,F${i}/G${i}/100,""))`);weightRow.set(`${r.security_key}|${r.fund}|${r.quarter}`,i);});
wi.getRange(`F7:F${weightEnd}`).setNumberFormat('0.000000');wi.getRange(`I7:I${weightEnd}`).setNumberFormat(pct);wi.getRange(`M7:N${weightEnd}`).setNumberFormat('yyyy-mm-dd');wi.getRange(`O7:O${weightEnd}`).setNumberFormat(pct);
for(const [c,w] of [['A',27],['B',12],['C',50],['D',12],['E',14],['F',29],['I',28],['P',63]])wi.getRange(`${c}1:${c}${weightEnd+5}`).format.columnWidth=w;
value(wi,`A${weightEnd+2}`,'Quarterly average = sum of daily ETF weights ÷ observed ETF dates. No position on an observed date contributes zero.');
value(wi,`A${weightEnd+3}`,'Missing dates are not filled. No ETF coverage or unresolved security identity leaves a quarter blank; current-quarter averages are partial.');
value(wi,`A${weightEnd+4}`,'Source: https://github.com/robynge/ark-routine/tree/main/data/holdings');

const weightMatrix=sheets['ETF Weights'],entrySheet=sheets['Entry Dates'];
const pairs=securityRows.flatMap(r=>holdings.metadata.funds.map(fund=>({security:r,fund,entry:entryMap.get(`${r.security_key}|${fund}`)})));
const pairEnd=pairs.length+6,weightLast=column(quarters.length+7);
base(weightMatrix,weightLast,pairEnd+5,'ETF holdings: quarterly-average weights (%)','Current securities in all six ETFs | historical daily weights averaged over each ETF observed dates, including zero when absent');
table(weightMatrix,6,['Ticker','Company','ETF','Current ETF weight (%)','First observed holding','Latest observed holding spell','Entry/history coverage',...quarters],pairs.map(({security:r,fund,entry:e})=>{
  const c=companyFor(r),position=currentPositions.get(`${r.security_key}|${fund}`);
  return [r.normalized_ticker,c?.company??r.company,fund,(position?.current_weight_pct??0)/100,date(e?.first_observed_holding_date),date(e?.latest_observed_spell_entry_date),!e?.first_observed_holding_date?'No holding observed in ETF archive':e.identity_conflict_requires_review?'Identifier conflict; earlier history may differ':e.first_entry_left_censored?'Held at archive start; earlier entry unknown':e.has_provisional_ticker_matches?'Some missing identifiers matched provisionally':'First observed date; actual trade date unknown',...quarters.map(()=>null)];
}),'ETFWeightHistory');
pairs.forEach(({security:r,fund},j)=>quarters.forEach((quarter,k)=>{const source=weightRow.get(`${r.security_key}|${fund}|${quarter}`);if(source)formula(weightMatrix,`${column(k+8)}${j+7}`,`='Weight Inputs'!I${source}`);}));
weightMatrix.getRange(`D7:D${pairEnd}`).setNumberFormat(pct);weightMatrix.getRange(`E7:F${pairEnd}`).setNumberFormat('yyyy-mm-dd');weightMatrix.getRange(`H7:${weightLast}${pairEnd}`).setNumberFormat(pct);
for(const [c,w] of [['A',12],['B',49],['C',12],['D',23],['E',24],['F',28],['G',58]])weightMatrix.getRange(`${c}1:${c}${pairEnd+5}`).format.columnWidth=w;
value(weightMatrix,`A${pairEnd+2}`,'Zero means absent on every observed ETF date. Blank means no ETF coverage or unresolved security-identifier continuity.');
value(weightMatrix,`A${pairEnd+3}`,'Current securities appear for all six funds, including funds that no longer hold them. 2026 Q3 is incomplete.');
value(weightMatrix,`A${pairEnd+4}`,'Source: https://github.com/robynge/ark-routine/tree/main/data/holdings');

base(entrySheet,'M',pairEnd+5,'First observed ETF holdings','Observed archive dates are not exact purchase dates. Identifier changes and incomplete histories limit entry-date interpretation.');
table(entrySheet,6,['Ticker','Company','ETF','Currently held','First observed holding','Held at archive start','Latest observed spell began','Latest spell left-censored','Unobserved sessions in latest spell','Provisional ticker matches','Identifier conflict','Source security identifier','Fund archive begins'],pairs.map(({security:r,fund,entry:e})=>[r.normalized_ticker,companyFor(r)?.company??r.company,fund,currentPositions.has(`${r.security_key}|${fund}`)?'Yes':'No',date(e?.first_observed_holding_date),e?.first_entry_left_censored===null?null:e?.first_entry_left_censored?'Yes':'No',date(e?.latest_observed_spell_entry_date),e?.latest_spell_left_censored===null?null:e?.latest_spell_left_censored?'Yes':'No',e?.unobserved_sessions_in_latest_spell??null,e?.has_provisional_ticker_matches?'Yes':'No',e?.identity_conflict_requires_review?'Yes':'No',r.security_key,date(e?.fund_history_first_date)]),'ObservedETFEntries');
for(const c of ['E','G','M'])entrySheet.getRange(`${c}7:${c}${pairEnd}`).setNumberFormat('yyyy-mm-dd');
for(const [c,w] of [['A',12],['B',49],['C',12],['E',24],['F',24],['G',27],['H',27],['I',29],['J',24],['K',24],['L',27],['M',24]])entrySheet.getRange(`${c}1:${c}${pairEnd+5}`).format.columnWidth=w;
currentCompanies.forEach((r,j)=>{
  const dates=pairs.filter(p=>companyFor(p.security)===r).map(p=>p.entry?.first_observed_holding_date).filter(Boolean).sort();
  if(dates.length)value(s,`K${j+7}`,date(dates[0]));
});
value(entrySheet,`A${pairEnd+2}`,'Left-censored means a holding was already present when the archive starts, so the actual entry may be earlier.');
value(entrySheet,`A${pairEnd+3}`,'A holding spell is continuous across observed snapshots only; missing sessions do not prove continuous ownership.');
value(entrySheet,`A${pairEnd+4}`,'Different nonempty security identifiers are not automatically combined merely because their ticker is unchanged.');

const cov=sheets.Coverage, coverage=[];
for(const [j,r] of currentCompanies.entries()){
  const records=data.history.filter(q=>r.cik&&cikKey(q.cik)===cikKey(r.cik)),quartersMissing=['2025Q2','2026Q2'].filter(q=>display.companies[j].negative_pct[q]===null);
  if(quartersMissing.length)coverage.push([r.ticker,r.company??r.sec_name,r.funds,records.filter(q=>q.form==='10-Q').length,records.filter(q=>q.form==='10-K').length,quartersMissing.join(', '),records.length?'No eligible 10-Q for the indicated report-period quarter':filingCoverage(r)]);
}
base(cov,'G',coverage.length+6,'Filing coverage for the named quarters','Missing 2025 Q2 or 2026 Q2 observations remain blank; other available quarters are retained.');
table(cov,6,['Ticker','Company','Current ETF holdings','10-Q filings','10-K filings','Unavailable quarters','Coverage reason'],coverage,'CoverageExceptions');
for(const [c,w] of [['A',12],['B',58],['C',30],['D',22],['E',18],['F',18],['G',70]])cov.getRange(`${c}1:${c}${coverage.length+6}`).format.columnWidth=w;

// Source counts span the actual Part II Item 1A heading up to, but excluding, Item 2.
const sectionInputs=[['ABSI','2024-09-30',137,136],['ABSI','2025-09-30',39750,174],['SOFI','2024-09-30',48358,602],['SOFI','2025-09-30',1703,591]];
const sec=sheets.Sections;
base(sec,'I',22,'Risk-factor disclosure sensitivity','Uncertainty outside Part II Item 1A | 2025 Q3 and prior-year comparisons');
table(sec,6,['Ticker','Period end','Total words','Item 1A words','Other words','Other uncertainty words','Other uncertainty share','Whole-document uncertainty share','SEC source'],sectionInputs.map(([ticker,period,risk,unc])=>{
  const r=data.history.find(x=>x.ticker===ticker&&x.form==='10-Q'&&x.report_date===period);
  assert.ok(r,`${ticker} ${period} source filing missing`);
  return [ticker,date(period),r.n_words,risk,null,unc,null,null,r.doc_url];
}),'SectionSensitivity');
sectionInputs.forEach(([ticker,period],j)=>{
  const i=j+7,r=data.history.find(x=>x.ticker===ticker&&x.form==='10-Q'&&x.report_date===period);
  formula(sec,`E${i}`,`=C${i}-D${i}`);formula(sec,`G${i}`,`=F${i}/E${i}`);formula(sec,`H${i}`,`=Filings!J${r.history_index+7}`);
});
sec.getRange('B7:B10').setNumberFormat('yyyy-mm-dd');sec.getRange('C7:F10').setNumberFormat('#,##0');sec.getRange('G7:H10').setNumberFormat(pct);
value(sec,'A13','The risk-factor section runs from the actual Part II Item 1A heading to the following Item 2 heading.');
value(sec,'A14','The heading is included. Contents entries and cross-references outside that section are excluded from the section count.');
value(sec,'A15','Other uncertainty share equals uncertainty occurrences outside Item 1A divided by words outside Item 1A.');
value(sec,'A16','Counts use the same tokenization and 297 active uncertainty words as the whole-document measures.');
value(sec,'A18','ABSI: the risk-factor section expanded between the 2024 Q3 and 2025 Q3 reports.');
value(sec,'A19','SOFI: the risk-factor section shortened between the 2024 Q3 and 2025 Q3 reports.');
value(sec,'A21','Removing one section does not hold the remaining document composition constant or identify a change in business risk.');
for(const [c,w] of [['A',12],['B',17],['C',17],['D',17],['E',17],['F',23],['G',23],['H',26],['I',70]])sec.getRange(`${c}1:${c}22`).format.columnWidth=w;

// Verify direct report-quarter observations and their links.
wb.recalculate();
const numeric=(sheet,cell)=>sheet.getRange(cell).values[0][0];
for(const [cell,expected] of overviewChecks)assert.ok(Math.abs(numeric(findings,cell)-expected)<1e-12,`Research findings ${cell}`);
const paired=display.companies.filter(c=>['negative_pct','uncertainty_pct'].every(key=>[answers.base_quarter,answers.end_quarter].every(q=>Number.isFinite(c[key][q]))));
const average=(records,key,q)=>records.reduce((sum,c)=>sum+c[key][q],0)/records.length;
for(const category of ['negative','uncertainty']){
  const a=answers[category],key=category+'_pct';assert.equal(paired.length,a.companies);
  assert.equal(paired.filter(c=>c[key][answers.end_quarter]>c[key][answers.base_quarter]).length,a.increased);
  assert.equal(paired.filter(c=>c[key][answers.end_quarter]<c[key][answers.base_quarter]).length,a.decreased);
  for(const [q,k] of [[answers.base_quarter,'base_company_average_pct'],[answers.end_quarter,'end_company_average_pct']])assert.ok(Math.abs(average(paired,key,q)-a[k])<1e-12);
}
const balanced=display.companies.filter(c=>answers.long_term.quarters.every(q=>Number.isFinite(c.uncertainty_pct[q])));
assert.equal(balanced.length,answers.long_term.companies);
answers.long_term.quarters.forEach((q,i)=>assert.ok(Math.abs(average(balanced,'uncertainty_pct',q)-answers.long_term.company_average_pct[i])<1e-12));
const withoutKdk=paired.filter(c=>c.ticker!=='KDK');assert.equal(withoutKdk.length,answers.uncertainty_excluding_kdk.companies);
for(const [q,k] of [[answers.base_quarter,'base_company_average_pct'],[answers.end_quarter,'end_company_average_pct']])assert.ok(Math.abs(average(withoutKdk,'uncertainty_pct',q)-answers.uncertainty_excluding_kdk[k])<1e-12);

for(const [i,expected] of [[7,136/10692],[8,174/11536],[9,602/46255],[10,591/43989]])assert.ok(Math.abs(numeric(sec,`G${i}`)-expected)<1e-12);
currentCompanies.forEach((r,j)=>{
  for(const [col,key,q] of [['G','negative_pct','2025Q2'],['H','negative_pct','2026Q2'],['I','uncertainty_pct','2025Q2'],['J','uncertainty_pct','2026Q2']]){
    const expected=display.companies[j][key][q],actual=numeric(s,`${col}${j+7}`);
    if(expected===null)assert.equal(actual,'');else assert.ok(Math.abs(actual*100-expected)<1e-10);
  }
});
let observedQuarterCells=0;
display.companies.forEach((r,j)=>quarters.forEach((q,k)=>{
  for(const [name,key] of [['Negative History','negative_pct'],['Uncertainty History','uncertainty_pct']])if(r[key][q]!==null){assert.ok(Math.abs(numeric(sheets[name],`${column(k+4)}${j+7}`)*100-r[key][q])<1e-10);observedQuarterCells++;}
}));
let unknownWeightCells=0;
weights.forEach((r,j)=>{const actual=numeric(wi,`I${j+7}`);if(r.average_weight_pct===null){assert.equal(actual,'');unknownWeightCells++;}else assert.ok(Math.abs(actual*100-r.average_weight_pct)<1e-10,`${r.security_key} ${r.fund} ${r.quarter}`);});
assert.equal(pairs.length,securityRows.length*6);
assert.equal(reportQuarter('2023-07-01'),'2023Q2');assert.equal(reportQuarter('2023-09-30'),'2023Q3');
await fs.mkdir(`${out}/workbook_preview`,{recursive:true});
for(const [sheetName,range] of [['Research findings','A1:E16'],['Research findings','A18:E41'],['Research findings','A44:E67'],['Summary','A1:F16'],['Summary','G6:L16'],['Negative History','A1:L16'],['Negative History','R6:Z16'],['Uncertainty History','A1:L16'],['ETF Weights','A1:J16'],['ETF Weights','U6:AD16'],['Entry Dates','A1:M16'],['Weight Inputs','D1:Q16'],['Annual Filings','A1:J16'],['Filings','A1:J16'],['Coverage','A1:G16'],['Sections','A1:I22']]){
  const png=await wb.render({sheetName,range,scale:1.4,format:'png'});await fs.writeFile(`${out}/workbook_preview/${sheetName}_${range.replace(':','-')}.png`,new Uint8Array(await png.arrayBuffer()));
}
const inspection=await wb.inspect({kind:'table',range:'Summary!A6:F12',include:'values,formulas',tableMaxRows:7,tableMaxCols:6,maxChars:4000});
await fs.writeFile(`${out}/workbook_inspection.json`,JSON.stringify(inspection,null,2));
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Formula error scan'});
await fs.writeFile(`${out}/workbook_error_scan.json`,JSON.stringify(errors));
const exported=await SpreadsheetFile.exportXlsx(wb);await exported.save(`${out}/ARK_Holdings_Company_Monitoring_Data_${data.metadata.as_of_date}.xlsx`);
console.log(JSON.stringify({currentCompanies:currentCompanies.length,currentSecurities:securityRows.length,securityFundRows:pairs.length,quarterlyWeightRows:weights.length,unknownWeightCells,observedQuarterCells,filings:data.history.length,overviewLinkedValues:overviewChecks.length,pairedCompanies:paired.length,balancedCompanies:balanced.length,checks:'Research answers, named-quarter word shares, full history shares, ETF weight averages and missing identity passed'}));

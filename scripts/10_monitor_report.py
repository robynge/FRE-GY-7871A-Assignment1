"""Create the company-monitoring DOCX and chart from the monitoring observations."""
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = Path('outputs/company_monitor')
DATA = json.loads((OUT / 'data.json').read_text())
Q = {r['ticker']: r for r in DATA['quarterly']}
H = DATA['history']
SUM = DATA['summary']
INK = '0A0A23'
ACCENT = '8264FF'
TABLE_TINT = 'F0ECFF'
assert DATA['metadata']['as_of_date'] == '2026-09-09', 'Reassess dated report commentary when refreshing the observation cutoff.'


def pct(x):
    return '—' if x is None else ('<0.01%' if 0 < x < 0.005 else f'{x:.2f}%')


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin, sec.bottom_margin = Inches(0.65), Inches(0.6)
sec.left_margin, sec.right_margin = Inches(0.8), Inches(0.8)
sec.header_distance, sec.footer_distance = Inches(0.25), Inches(0.25)
for name in ['Normal', 'Title', 'Heading 1', 'Heading 2', 'Caption']:
    st = doc.styles[name]
    st.font.name = 'Arial'
    st.font.color.rgb = RGBColor.from_string(INK)
    st.font.size = Pt(10.5)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.08
doc.styles['Title'].font.size = Pt(22)
doc.styles['Title'].font.bold = True
doc.styles['Heading 1'].font.size = Pt(14)
doc.styles['Heading 1'].font.bold = True
doc.styles['Heading 1'].paragraph_format.space_before = Pt(12)
doc.styles['Heading 2'].font.size = Pt(11)
doc.styles['Heading 2'].font.bold = True
doc.styles['Caption'].font.size = Pt(8.5)
doc.styles['Caption'].font.bold = False
doc.styles['Caption'].font.color.rgb = RGBColor.from_string('676777')
for style in doc.styles:
    for border in style.element.findall('.//' + qn('w:pBdr')):
        border.getparent().remove(border)
doc.core_properties.title = 'Current ARK Holdings: Filing Language'
doc.core_properties.subject = 'Company monitoring using SEC filing sentiment and uncertainty'
doc.core_properties.author = 'Research'
head = sec.header.paragraphs[0]
head.text = 'ARK HOLDINGS  |  COMPANY MONITORING'
head.style = doc.styles['Caption']
foot = sec.footer.paragraphs[0]
foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
foot.add_run('9 September 2026   |   ').font.size = Pt(8)
field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); foot._p.append(field)


def para(text, style=None):
    return doc.add_paragraph(text, style)


def heading(text, new_page=False):
    p = doc.add_heading(text, level=1)
    p.paragraph_format.page_break_before = new_page


def table(labels, rows, widths, font_size=9):
    t = doc.add_table(rows=1, cols=len(labels))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for col, width in zip(t.columns, widths):
        col.width = Inches(width)
    for cell, txt in zip(t.rows[0].cells, labels):
        cell.text = txt
    repeat = OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        for cell, txt in zip(t.add_row().cells, row):
            cell.text = str(txt)
    for i, row in enumerate(t.rows):
        pr = row._tr.get_or_add_trPr(); pr.append(OxmlElement('w:cantSplit'))
        for j, cell in enumerate(row.cells):
            cell.width = Inches(widths[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cp = cell._tc.get_or_add_tcPr()
            shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), TABLE_TINT if i == 0 else ('FAF9FE' if i % 2 else 'FFFFFF')); cp.append(shade)
            borders = OxmlElement('w:tcBorders')
            for edge in ['top', 'left', 'bottom', 'right']:
                el = OxmlElement('w:' + edge); el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), '4'); el.set(qn('w:color'), 'DDD6F0'); borders.append(el)
            cp.append(borders)
            margins = OxmlElement('w:tcMar')
            for side, v in [('top', 75), ('bottom', 75), ('left', 80), ('right', 80)]:
                el = OxmlElement('w:' + side); el.set(qn('w:w'), str(v)); el.set(qn('w:type'), 'dxa'); margins.append(el)
            cp.append(margins)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else (WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.RIGHT)
                for r in p.runs:
                    r.font.size = Pt(font_size)
                    r.font.bold = i == 0
                    r.font.color.rgb = RGBColor.from_string(INK)
    return t


def link(p, text, url):
    rel = p.part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), rel)
    r = OxmlElement('w:r'); pr = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'), '6542CE'); pr.append(color)
    size = OxmlElement('w:sz'); size.set(qn('w:val'), '17'); pr.append(size)
    r.append(pr); txt = OxmlElement('w:t'); txt.text = text; r.append(txt); h.append(r); p._p.append(h)


# A single display dataset supplies the same quarterly values to Excel and Word.
DISPLAY = json.loads((OUT / 'quarterly_display.json').read_text())
HD = json.loads(Path('outputs/current_holdings/data.json').read_text())
FUNDS = ['ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF', 'ARKX']
MATRIX = {r['ticker']: r for r in DISPLAY['companies'] if r.get('ticker')}
WEIGHTS = {(r['security_key'], r['fund'], r['quarter']): r for r in HD['quarterly_weights']}
ENTRIES = {(r['security_key'], r['fund']): r for r in HD['entry_dates']}
KEYS = {}
for r in HD['latest_holdings']:
    KEYS.setdefault(r['normalized_ticker'], set()).add(r['security_key'])


def company_name(r):
    names = {'TXG':'10x Genomics','COIN':'Coinbase','TEM':'Tempus AI','SOFI':'SoFi','TSLA':'Tesla',
             'KDK':'Kodiak AI','ABSI':'Absci','CDNA':'CareDx','BMNR':'BitMine','NTRA':'Natera',
             'AVGO':'Broadcom','GENB':'Generate Biomedicines','PACB':'Pacific Biosciences','NRIX':'Nurix','VCYT':'Veracyte','CRCL':'Circle','CNTN':'Canton Strategic Holdings'}
    return names.get(r['ticker'], r.get('company', r['ticker']))


A = json.loads((OUT / 'research_answers.json').read_text())
SHOW_QUARTERS = ['2025Q2', '2025Q3', '2025Q4', '2026Q1', '2026Q2']
NEG_NAMES = [r['ticker'] for r in A['negative_declines'][:3]]
RISE_NAMES = [r['ticker'] for r in A['uncertainty_increases'][:3]]
FALL_NAMES = [r['ticker'] for r in A['uncertainty_declines'][:3]]


def language_table(tickers, field):
    t = table(['Company'] + SHOW_QUARTERS,
              [[company_name(Q[ticker]) + ' (' + ticker + ')'] + [pct(MATRIX[ticker][field].get(q)) for q in SHOW_QUARTERS] for ticker in tickers],
              [2.20] + [.90] * 5, 9)
    for row, ticker in zip(t.rows[1:], tickers):
        p = row.cells[0].paragraphs[0]; p.clear()
        link(p, company_name(Q[ticker]) + ' (' + ticker + ')', Q[ticker]['latest_doc_url'])
    para('Source: SEC quarterly reports. Company names link to the latest filing. Percentages are matching words / all analyzed words. A dash means no quarterly report; an annual report is not substituted.', 'Caption')


def allocation_rows(tickers):
    rows = []
    for ticker in tickers:
        keys = set(KEYS.get(ticker, set()))
        for alias in Q[ticker].get('tickers', ticker).split('|'):
            keys |= KEYS.get(alias, set())
        funds = [f for f in FUNDS if any(x['security_key'] in keys and x['fund'] == f for x in HD['latest_holdings'])]
        assert funds, 'Displayed company must be held at the cutoff'
        for fund in funds:
            entries = [ENTRIES[(key, fund)] for key in keys if (key, fund) in ENTRIES and ENTRIES[(key, fund)]['first_observed_holding_date']]
            entry = min(entries, key=lambda x: x['first_observed_holding_date']) if entries else None
            first = entry['first_observed_holding_date'] if entry else '—'
            if entry and entry['first_entry_left_censored']:
                first = '≤ ' + first
            if entry and (entry.get('identity_conflict_requires_review') or entry.get('has_provisional_ticker_matches')):
                first += '*'
            values = []
            for quarter in SHOW_QUARTERS:
                ws = [WEIGHTS[(key, fund, quarter)] for key in keys if (key, fund, quarter) in WEIGHTS]
                values.append('—' if not ws or any(x['average_weight_pct'] is None for x in ws) else pct(sum(x['average_weight_pct'] for x in ws)))
            rows.append([ticker, fund, first] + values)
    return rows


def allocation_table(tickers):
    rows = allocation_rows(tickers)
    table(['Ticker', 'ETF', 'First holding\nrecord'] + SHOW_QUARTERS, rows, [.58, .47, 1.20] + [.89] * 5, 8.5)
    p = para('Source: ', 'Caption')
    link(p, 'ARK historical holdings archive', 'https://github.com/robynge/ark-routine/tree/main/data')
    p.add_run('. First holding record is the earliest observed date, not a verified purchase date.')
    return rows


def latest_allocation(ticker):
    return '; '.join(f'{r[1]} {r[-1]}' for r in allocation_rows([ticker]))


def subheading(text):
    doc.add_heading(text, 2)


doc.add_heading('Current ARK Holdings: Filing Language', 0)
para('9 September 2026 | ARKK, ARKQ, ARKW, ARKG, ARKF and ARKX', 'Caption')
para('We examine companies held today to identify whose financial reports use less negative language, whether uncertain language is increasing, and which holdings merit closer reading. Quarterly reports are available for 93 companies; 84 have both 2025 Q2 and 2026 Q2 reports for comparison.')
para('A word share of 2% means two matching word occurrences per 100 words of analyzed text. The financial dictionary identifies negative words such as “loss” and uncertainty words such as “may” and “approximately.” These are measures of wording, not probabilities of business failure.', 'Caption')
heading('1. Companies with less negative language')
para('34 of 84 companies use a smaller share of negative words than a year earlier; 50 use a larger share. Coinbase, Circle and 10x Genomics have the largest declines. Coinbase falls from 3.90% to 1.59%: roughly four negative words per 100 words become roughly 1.6.')
subheading('Negative words as a share of all words')
language_table(NEG_NAMES, 'negative_pct')
para('Circle’s share falls in each available quarter shown. Coinbase and 10x Genomics fluctuate. Coinbase’s decline occurs mainly in early 2026, when its risk disclosures become much shorter: part of the decline reflects report content, rather than demonstrating improving operations.')
subheading('The same companies’ quarterly average ETF weights')
para('A 4% ETF weight means $4 of each $100 of fund assets. Each column averages that ETF’s recorded daily weights within the quarter, including zero on observed days without a holding. Different ETFs are kept separate. Many reports are published in the following quarter. The weights shown average the report-period quarter; they do not measure trading after publication.', 'Caption')
allocation_table(NEG_NAMES)
para('Coinbase’s average ARKK weight falls from 8.12% to 4.10%, while Circle’s rises from 1.51% to 4.17% and 10x Genomics’ rises from 1.47% to 2.59%. Less negative language coincides with both smaller and larger positions.')

heading('2. Uncertainty language over time', new_page=True)
u = A['uncertainty']; long = A['long_term']
para(f"Recent uncertainty language increases slightly, but it does not rise continuously over the full study period. Among the same {u['companies']} companies, {u['increased']} have a higher uncertainty-word share in 2026 Q2 and {u['decreased']} have a lower share. Their average moves from {pct(u['base_company_average_pct'])} to {pct(u['end_company_average_pct'])}.")
subheading('Longer history: the same 69 companies in every year')
table(['Measure'] + [q[:4] + ' Q2' for q in long['quarters']],
      [['Average uncertainty-word share'] + [pct(x) for x in long['company_average_pct']]], [1.60] + [.85] * 6, 9)
para('Each cell averages the word shares of the same 69 companies in that one quarter, giving each company equal weight. The smaller group has a report in every displayed year. These are company averages, separate from ETF allocation weights. Source: SEC quarterly reports.', 'Caption')
para('The long-history average is near 1.85% through 2023, falls to 1.77% in 2024, and recovers to 1.80% in 2026. It remains below 2021’s 1.84%. The evidence supports a modest recent increase, not a persistent six-year rise.')
subheading('Largest increases since 2025 Q2')
language_table(RISE_NAMES, 'uncertainty_pct')
para('Kodiak rises most, from 1.06% to 2.68%, but the comparison crosses its change from an acquisition shell to an operating business. BitMine rises from 1.77% to 2.64%, after falling in the intervening reports. Natera rises from 1.34% to 1.77%. Natera shows the most consistent rise across the displayed quarters.')
subheading('Quarterly average ETF weights of these companies')
allocation_table(RISE_NAMES)
para('Kodiak’s large change needs particular care: excluding it, the other 83 companies’ average uncertainty-word share moves only from 1.806% to 1.814%. The size of the overall increase partly reflects this company’s transition.', 'Caption')

heading('3. Highest current uncertainty-word shares', new_page=True)
para('Broadcom has the highest share in the latest available quarterly report: 3.23%, or about 3.2 uncertainty words per 100 words. Absci follows at 2.96%. This ranks the amount of uncertain language, not the chance of a loss or the size of a recent increase.')
latest = A['highest_latest_uncertainty']
t = table(['Company', 'Report period\nended', 'Uncertainty\nword share', '2026 Q2 average ETF weight'],
          [[company_name(Q[r['ticker']]) + ' (' + r['ticker'] + ')', r['report_date'], pct(r['uncertainty_pct']), latest_allocation(r['ticker'])] for r in latest],
          [2.13, 1.05, 1.10, 2.42], 9)
for row, r in zip(t.rows[1:], latest):
    p = row.cells[0].paragraphs[0]; p.clear()
    link(p, company_name(Q[r['ticker']]) + ' (' + r['ticker'] + ')', r['source'])
para('Sources: each company’s linked SEC report and ARK holdings archive. Report-period dates differ because companies have different fiscal calendars. ETF percentages use calendar-quarter daily observations.', 'Caption')
para('High is different from rising: Broadcom is highest even though its share edges down from 3.26% in 2025 Q2 to 3.23% in 2026 Q2. Generate Biomedicines can be ranked by its latest level, but lacks a 2025 Q2 report for a one-year comparison.')
heading('4. Largest uncertainty-word declines')
para('Coinbase and Circle show the largest falls: 2.64% to 1.57% and 2.14% to 1.14%, respectively. Each now uses roughly one fewer uncertainty word per 100 words than a year earlier. Canton Strategic Holdings ranks third, falling from 1.46% to 1.16%.')
language_table(FALL_NAMES, 'uncertainty_pct')
para('Coinbase and Circle’s ETF histories appear with their negative-language results. Canton’s corresponding holding history is shown below; its earlier reports concern its predecessor business, so the decline is not a clean comparison of unchanged operations.', 'Caption')
allocation_table(['CNTN'])
para('Coinbase’s 2026 quarterly reports contain much shorter risk disclosures. Its lower word share therefore partly reflects what is included in the report; it does not by itself establish an improvement in operating risk.')
para('Common words such as “may” provide little company-specific information because they appear widely. ETF weights reflect both trades and prices. Neither word shares nor weight changes alone establish why ARK traded.', 'Caption')
para('Measurement: text excludes hidden content and numerical tables. Quarter labels follow report-period ends, aligning dates within seven days of a quarter end. The accompanying Excel contains full histories, all ETF weights and entry records, with annual reports separate. 2026 Q3 is incomplete.', 'Caption')
p = para('Dictionary: ', 'Caption')
link(p, 'Loughran–McDonald, March 2026 release', 'https://sraf.nd.edu/loughranmcdonald-master-dictionary/')
p.add_run(' — 2,345 active negative words; 297 uncertainty words.')
report_path = OUT / f"ARK_Holdings_Company_Monitoring_Report_{DATA['metadata']['as_of_date']}.docx"
doc.save(report_path)
print('Saved monitoring report answering four research questions.')

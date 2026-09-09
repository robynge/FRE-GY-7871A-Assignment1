"""Reproducible sample construction and seven assignment exhibits."""
from collections import Counter
import gzip
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from .config import (ROOT, INTERIM_DIR, PRICE_DIR, OUTPUT_DIR, UNIVERSE_DIR,
                     SAMPLE_START, SAMPLE_END, AS_OF_DATE, MARKET_END)
from .events import event_variables
from .lexicons import load_all
from .parse import tokenize
from .scoring import score_corpus, common_words
from .regressions import trend_tests, outcome_tests

MEASURES = ["Negative_prop", "Uncertainty_prop", "Negative_tfidf", "Uncertainty_tfidf"]
LABELS = {"Negative_prop": "Negative words (%)", "Uncertainty_prop": "Uncertainty words (%)",
          "Negative_tfidf": "Negative tf.idf", "Uncertainty_tfidf": "Uncertainty tf.idf"}


def _prices(name):
    return pd.read_csv(PRICE_DIR / name, index_col=0, parse_dates=True).sort_index()


def _prepare_samples(sample_end=SAMPLE_END):
    manifest = pd.read_csv(INTERIM_DIR / "filings_manifest.csv", dtype={"cik": str})
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    expected = universe.loc[universe.status.eq("domestic_filer"), ["n_10k", "n_10q"]].sum().sum()
    if manifest.status.isin(["listing_failed", "download_failed", "not_attempted"]).any():
        raise RuntimeError("Acquisition is incomplete; resolve manifest errors before analysis")
    if len(manifest[manifest.form.isin(["10-K", "10-Q"])]) != expected:
        raise RuntimeError("Manifest does not cover all expected original filings")
    manifest["filing_date"] = pd.to_datetime(manifest.filing_date)
    manifest = manifest[manifest.filing_date.between(SAMPLE_START, sample_end)].copy()
    waterfall = []
    def record(label, before, data, sample="Text"):
        waterfall.append({"sample": sample, "filter": label, "removed": before-len(data),
                          "remaining": len(data), "companies": data.cik.nunique()})
    data = manifest.copy()
    record("All 10-K/Q and amendments", len(data), data)
    before = len(data)
    data = data[data.status.eq("parsed") & data.form.isin(["10-K", "10-Q"])].copy()
    record("Remove amendments and parse failures", before, data)
    all_parsed = data.copy()
    before = len(data)
    data = data[data.n_words.ge(np.where(data.form.eq("10-K"), 2000, 1000))].copy()
    record("Minimum words: 2,000 K / 1,000 Q", before, data)
    data["quarter"] = data.filing_date.dt.to_period("Q").astype(str)
    before = len(data)
    data = data.sort_values(["cik", "filing_date", "acceptance_datetime", "accession"])
    data = data.drop_duplicates(["cik", "quarter"], keep="first").reset_index(drop=True)
    record("Earliest company filing each quarter", before, data)
    prices, nominal, volume = (_prices(f) for f in ["prices.csv", "nominal_close.csv", "volume.csv"])
    # Exclude an unfinished current-day quote even if the vendor supplied one.
    prices, nominal, volume = [d.loc[d.index < MARKET_END] for d in (prices, nominal, volume)]
    shares = pd.read_csv(PRICE_DIR/"shares.csv", dtype={"cik":str})
    if shares.accession.duplicated().any():
        raise ValueError("Ambiguous duplicate accession share counts")
    shares = shares.set_index("accession").shares_outstanding
    market_last = prices["SPY"].last_valid_index()
    if market_last is None:
        raise RuntimeError("No observed benchmark closes")
    calendar_end = max(pd.Timestamp(sample_end), market_last) + pd.Timedelta(days=150)
    calendar = mcal.get_calendar("NYSE").valid_days("2020-09-01", calendar_end).tz_localize(None)
    benchmark = prices["SPY"].reindex(calendar)
    records = []
    missing = pd.Series(np.nan,index=calendar)
    for _, filing in data.iterrows():
        t = filing.ticker
        result = event_variables(filing, prices.get(t,missing), nominal.get(t,missing),
                        volume.get(t,missing),benchmark,shares.get(filing.accession,np.nan),calendar)
        day = result["day0"]
        for kind, offset in [("volatility",63),("return",3)]:
            idx = calendar.get_indexer([day])[0] if pd.notna(day) else -1
            result[kind+"_window_elapsed"] = bool(idx >= 0 and idx+offset < len(calendar)
                                                    and calendar[idx+offset] <= market_last)
        records.append(result)
    data = pd.concat([data, pd.DataFrame(records)],axis=1).replace([np.inf,-np.inf],np.nan)
    periods = pd.PeriodIndex(data.quarter,freq="Q")
    data["time_years"] = (periods.year-2021)+(periods.quarter-1)/4
    for season in [2,3,4]:
        data[f"season{season}"] = (periods.quarter==season).astype(int)
    samples = {}
    for name, kind in [("Volatility","volatility"),("Return","return")]:
        d = data.copy()
        record("Eligible text filings",len(d),d,name)
        filters = [("Usable day 0 and prior price at least $3", "valid_day0_price"),
                   ("Outcome window elapsed by market cutoff",kind+"_window_elapsed"),
                   ("60 observed returns before and after" if kind=="volatility" else "60 observed returns before filing",
                    "valid_history" if kind=="volatility" else "valid_pre_history"),
                   ("Complete pre/post volatility windows" if kind=="volatility" else "Complete four-session return window",
                    "complete_volatility" if kind=="volatility" else "complete_return")]
        for label, flag in filters:
            before = len(d);d = d[d[flag].fillna(False)].copy();record(label,before,d,name)
        before = len(d)
        d = d[d.shares_outstanding.notna() & d.log_size.notna()].copy()
        record("Accession-matched outstanding shares",before,d,name)
        before = len(d)
        controls = ["log_size","log_dollar_volume","pre_excess","pre_vol",
                    "post_vol" if kind=="volatility" else "event_excess"]
        d = d.dropna(subset=controls).reset_index(drop=True)
        record("Complete liquidity and model controls",before,d,name)
        samples[kind] = d
    audit = {"sample_start":SAMPLE_START,"sample_end":sample_end,"as_of_date":AS_OF_DATE,
             "market_last_date":str(market_last.date()),
             "period_incomplete":pd.Timestamp(sample_end).normalize() < pd.Period(sample_end,"Q").end_time.normalize(),
             "day0_moved_before_market_filters":int(data.day0_moved.sum()),
             "amendments":int(manifest.form.str.endswith("/A").sum()),
             "parse_failures":int(manifest.status.eq("parse_failed").sum()),
             "expected_original_filings":int(manifest.form.isin(["10-K","10-Q"]).sum()),
             "all_scored_filings":len(all_parsed),"final_filings":len(data),"final_companies":data.cik.nunique(),
             "day0_moved_final":int(data.day0_moved.sum()),
             "quarter_counts":data.groupby(["form","quarter"]).size().rename("n").reset_index().to_dict("records"),
             "dict_version":"1993–2025, updated March 2026; active category flags > 0"}
    for kind,d in samples.items():
        audit[kind+"_filings"],audit[kind+"_companies"] = len(d),d.cik.nunique()
        audit[kind+"_last_filing_date"] = str(d.filing_date.max().date()) if len(d) else None
    return all_parsed,data,samples["volatility"],samples["return"],pd.DataFrame(waterfall),audit


def construct_sample(sample_end=SAMPLE_END):
    """Compatibility entry point for the complete volatility sample and its filters."""
    _,text,vol,ret,waterfall,audit = _prepare_samples(sample_end)
    audit = dict(audit, final_filings=len(vol), final_companies=vol.cik.nunique())
    return vol,waterfall[waterfall["sample"].isin(["Text","Volatility"])].reset_index(drop=True),audit


def read_counts(data):
    counts = []
    for path in data.text_path:
        with gzip.open(ROOT/path,"rt",encoding="utf-8") as fh:
            counts.append(Counter(tokenize(fh.read())))
    return counts


def score_sample(data, counts, lexicons):
    data = data.copy().reset_index(drop=True)
    scores = score_corpus(counts,lexicons)
    for name in scores:
        data[name] = scores[name].to_numpy()
    return data


def figure_one(data, vix, path, sample_end=SAMPLE_END):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,
                         "axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(2,2,figsize=(7.15,4.7),sharex=True)
    quarters=pd.period_range(pd.Period(SAMPLE_START,"Q"),pd.Period(sample_end,"Q"),freq="Q").astype(str)
    x=np.arange(len(quarters))
    vixq=vix.groupby(vix.index.to_period("Q").astype(str)).mean().reindex(quarters)
    for ax,tone in zip(axes.flat,MEASURES):
        scale=100 if tone.endswith("prop") else 1
        for form,color in [("10-K","#174A72"),("10-Q","#C16B32")]:
            d=data[data.form.eq(form)].copy()
            d["adjusted_tone"]=d[tone]-d.groupby("cik")[tone].transform("mean")+d[tone].mean()
            series=d.groupby("quarter").adjusted_tone.mean().reindex(quarters)*scale
            ax.plot(x,series,color=color,lw=1.8,marker="o",ms=2.4,label=form)
        ax.set_title(LABELS[tone],loc="left",fontsize=9)
        ax.grid(axis="y",alpha=.18)
        ticks=sorted(set(list(range(0,len(quarters),4))+[len(quarters)-1]))
        ax.set_xticks(ticks,[quarters[i] for i in ticks],rotation=30)
        ax.tick_params(axis="x",labelsize=7)
        twin=ax.twinx()
        twin.plot(x,vixq,color="#8C9195",alpha=.5,ls="--",lw=1,label="VIX")
        twin.set_ylabel("VIX",color="#73777A",fontsize=8)
        twin.tick_params(axis="y",labelsize=7,colors="#73777A")
        twin.spines["top"].set_visible(False)
    axes[0,0].legend(frameon=False,loc="upper left",ncol=2)
    min_k = int(data[data.form.eq("10-K")].groupby("quarter").size().min())
    partial = f"{quarters[-1]} through {sample_end}; incomplete quarter." if pd.Timestamp(sample_end).normalize() < pd.Period(sample_end,"Q").end_time.normalize() else ""
    fig.text(.01,.01,"Company-centered means restore each form mean; entry/exit timing can still affect composition.\n"
             + "Dashed gray: mean VIX (right axis). Weights fitted by form. " + partial + "\n"
             + f"Minimum 10-K quarter N = {min_k}; quarterly counts accompany the analysis.",fontsize=7)
    fig.tight_layout(rect=[0,.11,1,1])
    fig.savefig(path,dpi=220,bbox_inches="tight")
    plt.close(fig)


def run_analysis(sample_end=SAMPLE_END, output_dir=OUTPUT_DIR):
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    all_parsed,data,vol_data,ret_data,waterfall,audit=_prepare_samples(sample_end)
    if data.empty:
        raise RuntimeError("No complete observations; cannot manufacture results")
    lexicons={k:v for k,v in load_all().items() if k in ["Negative","Uncertainty"]}
    all_counts=read_counts(all_parsed)
    score_sample(all_parsed,all_counts,lexicons).to_csv(output_dir/"all_filing_scores.csv",index=False)
    count_map=dict(zip(all_parsed.accession,all_counts))
    counts=[count_map[a] for a in data.accession]
    data=score_sample(data,counts,lexicons)
    data.to_csv(output_dir/"text_sample.csv",index=False)
    for name,d in [("volatility",vol_data),("return",ret_data)]:
        score_sample(d,[count_map[a] for a in d.accession],lexicons).to_csv(output_dir/f"{name}_sample.csv",index=False)
    if output_dir == OUTPUT_DIR:
        data.to_csv(INTERIM_DIR/"analysis_sample.csv",index=False)
    waterfall.to_csv(output_dir/"table1.csv",index=False)
    candidates=pd.read_csv(UNIVERSE_DIR/"holdings_candidates.csv",dtype={"cik":str})
    remaining=len(candidates)
    company_rows=[{"filter":"Raw holding identifiers", "removed":0, "remaining":remaining,"unit":"identifiers"}]
    for status,label in [("non_company_security","Funds and non-company securities"),
                         ("foreign_local_listing","Foreign local listings"),
                         ("unresolved_identifier","Unresolved SEC identifiers")]:
        removed=int(candidates.status.eq(status).sum());remaining-=removed
        company_rows.append({"filter":label,"removed":removed,"remaining":remaining,"unit":"identifiers"})
    unique=candidates.cik.nunique()
    company_rows.append({"filter":"Combine share classes by company CIK","removed":remaining-unique,"remaining":unique,"unit":"companies"})
    universe=pd.read_csv(UNIVERSE_DIR/"universe.csv",dtype={"cik":str})
    remaining=unique
    eligible_ciks=set(all_parsed.cik)
    excluded=universe[~universe.cik.isin(eligible_ciks)].copy()
    excluded["reason"]=excluded.get("no10x_reason",pd.Series(index=excluded.index,dtype=str)).fillna("")
    excluded.loc[excluded.reason.eq(""),"reason"]="No 10-K/Q in selected period"
    for reason,g in excluded.groupby("reason"):
        remaining-=len(g)
        company_rows.append({"filter":reason,"removed":len(g),"remaining":remaining,"unit":"companies"})
    pd.DataFrame(company_rows).to_csv(output_dir/"table1_universe.csv",index=False)
    form_samples=[]
    for form in ["10-K","10-Q"]:
        mask=data.form.eq(form).to_numpy()
        form_samples.append(score_sample(data.loc[mask],[c for c,k in zip(counts,mask) if k],lexicons))
    form_data=pd.concat(form_samples,ignore_index=True)
    rows=[]
    for form,d in form_data.groupby("form"):
        for tone in MEASURES:
            series=d[tone]*(100 if tone.endswith("prop") else 1)
            rows.append({"form":form,"measure":LABELS[tone],"n":len(d),"mean":series.mean(),
                "sd":series.std(),"p25":series.quantile(.25),"median":series.median(),
                "p75":series.quantile(.75),"min":series.min(),"max":series.max()})
    pd.DataFrame(rows).to_csv(output_dir/"table2.csv",index=False)
    words=common_words(counts,lexicons)
    words.to_csv(output_dir/"table3.csv",index=False)
    correlations=[]
    for form,d in [("All",data)]+list(form_data.groupby("form")):
        correlations.append({"form":form,**{kind:d[f"Negative_{kind}"].corr(d[f"Uncertainty_{kind}"])
                                             for kind in ["prop","tfidf"]}})
    audit.update({"correlations":correlations,"lexicon_counts":{k:len(v) for k,v in lexicons.items()},
                  "lexicon_overlap":len(lexicons["Negative"]&lexicons["Uncertainty"]),
                  "top10_shares":words[words["rank"]<=10].groupby("category").share_pct.sum().to_dict()})
    audit["uncertainty_word_document_pct"]={w:100*sum(w in c for c in counts)/len(counts)
                                             for w in ["MAY","APPROXIMATELY"]}
    trends,outcomes=[],[]
    for label in ["All","10-K","10-Q"]:
        mask=np.ones(len(data),dtype=bool) if label=="All" else data.form.eq(label).to_numpy()
        d=score_sample(data.loc[mask], [c for c,keep in zip(counts,mask) if keep],lexicons)
        print(f"Estimating {label}: {len(d)} filings",flush=True)
        t=trend_tests(d);t["sample"]=label;trends.append(t)
        for kind,base in [("volatility",vol_data),("return",ret_data)]:
            subset=base if label=="All" else base[base.form.eq(label)]
            scored=score_sample(subset,[count_map[a] for a in subset.accession],lexicons)
            o=outcome_tests(scored,kind=kind)
            keep=o.model.str.startswith("volatility") if kind=="volatility" else o.model.eq("filing_return")
            o=o[keep].copy();o["sample"]=label
            o["tone_sd"]=o.measure.map(scored[MEASURES].std().to_dict())
            o["effect_1sd"]=o.coef*o.tone_sd
            o["mde80_1sd"]=o.mde80*o.tone_sd
            outcomes.append(o)
    pd.concat(trends,ignore_index=True).to_csv(output_dir/"table4.csv",index=False)
    outcomes=pd.concat(outcomes,ignore_index=True)
    outcomes[outcomes.model.str.startswith("volatility")].to_csv(output_dir/"table5.csv",index=False)
    outcomes[outcomes.model.eq("filing_return")].to_csv(output_dir/"table6.csv",index=False)
    figure_one(form_data,_prices("prices.csv").loc[lambda x:x.index < MARKET_END,"^VIX"],output_dir/"figure1.png",sample_end)
    pd.DataFrame(audit["quarter_counts"]).to_csv(output_dir/"quarter_counts.csv",index=False)
    # Select a contrasting observation without inventing illustrative text.
    contrast=data.Negative_prop.rank(pct=True)-data.Uncertainty_prop.rank(pct=True)
    example=data.loc[contrast.idxmax()]
    with gzip.open(ROOT/example.text_path,"rt",encoding="utf-8") as fh:
        text=fh.read()
    import re
    sentences=re.split(r"(?<=[.!?])\s+",text)
    ranked=sorted(sentences,key=lambda s:sum(w in lexicons["Negative"] for w in tokenize(s)),reverse=True)
    audit["example"]={"ticker":example.ticker,"form":example.form,"filing_date":str(example.filing_date.date()),
                      "accession":example.accession,"doc_url":example.doc_url,
                      "negative_pct":100*example.Negative_prop,"uncertainty_pct":100*example.Uncertainty_prop,
                      "negative_percentile":float(data.Negative_prop.rank(pct=True).loc[example.name]),
                      "uncertainty_percentile":float(data.Uncertainty_prop.rank(pct=True).loc[example.name]),
                      "sentence":" ".join(next((s for s in ranked if 40<len(s)<550),ranked[0][:500]).split()[:24])+" …"}
    (output_dir/"audit.json").write_text(json.dumps(audit,indent=2,default=str))
    print(json.dumps(audit,indent=2,default=str),flush=True)
    return data

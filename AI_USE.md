# AI use disclosure

**Tools used:** OpenAI Codex, including bounded subagents for specific code and review tasks; the configured EdgarTools MCP was used to test SEC connectivity. Data acquisition used SEC EDGAR and Yahoo Finance through reproducible Python code.

**What I used them for:** Codex inspected the course starter repository, obtained public data, corrected parsing and point-in-time data handling, implemented dictionary scoring and event windows, wrote and ran tests and regressions, and generated the notebook and report. Results are computed from downloaded filings and prices, not invented by the model.

**What I wrote myself:** The student supplied the assignment and the holdings and starter-repository sources. The analysis code and report text were generated with AI assistance; this disclosure makes no claim that the student independently wrote, rewrote or manually verified them. The student remains responsible for understanding every submitted line.

**Anything the model got wrong that I had to correct:** During the assisted work, the model initially overlooked the existing EDGAR identity configuration. Code review also caught an event-calendar implementation that would drop missing benchmark dates and a history filter that prematurely required day +63; both were corrected and regression-tested. The assisted process distinguished visible inline-XBRL text from hidden scaffolding, prevented arbitrary share-count selection, and kept acquisition failures separate from analysis exclusions. These corrections were made during AI-assisted review, not represented as independent student corrections.

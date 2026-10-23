# How the biological cases should enter the explorer

This is a specification and supplied data payload, not a claim of a deployed UI.
No full23run rebuild is needed merely to access the four cases: their original
scores are already present in the completed197MBlocal explorer.

Add a compact case-entry section with four explicit roles: persistent contrast
without the training line, training-line caution, shared high signal and
inconclusive contrast. Each entry must open the exact transcript/site, rather
than only choosing a gene's default transcript. Existing gene-only links do not
yet guarantee that exact destination.

Show run scores/readcounts, the equal-weight group summary, eligible group/run
counts and20/50/100depth outcomes. Keep missing/low-read values distinct from
zero. The0.5/0.7/0.9checks belong alongside continuous differences: HNRNPA1/RAB1B
high-side means pass0.5butnot0.7; ACTG1passesallthree inallsevenlines. G3BP2must
state range overlap and lack of a qualifying pair at stricter depths.

Include the exact seven-base context, training-positive-context support and
training-key diagnostic. Do not label data0label1as validation or data0label0as
a proven SG-NEx error. Display basecaller/platform differences as alternative
explanations. Link primary literature as gene-level context with the explicit
unmatched-site caveat. Scores cannot show altered splicing, trafficking or
stress-granule activity.

The selection rule and full ranked alternatives must remain accessible. These
are selected extremes, not representative examples or an exhaustive biological
summary. Keep all23run/global summaries and separate pairwise denominators.
`explorer_cases.json` supplies keys, scores, groups, warnings and source receipts;
verify its publication hash before integration. A final case panel, browser QA
and public deployment remain pending.

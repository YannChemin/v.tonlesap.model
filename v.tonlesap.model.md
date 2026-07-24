# v.tonlesap.model

## DESCRIPTION

*v.tonlesap.model* implements a multi-criteria pairwise-comparison
outranking model to score the suitability of Tonle Sap (Cambodia) villages
for one of three sectors: **irrigation**, **aquaculture** or **potable
water**. It is a native GRASS vector port of the standalone
[TSAPMODEL](https://github.com/YannChemin/TSAPMODEL) scripts (`TLI.py`,
`TLA.py`, `TLP.py`), written for IWMI.

The module reads three attribute columns (the *outranking criteria*) from
the **input** vector points map, compares every pair of villages for each
criterion, and accumulates a signed score per village weighted by
**weights** and the **better** direction (*more is better* or *less is
better*). The result is rescaled to 0-1 and written to a new
**score_column** (default `tsap_score`) in **output**.

An optional **screening** step removes villages that do not satisfy one or
more threshold conditions (e.g. `TOPOZONE,le,3`) from the *output* map —
screening does not affect how the score itself is computed, it only
filters which villages appear in the final result, matching the behaviour
of the original scripts.

### Criteria selection

Which attribute columns are used depends on **sector**:

* **irrigation** (all three required):
  * `crit1`: 0=`MA_INDACT`, 1=`MA_PROXROAD`
  * `crit2`: 0=`TAGAP_DRY`, 1=`TAGAP_WET`
  * `crit3`: 0=`SW_PROXRIV`, 1=`SW_PONDS`, 2=`GW_DWELL`, 3=`GW_BOREW`,
    4=`IRRI_SCH`, 5=`IRRI_HEAD`
* **aquaculture** (`crit1`/`crit2` required, `crit3` ignored):
  * `crit1`: 0=`MA_INDACT`, 1=`MA_PROXROAD`
  * `crit2`: 0=`SW_PROXRIV`, 1=`SW_PONDS`
  * 3rd criterion is always `FISHPRO` (compulsory)
* **potable** (`crit1`/`crit2`/`crit3` ignored, always uses all three):
  * `WA_AWAY`, `WS_UNSAFE`, `WT_UNTREAT`

**weights** and **better** always take exactly 3 comma-separated values,
in the same order as the resolved criteria above.

### Demonstration dataset

The addon ships the original TSAPMODEL `tablefile.csv` for each sector
(surveyed in *Indian 1960 / UTM zone 48N*, EPSG:3148). Pass the **-d**
flag to import the bundled dataset for the chosen **sector** on the fly
and use it as input instead of **input=** — this recreates the original
demonstration mapping without needing any external data. The current
GRASS project must be in EPSG:3148 (create one with
`grass -c EPSG:3148 <GISDBASE>/<project> -e` if needed).

## NOTES

The pairwise comparison is O(n^2) per criterion (n = number of input
features), vectorised with NumPy. Very large village counts will still be
slow; consider pre-filtering the input vector if performance becomes an
issue.

## EXAMPLES

Reproduce the original TLI.py self-test (irrigation, proxroad + wet +
proxriv) using the bundled demonstration dataset:

```sh
grass -c EPSG:3148 ~/grassdata/tonlesap_demo -e
grass ~/grassdata/tonlesap_demo/PERMANENT --exec \
  v.tonlesap.model -d sector=irrigation output=irrigation_score \
  crit1=0 crit2=1 crit3=0 weights=1.0,1.0,1.0 better=m,l,l
```

Run the aquaculture model on an existing vector, screening out villages
above elevation 5 and with TOPOZONE greater than 3:

```sh
v.tonlesap.model input=villages output=aqua_score sector=aquaculture \
  crit1=0 crit2=1 weights=1.0,1.0,1.0 better=m,l,m \
  screening=ELEVATION,ge,5,TOPOZONE,le,3
```

Run the potable-water model (fixed 3-column criteria set, no crit1/2/3):

```sh
v.tonlesap.model input=villages output=potable_score sector=potable \
  weights=1.0,1.0,1.0 better=m,m,l
```

## SEE ALSO

*[v.extract](v.extract.html)*, *[v.db.select](v.db.select.html)*,
*[v.in.ascii](v.in.ascii.html)*

## AUTHORS

Yann Chemin

Original TSAPMODEL: [github.com/YannChemin/TSAPMODEL](https://github.com/YannChemin/TSAPMODEL)

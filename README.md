# v.tonlesap.model

GRASS GIS addon: multi-criteria pairwise-comparison outranking model for
site suitability of Tonle Sap (Cambodia) villages, for irrigation,
aquaculture or potable-water siting.

Native GRASS vector port of the standalone
[TSAPMODEL](https://github.com/YannChemin/TSAPMODEL) scripts
(`TLI.py`/`TLA.py`/`TLP.py`), written for IWMI. See
[v.tonlesap.model.md](v.tonlesap.model.md) for full usage.

## Build

```sh
make MODULE_TOPDIR=$HOME/dev/grass
```

## Quick demo

Ships the original per-sector `tablefile.csv` datasets under `data/`, so
the demonstration mapping can be reproduced with no external data (`-d`
flag imports the bundled dataset; requires an EPSG:3148 project):

```sh
grass -c EPSG:3148 ~/grassdata/tonlesap_demo -e
grass ~/grassdata/tonlesap_demo/PERMANENT --exec \
  v.tonlesap.model -d sector=irrigation output=irrigation_score \
  crit1=0 crit2=1 crit3=0 weights=1.0,1.0,1.0 better=m,l,l
```

## License

Public domain (Unlicense) — see [LICENSE](LICENSE).

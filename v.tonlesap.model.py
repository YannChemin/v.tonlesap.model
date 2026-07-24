#!/usr/bin/env python3
"""
MODULE:       v.tonlesap.model

AUTHOR(S):    Yann Chemin

PURPOSE:      Multi-criteria pairwise-comparison outranking model for site
              suitability of Tonle Sap villages (irrigation, aquaculture,
              or potable water sectors). Port of the standalone TSAPMODEL
              TLI.py/TLA.py/TLP.py scripts (github.com/YannChemin/TSAPMODEL)
              to a native GRASS vector addon.

COPYRIGHT:    (C) 2026 by Yann Chemin

              This is free and unencumbered software released into the
              public domain. See the file LICENSE (unlicense.org) that
              comes with this addon for details.

SPDX-License-Identifier: Unlicense
"""

#%module
#% description: Multi-criteria pairwise-comparison outranking model for site suitability (Tonle Sap villages)
#% keyword: vector
#% keyword: multi-criteria
#% keyword: outranking
#% keyword: suitability
#%end

#%option G_OPT_V_INPUT
#% required: no
#% description: Name of input vector points map with village attribute table (ignored if -d is given)
#%end

#%option G_OPT_V_OUTPUT
#%end

#%option
#% key: sector
#% type: string
#% required: yes
#% options: irrigation,aquaculture,potable
#% description: Sector-specific criteria set to apply
#%end

#%option
#% key: crit1
#% type: integer
#% required: no
#% description: Index of criterion choice 1 (0/1; meaning depends on sector, see manual; ignored for sector=potable)
#%end

#%option
#% key: crit2
#% type: integer
#% required: no
#% description: Index of criterion choice 2 (0/1; meaning depends on sector, see manual; ignored for sector=potable)
#%end

#%option
#% key: crit3
#% type: integer
#% required: no
#% description: Index of criterion choice 3 (0-5 for sector=irrigation; ignored for aquaculture/potable)
#%end

#%option
#% key: weights
#% type: double
#% multiple: yes
#% required: yes
#% description: Weight for each of the 3 criteria, comma separated (0.0-1.0)
#%end

#%option
#% key: better
#% type: string
#% multiple: yes
#% required: yes
#% options: m,l
#% description: Direction for each of the 3 criteria, comma separated (m=more is better, l=less is better)
#%end

#%option
#% key: screening
#% type: string
#% multiple: yes
#% required: no
#% key_desc: column,operator,threshold
#% description: Screening triplets column,operator,threshold (operator: le,ge,eq,ne,lt,gt)
#%end

#%option
#% key: score_column
#% type: string
#% required: no
#% answer: tsap_score
#% description: Name of output column to hold the computed suitability score
#%end

#%flag
#% key: d
#% description: Ignore input=, import the bundled Tonle Sap demonstration dataset for sector= instead
#%end

import csv
import os
import sys

import grass.script as gs

# Criteria choice groups, by attribute column name (mirrors the mutually
# exclusive crit1/crit2/crit3 choices of the original TLI.py/TLA.py).
SECTOR_GROUPS = {
    "irrigation": {
        1: ["MA_INDACT", "MA_PROXROAD"],
        2: ["TAGAP_DRY", "TAGAP_WET"],
        3: ["SW_PROXRIV", "SW_PONDS", "GW_DWELL", "GW_BOREW", "IRRI_SCH", "IRRI_HEAD"],
    },
    "aquaculture": {
        1: ["MA_INDACT", "MA_PROXROAD"],
        2: ["SW_PROXRIV", "SW_PONDS"],
    },
}
# Aquaculture's 3rd criterion is compulsory (no crit3 choice in the original).
AQUACULTURE_FIXED_CRIT3 = "FISHPRO"
# Potable has no crit1/crit2/crit3 choice at all: 3 fixed compulsory columns.
POTABLE_COLUMNS = ["WA_AWAY", "WS_UNSAFE", "WT_UNTREAT"]

SCREEN_OPERATORS = {"le": "<=", "ge": ">=", "eq": "=", "ne": "<>", "lt": "<", "gt": ">"}

# Demonstration dataset shipped with the addon, one CSV per sector, in the
# same layout as the original TSAPMODEL tablefile.csv. Surveyed in
# Indian_1960 / UTM zone 48N (EPSG:3148).
DEMO_EPSG = "3148"


def resolve_criteria(sector, crit1, crit2, crit3):
    """Return the ordered list of 3 attribute column names for this sector."""
    if sector == "potable":
        return list(POTABLE_COLUMNS)

    groups = SECTOR_GROUPS[sector]
    cols = []
    for key, group_no, value in (("crit1", 1, crit1), ("crit2", 2, crit2)):
        group = groups[group_no]
        if value is None:
            gs.fatal(_("%s is required for sector=%s") % (key, sector))
        idx = int(value)
        if idx < 0 or idx >= len(group):
            gs.fatal(
                _("%s must be between 0 and %d for sector=%s")
                % (key, len(group) - 1, sector)
            )
        cols.append(group[idx])

    if sector == "irrigation":
        group3 = groups[3]
        if crit3 is None:
            gs.fatal(_("crit3 is required for sector=irrigation"))
        idx = int(crit3)
        if idx < 0 or idx >= len(group3):
            gs.fatal(_("crit3 must be between 0 and %d for sector=irrigation") % (len(group3) - 1))
        cols.append(group3[idx])
    else:  # aquaculture
        cols.append(AQUACULTURE_FIXED_CRIT3)

    return cols


def parse_screening(raw):
    """Parse column,operator,threshold triplets into (column, sql_op, threshold)."""
    if not raw:
        return []
    parts = raw.split(",")
    if len(parts) % 3 != 0:
        gs.fatal(_("screening must be given as column,operator,threshold triplets"))
    triplets = []
    for i in range(0, len(parts), 3):
        col, op, threshold = parts[i], parts[i + 1], parts[i + 2]
        if op not in SCREEN_OPERATORS:
            gs.fatal(_("Unknown screening operator '%s' (use le,ge,eq,ne,lt,gt)") % op)
        triplets.append((col, SCREEN_OPERATORS[op], threshold))
    return triplets


def demo_csv_path(sector):
    etc_dir = os.path.join(gs.gisenv()["GISBASE"], "etc", "v.tonlesap.model", "data", sector)
    path = os.path.join(etc_dir, "tablefile.csv")
    if not os.path.exists(path):
        gs.fatal(_("Bundled demonstration dataset not found at <%s>") % path)
    return path


def import_demo(sector):
    """Import the bundled demonstration CSV for sector into a temporary vector."""
    proj_epsg = gs.parse_command("g.proj", flags="g").get("srid", "")
    if DEMO_EPSG not in proj_epsg:
        gs.fatal(
            _(
                "The bundled demonstration dataset is in EPSG:%s, but the "
                "current project is <%s>. Create/switch to a project in "
                "EPSG:%s before using -d (e.g. grass -c EPSG:%s "
                "<GISDBASE>/<project> -e)."
            )
            % (DEMO_EPSG, proj_epsg, DEMO_EPSG, DEMO_EPSG)
        )

    csv_path = demo_csv_path(sector)
    with open(csv_path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))

    try:
        x_idx = header.index("XCOOR") + 1
        y_idx = header.index("YCOOR") + 1
    except ValueError:
        gs.fatal(_("Bundled dataset <%s> has no XCOOR/YCOOR columns") % csv_path)

    columns = ",".join("%s double precision" % name for name in header)
    tmp_map = gs.tempname(12)
    gs.run_command(
        "v.in.ascii",
        input=csv_path,
        output=tmp_map,
        format="point",
        separator="comma",
        skip=1,
        x=x_idx,
        y=y_idx,
        columns=columns,
        overwrite=gs.overwrite(),
        quiet=True,
    )
    gs.message(_("Imported bundled <%s> demonstration dataset as <%s>") % (sector, tmp_map))
    return tmp_map


def read_columns(vector_map, columns):
    """Read numeric columns from the vector's attribute table, aligned by cat."""
    import numpy as np

    sel = gs.vector_db_select(map=vector_map, columns=",".join(columns))
    col_index = {name: i for i, name in enumerate(sel["columns"])}
    cats = sorted(sel["values"].keys(), key=lambda k: int(k))
    if not cats:
        gs.fatal(_("Input vector <%s> has no records") % vector_map)

    arrays = {}
    for col in columns:
        idx = col_index[col]
        arrays[col] = np.array(
            [float(sel["values"][cat][idx]) for cat in cats], dtype=float
        )
    return [int(c) for c in cats], arrays


def pairwise_score(vals, weight, less_is_better):
    """
    Vectorised equivalent of the original TL*.py nested-loop pairwise
    comparison (assignvpwc called for every ordered village pair). The
    triple loop recomputed the value range on every call (O(n^3)); this
    replaces it with one O(n^2) broadcasted computation with identical
    per-pair semantics.
    """
    import numpy as np

    valrange = vals.max() - vals.min()
    if valrange == 0:
        gs.warning(_("Criterion is constant across all features, skipping it"))
        return np.zeros(len(vals))

    diff = (vals[:, None] - vals[None, :]) / valrange * weight
    pos = np.clip(diff, 0, None)
    neg = np.clip(diff, None, 0)
    if less_is_better:
        return pos.sum(axis=1) + neg.sum(axis=0)
    return neg.sum(axis=1) + pos.sum(axis=0)


def main():
    options, flags = gs.parser()

    output_map = options["output"]
    sector = options["sector"]
    score_column = options["score_column"]

    demo_map = None
    if flags["d"]:
        demo_map = import_demo(sector)
        input_map = demo_map
    else:
        if not options["input"]:
            gs.fatal(_("input= is required unless -d is given"))
        input_map = options["input"]

    crit1 = options["crit1"] if options["crit1"] else None
    crit2 = options["crit2"] if options["crit2"] else None
    crit3 = options["crit3"] if options["crit3"] else None

    criteria_cols = resolve_criteria(sector, crit1, crit2, crit3)

    weights = [float(w) for w in options["weights"].split(",")]
    better = options["better"].split(",")
    if len(weights) != 3:
        gs.fatal(_("weights must have exactly 3 comma-separated values"))
    if len(better) != 3:
        gs.fatal(_("better must have exactly 3 comma-separated values"))

    screening = parse_screening(options["screening"])

    existing_cols = set(gs.vector_columns(input_map).keys())
    for col in criteria_cols:
        if col not in existing_cols:
            gs.fatal(_("Column <%s> not found in attribute table of <%s>") % (col, input_map))
    for col, _op, _threshold in screening:
        if col not in existing_cols:
            gs.fatal(_("Screening column <%s> not found in attribute table of <%s>") % (col, input_map))

    import numpy as np

    unique_cols = list(dict.fromkeys(criteria_cols + [c for c, _o, _t in screening]))
    cats, arrays = read_columns(input_map, unique_cols)

    n = len(cats)
    total = np.zeros(n)
    for col, weight, direction in zip(criteria_cols, weights, better):
        total += pairwise_score(arrays[col], weight, less_is_better=(direction == "l"))

    total = np.clip(total, 0, None)
    vmin, vmax = total.min(), total.max()
    if vmax - vmin == 0:
        gs.warning(_("All computed scores are equal; output column will be constant 0"))
        scaled = np.zeros(n)
    else:
        scaled = (total - vmin) / (vmax - vmin)

    score = {cat: float(scaled[i]) for i, cat in enumerate(cats)}

    tmp_map = gs.tempname(12)
    target = tmp_map if screening else output_map

    gs.run_command("g.copy", vector=[input_map, target], overwrite=gs.overwrite(), quiet=True)
    gs.run_command(
        "v.db.addcolumn", map=target, columns="%s double precision" % score_column, quiet=True
    )

    sql = "\n".join(
        "UPDATE %s SET %s = %.6f WHERE cat = %d;" % (target, score_column, score[cat], cat)
        for cat in cats
    )
    gs.write_command("db.execute", input="-", stdin=sql, quiet=True)

    if screening:
        where_clause = " AND ".join(
            "%s %s %s" % (col, op, threshold) for col, op, threshold in screening
        )
        gs.run_command(
            "v.extract",
            input=target,
            output=output_map,
            where=where_clause,
            overwrite=gs.overwrite(),
            quiet=True,
        )
        gs.run_command("g.remove", type="vector", name=target, flags="f", quiet=True)

    if demo_map:
        gs.run_command("g.remove", type="vector", name=demo_map, flags="f", quiet=True)

    gs.vector_history(output_map)
    gs.message(
        _("Suitability score written to column <%s> in vector map <%s>")
        % (score_column, output_map)
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

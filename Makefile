MODULE_TOPDIR = ../..

PGM = v.tonlesap.model

include $(MODULE_TOPDIR)/include/Make/Script.make
include $(MODULE_TOPDIR)/include/Make/Html.make

default: script html demodata

# Ship the bundled per-sector demonstration datasets (used by the -d flag
# to recreate the Tonle Sap mapping without an external data source) under
# $(ETC)/$(PGM)/data/<sector>/tablefile.csv. Script.make's own "install"
# rule already copies $(ETC)/$(PGM) into $(INST_DIR)/etc if it exists, so
# no extra install: rule is needed here.
demodata:
	$(MKDIR) $(ETC)/$(PGM)/data/irrigation
	$(MKDIR) $(ETC)/$(PGM)/data/aquaculture
	$(MKDIR) $(ETC)/$(PGM)/data/potable
	$(INSTALL_DATA) data/irrigation/tablefile.csv $(ETC)/$(PGM)/data/irrigation/tablefile.csv
	$(INSTALL_DATA) data/aquaculture/tablefile.csv $(ETC)/$(PGM)/data/aquaculture/tablefile.csv
	$(INSTALL_DATA) data/potable/tablefile.csv $(ETC)/$(PGM)/data/potable/tablefile.csv

.PHONY: demodata

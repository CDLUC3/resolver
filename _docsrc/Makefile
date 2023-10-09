# ===== Usage ================================================================
#
# make                  Prepare docs/ folder (all markdown & assets)
# make clean            Delete all generated files
# ============================================================================

SOURCES := $(shell find . -type f -name '*.md')
TARGETS := $(patsubst ./%.md,../docs/%.md,$(SOURCES))

.PHONY: all
all: $(TARGETS)

.PHONY: clean
clean:
	rm -rf ../docs/*.md ./_codebraid

.PHONY: docs
docs: $(TARGETS)

# Generalized rule: how to build a .html file from each .md
# Note: you will need pandoc 2 or greater for this to work
../docs/%.md: %.md Makefile ./build.sh
	./build.sh "$<" "$@"

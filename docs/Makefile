#
# Author: Jake Zimmerman <jake@zimmerman.io>
#
# ===== Usage ================================================================
#
# make                  Prepare docs/ folder (all markdown & assets)
# make docs/index.html  Recompile just docs/index.html
#
# make watch            Start a local HTTP server and rebuild on changes
# PORT=4242 make watch  Like above, but use port 4242
#
# make clean            Delete all generated files
#
# ============================================================================

SOURCES := $(shell find . -type f -name '*.md')
TARGETS := $(patsubst %.md,%.html,$(SOURCES))

.PHONY: all
all: .nojekyll $(TARGETS)

.PHONY: clean
clean:
	rm -rf *.html _codebraid

.PHONY: watch
watch:
	../tools/doc_serve.sh --watch

.nojekyll:
	touch .nojekyll

.PHONY: docs
docs: .nojekyll

# Generalized rule: how to build a .html file from each .md
# Note: you will need pandoc 2 or greater for this to work
%.html: %.md ../tools/template.html5 Makefile ../tools/build.sh
	../tools/build.sh "$<" "$@"



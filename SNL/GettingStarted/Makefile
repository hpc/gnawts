
LATEXMK      = latexmk
LATEXMKFLAGS = -f -pdf -g
LATEXMKCLEAN = -C

SOURCES      = GettingStarted.tex
EXECS        = $(SOURCES:.tex=.pdf)
BASE         = $(SOURCES:.tex=)

TEXSRC       = $(filter-out $(SOURCES), $(shell ls *.tex))

BIBSRC       = $(shell ls *.bib)
BBL          = $(notdir $(BIBSRC:.bib=.bbl))

DEPS         = $(DEP) $(TEXSRC) $(BIBSRC)


all: $(EXECS)

$(EXECS): %.pdf : %.tex $(DEPS)
	$(LATEXMK) $(LATEXMKFLAGS) $<
	$(LATEXMK) $(LATEXMKFLAGS) $<

$(BBL): $(BIBSRC)
	bibtex $(BASE)

view:	all
	$(LATEXMK) -pvc -view=ps -r latexmkrc paper

clean:
	-$(LATEXMK) $(LATEXMKCLEAN)
	-rm -f *~


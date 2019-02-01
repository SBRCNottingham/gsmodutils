#!/bin/bash

pdflatex pathway.tex

pdftops -eps pathway.pdf

pdflatex cycle.tex
pdflatex design.tex
pdflatex test_case.tex
pdflatex inheritence.tex

pdftops -eps cycle.pdf
pdftops -eps design.pdf
pdftops -eps test_case.pdf
pdftops -eps inheritence.pdf

pdflatex article.tex
bibtex article.aux
pdflatex article.tex


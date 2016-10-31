# junthelper

Simple program that scores job postings from various job aggregating websites and scores them accordingly. The extracts data from an arbitrary website, reads the text, and scores the page based on the presence of specific keywords.

Author: David Tétreault-La Roche
# Installation
Prior to running the program, a database file must be instantiated. This can be done with:
```
python -c "import juntdb; juntdb.init()"
```
executed in the cloned git repository.


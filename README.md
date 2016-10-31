# junthelper

Simple program that scores job postings from various job aggregating websites and scores them accordingly. The extracts data from an arbitrary website, reads the text, and scores the page based on the presence of specific keywords.

Author: David Tétreault-La Roche
# Installation
Prior to running the program, a database file must be instantiated. This can be done with:
```
python -c "import juntdb; juntdb.init()"
```
executed in the cloned git repository.

# Utilization
Setup the scoring scheme in `scorefile.csv` according to the syntax specified in said file.

The two default websites `indeed.ca` and `careerjet.ca` can be scraped by using `lib.exec_crawl`. 

Once scraped, the job postings can be scored using `lib.score_db` and displayed with `lib.get_sensible_jentries`.

Finally, desired job entries can be displayed in your system's default browser with `lib.open_in_browser`

See the docstring of each for details. The file `wrapper.py` contains an example of the workflow of this project.

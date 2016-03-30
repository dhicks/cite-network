## A quick script to take the results from stics_to_doi and generate a Scopus search string

import pandas as pd

dois = pd.read_csv('results.csv')['doi']

dois_search = ['DOI(' + str(doi) + ')' for doi in dois if not pd.isnull(doi)]

with open('search_string.txt', 'w') as writefile:
	writefile.write(' OR '.join(dois_search))
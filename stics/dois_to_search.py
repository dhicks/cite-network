## A quick script to take the results from stics_to_doi and generate a Scopus search string
import json
import pandas as pd

dois = pd.read_csv('results.csv')['doi'].tolist()

dois = [doi for doi in dois if not pd.isnull(doi)]

with open('css_dois_file.txt', 'w') as writefile:
	json.dump(dois, writefile)

dois_search = ['DOI(' + str(doi) + ')' for doi in dois]

with open('search_string.txt', 'w') as writefile:
	writefile.write(' OR '.join(dois_search))
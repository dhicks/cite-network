import html
import json
import pandas as pd
import re
import requests

from api_key import MY_API_KEY

def get_query (query):
	response = requests.get(query)
	note = []
	if response.status_code == 400:
		note += ['Scopus returned a parse error']
#	elif response.status_code == 401:
#		note = 'Scopus returned a parse error'
	elif response.status_code != 200:
		print('Query response ' + str(response.status_code))
		print(response.text)
		input()
	return response, note

stics_data = pd.read_csv('STICS output.csv')
titles = stics_data['Title'].tolist()
## Many titles have HTML-escaped non-ascii characters, 
##  or other characters that will break the search string
titles = [html.unescape(title) for title in titles]
titles = [re.sub(r'[&#()?\r\n]', '', title) for title in titles]

data = []

base_query = 'http://api.elsevier.com/content/search/scopus?'
for title in titles:
	print(len(data))
	query = base_query + 'query=title("' + title + '")&' + 'apiKey=' + MY_API_KEY
	print(query)

	doi = ''
	response, note = get_query(query)
	results = response.json()
	
	if response.status_code != 200 or 'service-error' in results:
		## If we get an error status, try an unquoted search
		print('\t', 'Error; trying unquoted search')
		query = base_query + 'query=title(' + title + ')&' + 'apiKey=' + MY_API_KEY
		print('\t', query)
		response, note = get_query(query)
		note += ['Unquoted search']
		results = response.json()
	if response.status_code != 200 or 'service-error' in results:
		## If we still get an error status, finish with this title
		print('\t', 'Search returned error: ' + str(response.status_code))
		data += [{'title': title, 'doi': doi, 'note': note, 'query': query}]
		print(response.text)
		input()
		continue

	if results['search-results']['opensearch:totalResults'] == '0' or \
			results['search-results']['opensearch:totalResults'] is None:
		## If there weren't any results, try an unquoted search
		print('\t', 'No results; trying unquoted search')
		query = base_query + 'query=title(' + title + ')&' + 'apiKey=' + MY_API_KEY
		print('\t', query)
		response, note = get_query(query)
		note += ['Unquoted search']
		results = response.json()
	if 'search-results' not in results or \
			results['search-results']['opensearch:totalResults'] == '0' or \
			results['search-results']['opensearch:totalResults'] is None:
		## If the result is still no results, finish with this title
		print('\t', 'Search found no results')
		data += [{'title': title, 'doi': doi, 'note': note, 'query': query}]
		continue
	
	n_results = int(results['search-results']['opensearch:totalResults'])
	
	if n_results > 1:
		note += ['Scopus returned multiple results']

	results = results['search-results']['entry']

	if 'prism:doi' in results[0]:
		doi = results[0]['prism:doi']
	elif n_results > 0:
		note += ['No DOI in result']

	data += [{'title': title, 'doi': doi, 'note': note, 'query': query}]
	print()
	
pd.DataFrame(data)[['title', 'doi', 'note', 'query']].to_csv('results.csv')
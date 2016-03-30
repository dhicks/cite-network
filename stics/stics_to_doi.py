import json
import pandas as pd
import requests

from api_key import MY_API_KEY

stics_data = pd.read_csv('STICS output.csv')
titles = stics_data['Title'].tolist()

data = []

base_query = 'http://api.elsevier.com/content/search/scopus?'
for title in titles:
	query = base_query + 'query=title("' + title + '")&' + 'apiKey=' + MY_API_KEY
	print(query)

	note = ''
	doi = ''
	response = requests.get(query)
	if response.status_code == 400:
		note = 'Scopus returned a parse error'
	elif response.status_code == 401:
		note = 'Scopus failed to parse the request'
	elif response.status_code != 200:
		print('Query response ' + str(response.status_code))
		exit(1)
	else:
		response = response.json()
		results = response['search-results']['entry']

		if len(results) > 1:
			note = 'Scopus returned multiple results'
		if 'error' in results[0]:
			note = 'Scopus returned error'
		if 'prism:doi' not in results[0]:
			note = 'No DOI in result'
		else:
			doi = results[0]['prism:doi']

	data += [{'title': title, 'doi': doi, 'note': note, 'query': query}]
	
pd.DataFrame(data)[['title', 'doi', 'note', 'query']].to_csv('results.csv')
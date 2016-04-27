import csv
import json

papers_file = 'papers.json'
val_list_file = 'validation.json'
val_spreadsheet_file = 'validation.csv'

with open(papers_file) as readfile:
	papers = json.load(readfile)
	
with open(val_list_file) as readfile:
	validation_sids = json.load(readfile)
	
validation = [paper for paper in papers if paper['sid'] in validation_sids]

for paper in validation:
	paper['n_author'] = len(paper['authors'])
	paper['n_references'] = len(paper['references'])
	
with open(val_spreadsheet_file, 'w') as writefile:
	fieldnames = ['sid', 'doi', 'n_author', 'n_references']
	writer = csv.DictWriter(writefile, fieldnames, extrasaction='ignore')
	writer.writeheader()
	writer.writerows(validation)
# -*- coding: utf-8 -*-
'''
Starting with the `csv` file for generation 1, retrieve the desired metadata.  
'''

import batch
import csv

import os
import random
import pandas as pd
from scrape import *
import sys
import time

# File with the list of generation 1 DOIs
#infile = 'gen 01 2016-03-30.csv'
infile = 'gen 01 2016-03-30.xlsx'

# Files to save the scraped data
gen_1_outfile = 'gen_1.json'
gen_0_outfile = 'gen_0.json'
gen_n1_outfile = 'gen_n1.json'
combined_outfile = 'papers.json'

# File with the DOIs for the core set
css_dois_file = 'css_dois.txt'

print('Run started at ' + time.strftime('%c', time.localtime()))

# A file to track the status of the scrape
status_file = 'status.json'
if os.access(status_file, os.R_OK):
	with open(status_file) as readfile:
		status = json.load(readfile)
else:
	status = {
		# Generation +1
		'1': {'start': False, 'finish': False},
		# Generation 0
		'2a': {'start': False, 'finish': False},
		# Generation -1
		'2b': {'start': False, 'finish': False},
		# Set core set metadata
		'3': {'start': False, 'finish': False}, 
		# Print a sample of IDs for validation
		'4': {'start': False, 'finish': False}}



# Step 1:  Define core set and retrieve metadata

if status['1']['start'] == False:
	# Get the DOIs manually retrieved from Scopus
	gen_1_doi = pd.read_excel(infile)['DOI'].tolist()
	#print(gen_1_doi)
	print(str(len(gen_1_doi)) + ' items in generation +1')

	if not batch.exists_batch():
		print('Setting batch for generation +1')
		batch_response = batch.set_batch(gen_1_doi)

	if batch_response == True:
		status['1']['start'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)
	else:	
		raise Exception('Error setting batch')

if status['1']['finish'] == False:
	if batch.exists_batch():
		# Run the batch
		print('Running batch for generation +1')
		batch_response = batch.run_batch(get_meta_by_doi)

	# If the batch finished on this run, or previously, exists_batch will return False
	if batch.exists_batch():
		# Exit gracefully
		print('Finished the current batch run; batch not finished')
		sys.exit(0)
	else:
		print('Finished the batch; moving data and cleaning up')
		# Retrieve the batch results
		gen_1 = batch.retrieve_batch()
		# Write them to a permanent file
		with open(gen_1_outfile, 'w') as writefile:
			json.dump(gen_1, writefile)
		# Clean up the batch output
		batch.clean_batch()
		
		# Finished with step 1
		status['1']['finish'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)



# Step 2:  Two generation backwards search

if status['2a']['start'] == False:
	# Load generation 1
	with open(gen_1_outfile) as readfile:
		gen_1 = json.load(readfile)
	# Extract the generation 1 SIDs
	gen_1_sid = [paper['sid'] for paper in gen_1]
	# Extract the references
	#  This isn't perspicuous.  
	#  `for paper in gen_1` gets every paper in generation 1
	#  `if 'references' in paper` filters out the papers without reference lists
	#  `for reference in paper['references']` unpacks the list of references
	#  Extracting as a set removes redundancies automatically
	gen_0_sid = {reference for paper in gen_1 
								if 'references' in paper 
							for reference in paper['references']}
	# Remove the SIDs that we've already scraped
	gen_0_sid = {sid for sid in gen_0_sid if sid not in gen_1_sid}

	print(str(len(gen_0_sid)) + ' items in generation 0')
	
	if not batch.exists_batch():
		print('Setting batch for generation 0')
		batch_response = batch.set_batch(list(gen_0_sid))
		
	if batch_response == True:
		status['2a']['start'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)
	else:
		raise Exception('Error setting batch')
		
if status['2a']['finish'] == False:
	# Run the batch
	print('Running batch for generation 0')
	batch_response = batch.run_batch(get_meta_by_scopus)
	if batch_response == False:
		raise Exception('Error running batch')
		
	# If the batch finished on this run, exists_batch will return False
	if batch.exists_batch():
		# Exit gracefully
		print('Finished the current batch run; batch not finished')
		sys.exit(0)
	else:
		print('Finished the batch; moving data and cleaning up')
		# Retrieve the batch results
		gen_0 = batch.retrieve_batch()
		# Write them to a permanent file
		with open(gen_0_outfile, 'w') as writefile:
			json.dump(gen_0, writefile)
		# Clean up the batch output
		batch.clean_batch()
		
		# Finished with step 2a
		status['2a']['finish'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)
			
if status['2b']['start'] == False:
	with open(gen_0_outfile) as readfile:
		gen_0 = json.load(readfile)
	# Extract the SIDs
	gen_0_sid = [paper['sid'] for paper in gen_0]
	gen_n1_sid = {reference for paper in gen_0 
								if 'references' in paper 
							for reference in paper['references']}
	print('Total ' + str(len(gen_n1_sid)) + ' references extracted from generation 0')

	# Remove the SIDs scraped in generation 0
	print('Filtering out generation 0 SIDs')
	gen_n1_sid = {sid for sid in gen_n1_sid if sid not in gen_0_sid}
	print('Done')
	
	# Load the generation 1 SIDs
	print('Filtering out generation 1 SIDs')
	with open(gen_1_outfile) as readfile:
		gen_1 = json.load(readfile)
	gen_1_sid = [paper['sid'] for paper in gen_1]
	# And remove the SIDs scraped in generation 1
	gen_n1_sid = {sid for sid in gen_n1_sid if sid not in gen_1_sid}
	print('Done')

	print(str(len(gen_n1_sid)) + ' new items in generation -1')
	
	# If there are more than 100,000 new items to retrieve, we'll cut things short here
	if len(gen_n1_sid) < 100000:
		if not batch.exists_batch():
			print('Setting batch for generation -1')
			batch_response = batch.set_batch(list(gen_n1_sid))
		else:
			raise Exception('Error setting batch')
		
		if batch_response == True:
			status['2b']['start'] = True
			with open(status_file, 'w') as writefile:
				json.dump(status, writefile)
		else:
			raise Exception('Error setting batch')
	else:
		status['2b']['start'] = True
		stats['2b']['finish'] = True
		
if status['2b']['finish'] == False:
	# Run the batch
	print('Running batch for generation -1')
	batch_response = batch.run_batch(get_meta_by_scopus)
	if batch_response == False:
		raise Exception('Error running batch')
		
	# If the batch finished on this run, exists_batch will return False
	if batch.exists_batch():
		# Exit gracefully
		print('Finished the current batch run; batch not finished')
		sys.exit(0)
	else:
		print('Finished the batch; moving data and cleaning up')
		# Retrieve the batch results
		gen_n1 = batch.retrieve_batch()
		# Write them to a permanent file
		with open(gen_n1_outfile, 'w') as writefile:
			json.dump(gen_n1, writefile)
		# Clean up the batch output
		batch.clean_batch()
		
		# Combine all three generations
		with open(gen_1_outfile) as readfile:
			gen_1 = json.load(readfile)
		with open(gen_0_outfile) as readfile:
			gen_0 = json.load(readfile)
		all_papers = gen_1 + gen_0 + gen_n1
		# And write them to a permanent file
		with open(combined_outfile, 'w') as writefile:
			json.dump(all_papers, writefile)

		print()
		print('Totals:')
		print('Generation +1: ' + str(len(gen_1)))
		print('Generation 0: ' + str(len(gen_0)))
		print('Generation -1: ' + str(len(gen_n1)))
		print('All papers: ' + str(len(all_papers)))
		print()

		# Finished with step 2a
		status['2b']['finish'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)



# Step 3: Load the list of core set DOIs and set metadata appropriately

if status['3']['start'] == False:
	print('Setting core set metadata')

	with open(combined_outfile) as readfile:
		all_papers = json.load(readfile)
	with open(css_dois_file) as readfile:
		core_doi = json.load(readfile)

	for paper in all_papers:
		paper['core'] = (paper['doi'] in core_doi)
	
	with open(combined_outfile, 'w') as writefile:
		json.dump(all_papers, writefile)
	
	core_set = [paper for paper in all_papers if paper['core']]
	print('Core set: ' + str(len(core_set)))
	print()

	# Finished step 3	
	status['3']['start'] = True
	status['3']['finish'] = True
	with open(status_file, 'w') as writefile:
			json.dump(status, writefile)



# Step 4:  Generate a list of 100 entries for validation

if status['4']['start'] == False:
	with open(combined_outfile) as readfile:
		all_papers = json.load(readfile)
	all_papers_sid = {paper['sid'] for paper in all_papers}

	random.seed(1234567)
	sample_papers = random.sample(all_papers_sid, 100)
	print('Validation sample:')
	print(sample_papers)

	# Finished step 4
	status['4']['start'] = True
	status['4']['finish'] = True
	with open(status_file, 'w') as writefile:
			json.dump(status, writefile)

if status['4']['finish'] == True:
	print('Finished with all steps')
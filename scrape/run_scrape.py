# -*- coding: utf-8 -*-
'''
This module uses the functions in the `batch` and `scrape` modules to 
build the dataset.
'''

import batch
import csv
import os
import random
from scrape import *
import sys
import time

# File with the list of generation 1 DOIs
infile = 'gen_1 2015-10-30.csv'
#infile = 'test_dois.csv'

# Files to save the scraped data
gen_1_outfile = 'gen_1.json'
gen_0_outfile = 'gen_0.json'
gen_n1_outfile = 'gen_n1.json'
combined_outfile = 'papers.json'

# File with the DOIs for the core set
css_dois_file = 'css_dois.txt'

print('Run started at ' + time.strftime('%c', time.localtime()))

# Set up a file that tracks the status of the scrape
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
	gen_1_doi = []
	with open(infile) as readfile:
		csvreader = csv.reader(readfile)
		# Skip the header row
		next(csvreader)
		for row in csvreader:
			this_doi = row[0]
			gen_1_doi += [this_doi]
			# The next two lines limit how many DOIs we read, for debugging
	#        if len(gen_1_doi) >= 1:
	#            break

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
	# Run the batch
	print('Running batch for generation +1')
	batch_response = batch.run_batch(get_meta_by_doi)
	if batch_response == False:
		raise Exception('Error running batch')

	# If the batch finished on this run, exists_batch will return False
	if batch.exists_batch():
		# Exit gracefully
		print('Finished the current batch run; batch not finished')
		sys.exit(0)
	else:
		# Retrieve the batch results
		gen_1 = batch.retrieve_batch()
		# Write them to a permanent file
		with open(gen_1_outfile, 'w') as writefile:
			json.dump(gen_1, writefile)
		# Clean up the batch output
		batch.clean_batch()
		
		# Extract the sids and references
		gen_1_sid = [paper['sid'] for paper in gen_1]
		gen_0_sid = []
		for paper in gen_1:
			# Skip papers with missing reference list
			if 'references' not in paper:
				continue
			gen_0_sid += paper['references']
		# Remove all of the SIDs that we've already scraped
		# At the same time, make it a set to remove redundancies
		gen_0_sid = {sid for sid in gen_0_sid if sid not in gen_1_sid}
		
		# Finished with step 1
		status['1']['finish'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)



# Step 2:  Two generation backwards search

if status['2a']['start'] == False:
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
		# Retrieve the batch results
		gen_0 = batch.retrieve_batch()
		# Write them to a permanent file
		with open(gen_0_outfile, 'w') as writefile:
			json.dump(gen_0, writefile)
		# Clean up the batch output
		batch.clean_batch()
		
		# Extract the SIDs
		gen_0_sid = [paper['sid'] for paper in gen_0]
		# Extract the references
		gen_n1_sid = []
		for paper in gen_0:
			# Skip papers with missing reference lists
			if 'references' not in paper:
				continue
			gen_n1_sid = paper['references']
		# Remove all of the SIDs scraped in generation 0
		gen_n1_sid = {sid for sid in gen_n1_sid if sid not in gen_0_sid}
		
		# Get the generation 1 SIDs
		with open(gen_1_outfile) as readfile:
			gen_1 = json.load(readfile)
		gen_1_sid = [paper['sid'] for paper in gen_1]
		# And remove all of the SIDs scraped in generation 1
		gen_n1_sid = {sid for sid in gen_n1_sid if sid not in gen_1_sid}
		
		# Finished with step 2a
		status['2a']['finish'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)
			
if status['2b']['start'] == False:
	print(str(len(gen_0_sid)) + ' items in generation -1')
	
	if not batch.exists_batch():
		print('Setting batch for generation -1')
		batch_response = batch.set_batch(list(gen_n1_sid))
		
	if batch_response == True:
		status['2b']['start'] = True
		with open(status_file, 'w') as writefile:
			json.dump(status, writefile)
	else:
		raise Exception('Error setting batch')
		
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
		readdata = readfile.read()
	core_doi = readdata.split(', ')

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



# Step 4:  Print a list of 100 entries for validation

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
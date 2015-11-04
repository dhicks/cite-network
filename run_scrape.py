# -*- coding: utf-8 -*-
'''
This module uses the functions in the `scrape` module to build the dataset.
'''

import csv
import random
from scrape import *
import time

# File to save the set of scraped data
#max_sources = 20
outfile = 'papers.json'

start_time = time.time()
print('Run started at ' + time.strftime('%c', time.localtime()))


# Step 1:  Define core set and retrieve metadata

# Get the DOIs manually retrieved from Scopus
infile = 'gen_1 2015-10-30.csv'
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
print('Retrieving metadata for generation +1')
gen_1 = []
gen_1_sid = []
gen_0_sid = []
for doi in gen_1_doi:
    # Skip empty DOIs
    if doi == '':
        continue
    # TODO: throttle
    meta = get_meta_by_doi(doi, save_raw=False)
    gen_1 += [meta]
    gen_1_sid += [meta['sid']]
    gen_0_sid += meta['references']
    if len(gen_1) % 25 == 0:
        print(len(gen_1))
# Remove all of the SIDs that we've already scraped
# At the same time, make it a set to remove redundancies
gen_1_sid = set(gen_1_sid)
gen_0_sid = {sid for sid in gen_0_sid if sid not in gen_1_sid}
    


# Step 2:  Two generation backwards search
# TODO: generation 0 already has ~50k items
#  so we'll need a way to break the retrieval into batches of ~10k, 
#  each of which can be run a week apart

print(str(len(gen_0_sid)) + ' items in generation 0')
print('Retrieving metadata for generation 0')
gen_0 = []
gen_n1_sid = []
for sid in gen_0_sid:
    # Skip empty SIDs
    if sid == '':
        continue
    # TODO: throttle
    meta = get_meta_by_scopus(sid, save_raw=False)
    #meta['core'] = False
    gen_0 += [meta]
    gen_n1_sid += meta['references']
    if len(gen_0) % 25 == 0:
        print(len(gen_0))
all_papers = gen_1 + gen_0
all_papers_sid = gen_1_sid | gen_0_sid
gen_n1_sid = {sid for sid in gen_n1_sid if sid not in all_papers_sid}

print(str(len(gen_n1_sid)) + ' items in generation -1')
print('Retrieving metadata for generation -1')
gen_n1 = []
# Swap comments on the next two lines to grab only a subset of generation -1
for sid in gen_n1_sid:
#for sid in list(gen_n1_sid)[:100]:
    # Skip empty SIDs
    if sid == '':
        continue
    # TODO: throttle
    meta = get_meta_by_scopus(sid, save_raw=False)
    #meta['core'] = False
    gen_n1 += [meta]
    if len(gen_n1) % 25 == 0:
        print(len(gen_n1))
all_papers = all_papers + gen_n1
all_papers_sid = all_papers_sid | gen_n1_sid


print()
print('Totals:')
print('Generation +1: ' + str(len(gen_1)))
print('Generation 0: ' + str(len(gen_0)))
print('Generation -1: ' + str(len(gen_n1)))
print('All papers: ' + str(len(all_papers)))
print()



# Step 3: Load the list of core set DOIs and set metadata appropriately

infile = 'css_dois.txt'
with open(infile) as readfile:
	readdata = readfile.read()
core_doi = readdata.split(', ')

for paper in all_papers:
	paper['core'] = (paper['doi'] in core_doi)
	
core_set = [paper for paper in all_papers if paper['core']]
print('Core set: ' + str(len(core_set)))
print()



# Step 4:  Write everything into a json file
# TODO: for memory management reasons, save raw xml separately from everything else
with open(outfile, 'w') as out:
    json.dump(all_papers, out)

finish_time = time.time()
print('Run ended at ' + time.strftime('%c', time.localtime()))
print('Total run time ' + str((finish_time - start_time) / 60) + ' minutes')
print()



# Step 5:  Print a list of 100 entries for validation

random.seed(1234567)
sample_papers = random.sample(all_papers_sid, 100)
print('Validation sample:')
print(sample_papers)
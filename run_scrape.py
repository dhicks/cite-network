# -*- coding: utf-8 -*-
'''
This module uses the functions in the `scrape` module to build the dataset.
'''

from scrape import *
import time

# File to save the set of scraped data
max_sources = 20
outfile = 'papers.json'


start_time = time.time()

# Step 1:  Define core set and retrieve metadata

#core_doi = set(['10.1007/978-1-61779-170-3_23'])
#core_doi = set(['10.1016/j.ntt.2009.06.005', '10.1016/j.neuro.2010.04.001', '10.1007/978-1-61779-170-3_23'])
core_doi = ['10.14573/altex.2012.2.202', '10.1016/j.reprotox.2011.11.111', '10.14573/altex.2011.1.009', '10.1016/j.neuro.2012.05.012', '10.1016/j.neuro.2012.10.013', '10.1016/j.taap.2011.02.013', '10.1016/j.tiv.2010.10.011', '10.1016/j.pbb.2012.12.010', '10.1016/j.neuro.2013.02.006', '10.1016/j.neuro.2013.11.008', '10.1002/9781118102138.ch12', '10.1016/j.neuro.2012.05.001', '10.3389/fneng.2011.00004', '10.1016/B978-0-12-382032-7.10015-3', '10.3389/fneng.2011.00001', '10.1016/j.neuro.2014.06.012', '10.1093/toxsci/kfr185', '10.1016/j.ntt.2011.06.007', '10.1016/j.neuro.2008.02.011', '10.1093/toxsci/kfn114', '10.1093/toxsci/kfn115', '10.1016/j.ntt.2009.06.003', '10.1016/j.tox.2010.02.004', '10.1016/j.neuro.2010.02.003', '10.1016/j.ntt.2009.06.005', '10.1016/j.neuro.2010.04.001', '10.1007/978-1-61779-170-3_23', '10.1111/j.1741-4520.2012.00377.x', '10.1002/stem.1201', '10.1016/j.neuro.2008.09.011', '10.1016/j.ntt.2009.04.066', '10.1016/j.ntt.2009.04.065', '10.1016/j.aquatox.2011.05.017', '10.1016/j.ntt.2011.08.005']

print(str(len(core_doi)) + ' items in core set')
print('Retrieving metadata for core set')
core = []
ancestors_sid = []
for doi in core_doi:
    # TODO: throttle
    meta = get_meta_by_doi(doi, save_raw=False)
    meta['core'] = True
    core += [meta]
    ancestors_sid += meta['references']
    if len(core) % 25 == 0:
        print(len(core))
ancestors_sid = set(ancestors_sid)
    

# Step 2:  One generation backwards search

print(str(len(ancestors_sid)) + ' items in ancestors')
print('Retrieving metadata for ancestors')
ancestors = []
for sid in ancestors_sid:
    # TODO: throttle
    meta = get_meta_by_scopus(sid, save_raw=False)
    meta['core'] = False
    ancestors += [meta]
    if len(ancestors) % 25 == 0:
        print(len(ancestors))

core_ancestors = core + ancestors

print()
print('Totals:')
print('Core set: ' + str(len(core)))
print('Ancestors: ' + str(len(ancestors)))
print()


# Step 3:  Get complete list of sources
# Get the sources as a dict, with the number of entries in core_ancestores
print('Collating sources')
sources = {}
for paper in core_ancestors:
    this_source = paper['source']
    if type(this_source) is list:
        # Some papers have a list of variant ISBNs, not a single number
        this_source = this_source[0]
    if this_source not in sources:
        sources[this_source] = 1
    else:
        sources[this_source] = +1
print(str(len(sources)) + ' distinct sources')

# Sort by number of entries
sorted_sources = sorted(sources, key=sources.get, reverse=True)
# Drop the empty value
sorted_sources.remove('')
# And subset to the desired number of sources
target_sources = sorted_sources[:max_sources]

print('Target sources cover ' + 
    str(
        round(
        sum([sources[source] for source in sources if source in target_sources])/
        sum([sources[source] for source in sources]) * 100
        )) +
    '% of core and ancestors')
    



# Step 4:  Get all articles in sources for 2010-2015

print('Getting PubMed IDs for target sources')
extended_set_pmids = []
for source in target_sources:
    # PLoS One is too big
    # TODO: note exclusion of PLoS One from network
    if source == '19326203':
        continue
    # Internal to this loop, new_pmids contains the PubMed IDs for an individual source
    new_pmids = get_pmids_by_issn(source)
    extended_set_pmids += new_pmids
core_ancestor_pmids = []
for paper in core_ancestors:
    core_ancestor_pmids += [paper['pmid']]
# NB After the next line, new_pmids contains the PubMed IDs for which we don't already have metadata
new_pmids = set(extended_set_pmids) - set(core_ancestor_pmids)
print('Total ' + str(len(new_pmids)) + ' new items')
print()


# Step 5:  Get metadata for everything in new_pmids

extended_set = []
for pmid in list(new_pmids)[:1000]:
#for pmid in new_pmids:
    # TODO: throttle
    meta = get_meta_by_pmid(pmid, save_raw=False)
    meta['core'] = False
    extended_set += [meta]
    if len(extended_set) % 100 == 0:
        print(len(extended_set))


# Step 6:  Write everything into a json file
# TODO: for memory management reasons, save raw xml separately from everything else
all_papers = core_ancestors + extended_set
with open(outfile, 'w') as out:
    json.dump(all_papers, out)

finish_time = time.time()
print('total run time ' + str((finish_time - start_time) / 60) + ' minutes')
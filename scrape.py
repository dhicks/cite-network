# -*- coding: utf-8 -*-
import requests
import json
from math import ceil
import xmltodict
import time

MY_API_KEY = '1f271dd2cf40387ab1d7e4645d36f599'
#MY_API_KEY = '6492f9c867ddf3e84baa10b5971e3e3d'

# Metadata to gather:  DOI, Scopus ID, author IDs, source ID, references

def get_meta_by_doi(doi):
    '''
    Retrieve metadata for a single paper from Scopus given its DOI
    :param doi: The paper's DOI
    :return: A dict of metadata:
        'doi': The paper's DOI
        'sid': The paper's Scopus ID
        'authors': The paper's authors, as a list of Scopus author IDs
        'source': The journal, etc., the paper was published in, as a Scopus source ID
        'references': The paper's references, as a list of Scopus IDs
        'raw': The raw XML response from the server
    '''
    #print 'getting metadata for DOI ' + doi
    # Build the http query, and send it using `requests`
    base_query = 'http://api.elsevier.com/content/abstract/doi/'
    query = base_query + doi + '?' + 'apiKey=' + MY_API_KEY
    response_raw = requests.get(query, headers = {'X-ELS-APIKey': MY_API_KEY})
    #print 'received response'
    # Convert the xml response to a dict to make it easier to parse
    response = xmltodict.parse(response_raw.text)
    #print 'parsed to dict'
    # Set default values in case of missing data
    doi = ''
    sid = ''
    authors = []
    source = ''
    refs = []
    try:
        # The locations of these metadata are given in the Scopus XML documentation
        # http://ebrp.elsevier.com/pdf/Scopus_Custom_Data_Documentation_v4.pdf
        # The content for `dc:identifier` looks something like 'Scopus:115628'
        sid = response['abstracts-retrieval-response']['coredata']['dc:identifier']
        sid = sid.split(':')[1]
        #print sid
        # `authors_resp` grabs a list of dicts, one for each author
        # We're only grabbing the Scoupus ID for each one.  
        authors = []
        authors_resp = response['abstracts-retrieval-response']['authors']['author']
        #return authors_resp
        for author in authors_resp:
            authors += [author['@auid']]
        #print authors
        if 'prism:isbn' in response['abstracts-retrieval-response']['coredata']:
            source = response['abstracts-retrieval-response']['coredata']['prism:isbn']
        else:
            source = response['abstracts-retrieval-response']['coredata']['prism:issn']
        #print source
        # The references work like the authors list
        refs = []
        if response['abstracts-retrieval-response']['item']['bibrecord']['tail'] is not None:
            refs_response = response['abstracts-retrieval-response']['item']['bibrecord']['tail']['bibliography']['reference']
            for ref in refs_response:
                refs += [ref['ref-info']['refd-itemidlist']['itemid']['#text']]
        #print refs
    except KeyError:
        # If a field is missing, the dict replies with a KeyError.
        # We've defined empty defaults above the try statement, so if we catch 
        # a KeyError we'll just stop and send back whatever we've gotten so far.
        # This isn't the most elegant want to handle missing fields, since 
        # one missing field early on (say, sid) causes everything to be empty.
        # TODO: handle missing data better
        pass
    finally:
        return {'doi': doi, 'sid': sid, 'authors': authors, 'source': source, 'references': refs, 'raw': response_raw.text}

def get_meta_by_scopus(sid):
    '''
    Retrieve metadata for a single paper from Scopus given its Scopus ID
    :param sid: The paper's Scopus ID
    :return: A dict of metadata:
        'doi': The paper's DOI
        'sid': The paper's Scopus ID
        'authors': The paper's authors, as a list of Scopus author IDs
        'source': The journal, etc., the paper was published in, as a Scopus source ID
        'references': The paper's references, as a list of Scopus IDs
        'raw': The raw XML response from the server
    '''
    # This function should work pretty much just like `get_meta_by_doi`.  
    # And I'm too lazy to copy and paste the documentation from there to here.
    #print 'getting metadata for Scopus ID ' + sid
    base_query = 'http://api.elsevier.com/content/abstract/scopus_id/'
    query = base_query + sid + '?' + 'apiKey=' + MY_API_KEY
    response_raw = requests.get(query, headers = {'X-ELS-APIKey': MY_API_KEY})
    #print 'received response'
    response = xmltodict.parse(response_raw.text)
    #print 'parsed to dict'
    # return response
    # Set default values in case of missing data
    doi = ''
    sid = ''
    authors = []
    source = ''
    refs = []
    try:
        doi = response['abstracts-retrieval-response']['coredata']['prism:doi']
        #print doi
        authors = []
        authors_resp = response['abstracts-retrieval-response']['authors']['author']
        #return authors_resp
        for author in authors_resp:
            authors += [author['@auid']]
        #print authors
        if 'prism:isbn' in response['abstracts-retrieval-response']['coredata']:
            source = response['abstracts-retrieval-response']['coredata']['prism:isbn']
        else:
            source = response['abstracts-retrieval-response']['coredata']['prism:issn']
        #print source
        refs = []
        if response['abstracts-retrieval-response']['item']['bibrecord']['tail'] is not None:
            refs_response = response['abstracts-retrieval-response']['item']['bibrecord']['tail']['bibliography']['reference']
            for ref in refs_response:
                refs += [ref['ref-info']['refd-itemidlist']['itemid']['#text']]
        #print refs
    except KeyError:
        # TODO: Handle missing data better
        pass
    finally:
        return {'doi': doi, 'sid': sid, 'authors': authors, 'source': source, 'references': refs, 'raw': response_raw.text}

def get_dois_by_issn(issn, after = '2004', before = '2016'):
    # TODO: replace with the pubmed version from temp.py
    '''
    Retrieve DOIs for every article published in the source with the given ISSN
    :param issn: The source's ISSN
    :param after: Lower bound (exclusive) on publication year
    :param before: Upper bound (exclusive) on publication year
    
    :return: A list of DOIs
    '''
    max_per_page = 200
    # First search, to get the total number of papers and pages
    base_query = 'http://api.elsevier.com/content/search/scopus?'
    # Search string:  
	# (ISBN(issn) OR ISSN(issn)) AND PUBYEAR > after AND PUBYEAR < before			
    search_string = ('query=' + 
        '(' + 
            'ISBN(' + issn + ')' + '%20OR%20' + 
            'ISSN(' + issn + ')' #+ 
        ')' + '%20AND%20' + 
        'PUBYEAR%20%3E%20' + after + '%20AND%20' + 
        'PUBYEAR%20%3C%20' + before
        )
    query = (base_query + search_string + '&' +
                # We only need the DOI
                'field=doi' + '&' + 
                'httpAccept=application%2Fjson' + '&' +
                'apiKey=' + MY_API_KEY)
    response_raw = requests.get(query + '&count=1')
    response = json.loads(response_raw.text)
    try:
        total_papers = int(response['search-results']['opensearch:totalResults'])
    except KeyError:
        print(issn)
        raise
    total_pages = ceil(total_papers / max_per_page)
    #return(total_pages)
    dois = []
    for page in range(total_pages):
        start_at = max_per_page * page
        this_query = (query + '&' + 
                            'start=' + str(start_at) + '&' +
                            'count=' + str(max_per_page))
        #print(this_query)
        response_raw = requests.get(this_query)
        response = json.loads(response_raw.text)
        for entry in response['search-results']['entry']:
            dois += [entry['prism:doi']]
    if len(dois) != total_papers:
        raise ValueError("Number of DOIs retrieved doesn't match total_papers")
    return(dois)


start_time = time.time()

# Step 1:  Define core set and retrieve metadata

gen_0_doi = set(['10.1016/j.ntt.2009.06.005', '10.1016/j.neuro.2010.04.001', '10.1007/978-1-61779-170-3_23'])
#gen_0_doi = set(['10.1007/978-1-61779-170-3_23'])

print(str(len(gen_0_doi)) + ' items in generation 0')
print('Retrieving metadata for generation 0')
gen_0 = []
gen_n1_sid = []
for doi in gen_0_doi:
    meta = get_meta_by_doi(doi)
    meta['core'] = True
    gen_0 += [meta]
    gen_n1_sid += meta['references']
    if len(gen_0) % 25 == 0:
        print(len(gen_0))
gen_n1_sid = set(gen_n1_sid)
    

# Step 2:  Two generations of backwards search

print(str(len(gen_n1_sid)) + ' items in generation -1')
print('Retrieving metadata for generation -1')
gen_n1 = []
gen_n2_sid = []
for sid in gen_n1_sid:
    meta = get_meta_by_scopus(sid)
    meta['core'] = False
    gen_n1 += [meta]
    gen_n2_sid += meta['references']
    if len(gen_n1) % 25 == 0:
        print(len(gen_n1))
gen_n2_sid = set(gen_n2_sid)

print(str(len(gen_n2_sid)) + ' items in generation -2')
gen_n2 = []
#print('Retrieving metadata for generation -2')
#for sid in gen_n2_sid:
#    meta = get_meta_by_scopus(sid)
#    meta['core'] = False
#    gen_n2 += [meta]
#    if len(gen_n2) % 100 == 0:
#        print(len(gen_n2))

core_ancestors = gen_0 + gen_n1 + gen_n2

print()
print('Totals for core set and ancestors:')
print('Gen 0: ' + str(len(gen_0)))
print('Gen -1: ' + str(len(gen_n1)))
print('Gen -2: ' + str(len(gen_n2)))
print()


# Step 3:  Get complete list of sources
print('Collating sources for core set and ancestors:')
sources = []
for paper in core_ancestors:
#for paper in papers:
    this_source = paper['source']
    if type(this_source) is str:
        sources += [this_source]
    if type(this_source) is list:
        # Some papers have a list of variant ISBNs rather than a single number
        sources += [this_source[0]]
sources = set(sources)
print(str(len(sources)) + ' distinct sources')


# Step 4:  Get all articles in sources for 2005-2015

print('Getting DOIs for each source')
extended_set_dois = []
for source in sources:
    new_dois = get_dois_by_issn(source)
    extended_set_dois += new_dois
core_ancestor_dois = []
for paper in core_ancestors:
    core_ancestor_dois += [paper['doi']]
new_dois = set(extended_set_dois) - set(core_ancestor_dois)


# Step 5:  Write everything into a json file
# TODO: for memory management reasons, save raw xml separately from everything else
all_papers = gen_0 + gen_n1 + gen_n2
outfile = 'papers.json'
with open(outfile, 'w') as out:
    json.dump(all_papers, out)

finish_time = time.time()
print('total run time ' + str((finish_time - start_time) / 60) + ' minutes')
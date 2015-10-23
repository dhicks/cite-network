# -*- coding: utf-8 -*-
from collections import OrderedDict
import requests
import json
#from math import ceil
import xmltodict
import time

MY_API_KEY = '1f271dd2cf40387ab1d7e4645d36f599'
#MY_API_KEY = '6492f9c867ddf3e84baa10b5971e3e3d'

# TODO: handle timeouts exception ReadTimeout

def _parse_scopus_metadata(response_raw):
    '''
    Given the requests.response, parse the XML metadata.
    Metadata to gather:  DOI, Scopus ID, author IDs, source ID, references.
    '''
    # Convert the xml response to a dict to make it easier to parse
    response = xmltodict.parse(response_raw.text)
    #print 'parsed to dict'
    # The locations of these metadata are given in the Scopus XML documentation
    # http://ebrp.elsevier.com/pdf/Scopus_Custom_Data_Documentation_v4.pdf
    # If a field is missing, the dict raises a KeyError or TypeError ('NoneType' object is not subscriptable), and so we use a blank instead
    try:
        doi = response['abstracts-retrieval-response']['coredata']['prism:doi']
    except KeyError:
        doi = ''
    #print doi
    try:
        # The content for `dc:identifier` looks something like 'Scopus:115628'        
        sid = response['abstracts-retrieval-response']['coredata']['dc:identifier']
        sid = sid.split(':')[1]
        #print sid
    except KeyError:
        sid = ''
    #print sid
    try:
        pmid = response['abstracts-retrieval-response']['coredata']['pubmed-id']
    except KeyError:
        pmid = ''
    try:
        authors = []
        authors_resp = response['abstracts-retrieval-response']['authors']['author']
        # If there's only one <author>, xmltodict parses the contents to an OrderedDict
        if type(authors_resp) is OrderedDict:
            authors += [authors_resp['@auid']]
        # But if there are several <author>s, xmltodict produces a list of 
        #    OrderedDicts, one for each author
        elif type(authors_resp) is list:
            for author in authors_resp:
                #print(author['@auid'])
                authors += [author['@auid']]
        else:
            raise ValueError('Problem parsing authors for doi ' + doi)
    except KeyError:
        authors = []
    #print authors
    try:
        if 'prism:isbn' in response['abstracts-retrieval-response']['coredata']:
            source = response['abstracts-retrieval-response']['coredata']['prism:isbn']
        else:
            source = response['abstracts-retrieval-response']['coredata']['prism:issn']
    except KeyError:
        source = ''
    #print source
    try:
        refs_response = response['abstracts-retrieval-response']['item']['bibrecord']['tail']['bibliography']['reference']
        refs = []
        for ref in refs_response:
            refs += [ref['ref-info']['refd-itemidlist']['itemid']['#text']]
    except KeyError:
        refs = []
    except TypeError:
        refs = []
    #print refs
    return {'doi': doi, 'sid': sid, 'pmid': pmid, 'authors': authors, 
                'source': source, 'references': refs}


def get_meta_by_doi(doi, save_raw = True):
    '''
    Retrieve metadata for a single paper from Scopus given its DOI
    :param doi: The paper's DOI
    :return: A dict of metadata:
        'doi': The paper's DOI
        'sid': The paper's Scopus ID
        'pmid': The paper's PubMed ID
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
    # Send the result to the parser    
    meta = _parse_scopus_metadata(response_raw)
    # If the call asks us to save the raw response, do so; otherwise add a blank
    if save_raw:
        meta['raw'] = response_raw.text
    else:
        meta['raw'] = ''
    return meta

def get_meta_by_scopus(sid, save_raw = True):
    '''
    Retrieve metadata for a single paper from Scopus given its Scopus ID
    :param sid: The paper's Scopus ID
    :return: A dict of metadata:
        'doi': The paper's DOI
        'sid': The paper's Scopus ID
        'pmid': The paper's PubMed ID
        'authors': The paper's authors, as a list of Scopus author IDs
        'source': The journal, etc., the paper was published in, as a Scopus source ID
        'references': The paper's references, as a list of Scopus IDs
        'raw': The raw XML response from the server
    '''
    # This works just like get_meta_by_doi 
    base_query = 'http://api.elsevier.com/content/abstract/scopus_id/'
    query = base_query + sid + '?' + 'apiKey=' + MY_API_KEY
    #print(query)
    response_raw = requests.get(query, headers = {'X-ELS-APIKey': MY_API_KEY})
    #print 'received response'
    meta = _parse_scopus_metadata(response_raw)
    if save_raw:
        meta['raw'] = response_raw.text
    else:
        meta['raw'] = ''
    return meta

                
def get_meta_by_pmid(pmid, save_raw = True):
    '''
    Retrieve metadata for a single paper from Scopus given its PubMed ID
    :param pmid: The paper's PubMed ID
    :return: A dict of metadata:
        'doi': The paper's DOI
        'sid': The paper's Scopus ID
        'pmid': The paper's PubMed ID
        'authors': The paper's authors, as a list of Scopus author IDs
        'source': The journal, etc., the paper was published in, as a Scopus source ID
        'references': The paper's references, as a list of Scopus IDs
        'raw': The raw XML response from the server
    '''
    base_query = 'http://api.elsevier.com/content/abstract/pubmed_id/'
    query = base_query + pmid + '?' + 'apiKey=' + MY_API_KEY
    response_raw = requests.get(query, headers = {'X-ELS-APIKey': MY_API_KEY})
    #print 'received response'
    meta = _parse_scopus_metadata(response_raw)
    if save_raw:
        meta['raw'] = response_raw.text
    else:
        meta['raw'] = ''
    return meta


def get_pmids_by_issn(issn, since = '2010', until = '2015'):
    '''
    Use a PubMed query to retrieve the list of every item published in the given source
    :param issn: The source's ISSN
    :param since: Lower bound (exclusive) on publication year
    :param until: Upper bound (exclusive) on publication year
    
    :return: A list of PubMed IDs
    '''
    # First deal with a degenerate case
    if issn == '':
        return([])
    # Build the PubMed query
    # Start with the base URL of the API
    base_query = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?'
    # Build the search string.  
    # Note that PubMed expects ISSNs with the form NNNN-NNNN
    # TODO: handle ISBNs
    if len(issn) != 8:
        return([])
    search_string = ('term=' + issn[:4] + '-' + issn[4:] + '&' + 
        'field=journal' + '&' + 
        'mindate=' + since + '&' +
        'maxdate=' + until)
    retmax = 100000    # Max no. of items to return; PubMed's max is 100k
    query = (base_query + 'retmax=' + str(retmax) + '&' + 
                # Get the results in json
                'retmode=json' + '&' +
                search_string)
    try:
        # Send the request and turn it into json
        response_raw = requests.get(query)
        response = json.loads(response_raw.text)
        # Get the total number of items
        total_papers = int(response['esearchresult']['count'])
    except:
        # If there's an error, output the query for debugging and pass on the error
        print(query)
        raise
    # Update stdout
    print('found ' + str(total_papers) + ' items for source ' + issn)
    # This function assumes we can get everything on one page. 
    # Raise an error if this isn't the case. 
    if total_papers > retmax:
        raise ValueError('more items than PubMed can return on one page')
    pmids = response['esearchresult']['idlist']
    return(pmids)

# The following lines retrieve the DOI for each PubMed ID
# But we need to get the citation data from Scopus anyways, so don't bother with this
#    max_per_page = 250
#    total_pages = ceil(total_papers / max_per_page)
#    base_query = ('http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?' +
#        'db=pubmed' + '&' + 'retmode=json' + '&' + 'retmax=' + str(max_per_page))
#    dois = []
#    for page in range(total_pages):
#        try:    
#            these_pmids = pmids[page * max_per_page : (page+1) * max_per_page]
#            response_raw = requests.post(base_query, {'id': ','.join(these_pmids)})
#            response = json.loads(response_raw.text)
#            articles = response['result']
#            for pmid in these_pmids:
#                article = articles[pmid]
#                for this_id in article['articleids']:
#                    if this_id['idtype'] == 'doi':
#                        dois += [this_id['value']]
#                        break
#            if len(dois) % 100 == 0:
#                print(len(dois))
#        except:
#            print(page)
#            print(response_raw.text)
#            raise
#    return(dois)


start_time = time.time()

# Step 1:  Define core set and retrieve metadata

core_doi = set(['10.1016/j.ntt.2009.06.005', '10.1016/j.neuro.2010.04.001', '10.1007/978-1-61779-170-3_23'])
#core_doi = set(['10.1007/978-1-61779-170-3_23'])

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
print('Collating sources')
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
print()


# Step 4:  Get all articles in sources for 2010-2015

print('Getting PubMed IDs for each source')
extended_set_pmids = []
for source in sources:
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
    if len(extended_set) % 300 == 0:
        print(len(extended_set))


# Step 6:  Write everything into a json file
# TODO: for memory management reasons, save raw xml separately from everything else
all_papers = core_ancestors + extended_set
outfile = 'papers.json'
with open(outfile, 'w') as out:
    json.dump(all_papers, out)

finish_time = time.time()
print('total run time ' + str((finish_time - start_time) / 60) + ' minutes')
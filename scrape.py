# -*- coding: utf-8 -*-
'''
This module defines several functions used to scrape article metadata, 
primarily from Scopus but also from PubMed.  

Note that these functions need a Scopus API key, defined in `api_key.py`.
'''

from collections import OrderedDict
import requests
import json
#from math import ceil
import time
import xmltodict

from api_key import MY_API_KEY

def _parse_scopus_metadata(response_raw):
    '''
    Given the requests.response, parse the XML metadata.
    Metadata to gather:  DOI, Scopus ID, author IDs, source ID, references.
    :param response_raw: XML metadata, retrieved from Scopus using requests.get
    :return: A dict of metadata:
        'doi': The paper's DOI
        'sid': The paper's Scopus ID
        'pmid': The paper's PubMed ID
        'authors': The paper's authors, as a list of Scopus author IDs
        'source': The journal, etc., the paper was published in, as a Scopus source ID
        'year': The publication year
        'references': The paper's references, as a list of Scopus IDs
        'raw': The raw XML response from the server
    '''
    # Convert the xml response to a dict to make it easier to parse
    response = xmltodict.parse(response_raw.text)
    #print 'parsed to dict'
    # This branch catches error codes in the response
    if 'service-error' in response:
        # If the resource isn't found, we'll just get a bunch of key errors and can return an empty set of metadata
        if response['service-error']['status']['statusCode'] == 'RESOURCE_NOT_FOUND':
            print('Resource not found error')
        # If something else is going on, raise an exception
        else:
            print(response)
            raise ValueError('Service error in query response')
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
    except TypeError:
        authors = []
        #raise ValueError('Problem parsing authors for doi ' + doi)
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
    	year = response['abstracts-retrieval-response']['item']['bibrecord']['head']['source']['publicationyear']['@first']
    	year = int(year)
    	#print(year)
    except KeyError:
    	print(response['abstracts-retrieval-response']['item']['bibrecord']['head']['source']['publicationyear'])
    	year = None
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
                'source': source, 'year': year, 'references': refs}
                
def _get_query(query):
    '''
    Get an HTTP query, with some wrapping to handle timeouts.
    :param query: The HTTP query string
    :return: The requests.get response
    '''
    # Timeout for HTTP requests
    TIMEOUT = 60
    # Delay, in seconds, after receiving a timeout
    DELAY = 3*60
    # Maximum number of attempts to make before throwing an error
    MAX_ATTEMPTS = 5
    
    attempts = 0
    while (attempts < MAX_ATTEMPTS):
        attempts += 1
        try:
            response_raw = requests.get(query, 
                            #headers = {'X-ELS-APIKey': MY_API_KEY}, 
                            timeout = TIMEOUT)
            return(response_raw)
        except requests.exceptions.Timeout:
            print('Request timed out.  Cooldown for ' + str(DELAY) + ' seconds.')
            time.sleep(DELAY)
    else:
        raise requests.exceptions.Timeout('Maximum number of requests')
    


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
    print('\t' + query)
    response_raw = _get_query(query)
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
    print('\t' + query)
    response_raw = _get_query(query)
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
    print('\t' + query)
    response_raw = _get_query(query)
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
    print('\t' + query)
    try:
        response_raw = _get_query(query)
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



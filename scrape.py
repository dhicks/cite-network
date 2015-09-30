import requests
import json
import xmltodict
MY_API_KEY = '1f271dd2cf40387ab1d7e4645d36f599'#'6492f9c867ddf3e84baa10b5971e3e3d'#

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
    '''
    #print 'getting metadata for DOI ' + doi
    base_query = 'http://api.elsevier.com/content/abstract/doi/'
    query = base_query + doi + '?' + 'apiKey=' + MY_API_KEY
    response = requests.get(query, headers = {'X-ELS-APIKey': MY_API_KEY})
    #print 'received response'
    response = xmltodict.parse(response.text)
    #print 'parsed to dict'
    # return response
    # Set default values in case of missing data
    doi = ''
    authors = []
    source = ''
    refs = []
    try:
        sid = response['abstracts-retrieval-response']['coredata']['dc:identifier']
        sid = sid.split(':')[1]
        #print sid
        authors = []
        authors_resp = response['abstracts-retrieval-response']['authors']['author']
        #return authors_resp
        for author in authors_resp:
            authors += [author['@auid']]
        #print authors
        source = response['abstracts-retrieval-response']['coredata']['source-id']
        #print source
        refs = []
        if response['abstracts-retrieval-response']['item']['bibrecord']['tail'] is not None:
            refs_response = response['abstracts-retrieval-response']['item']['bibrecord']['tail']['bibliography']['reference']
            for ref in refs_response:
                refs += [ref['ref-info']['refd-itemidlist']['itemid']['#text']]
        #print refs
    except KeyError:
        pass
    finally:
        return {'doi': doi, 'sid': sid, 'authors': authors, 'source': source, 'references': refs}

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
    '''
    #print 'getting metadata for Scopus ID ' + sid
    base_query = 'http://api.elsevier.com/content/abstract/scopus_id/'
    query = base_query + sid + '?' + 'apiKey=' + MY_API_KEY
    response = requests.get(query, headers = {'X-ELS-APIKey': MY_API_KEY})
    #print 'received response'
    response = xmltodict.parse(response.text)
    #print 'parsed to dict'
    # return response
    # Set default values in case of missing data
    doi = ''
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
        source = response['abstracts-retrieval-response']['coredata']['source-id']
        #print source
        refs = []
        if response['abstracts-retrieval-response']['item']['bibrecord']['tail'] is not None:
            refs_response = response['abstracts-retrieval-response']['item']['bibrecord']['tail']['bibliography']['reference']
            for ref in refs_response:
                refs += [ref['ref-info']['refd-itemidlist']['itemid']['#text']]
        #print refs
    except KeyError:
        pass
    finally:
        return {'doi': doi, 'sid': sid, 'authors': authors, 'source': source, 'references': refs}


# TODO: forward citation search doesn't seem to be working

gen_0_doi = ['10.1007/978-1-61779-170-3_23']

print 'Retrieving metadata for generation 0'
gen_0 = []
gen_n1_sid = []
for doi in gen_0_doi:
    meta = get_meta_by_doi(doi)
    gen_0 += [meta]
    gen_n1_sid += meta['references']

# TODO: retrieve publications from sources for 2005-2015
sources = []
for paper in gen_0:
    sources += [paper['source']]
print sources

print 'Retrieving metadata for generation -1'
gen_n1 = []
gen_n2_sid = []
for sid in gen_n1_sid:
    print sid
    meta = get_meta_by_scopus(sid)
    gen_n1 += [meta]
    gen_n2_sid += meta['references']

print 'Generation 0 papers: ' + str(len(gen_0))
print 'Generation -1 papers: ' + str(len(gen_n1))
print 'Generation -2 papers: ' + str(len(gen_n2_sid))

# TODO: build citation network
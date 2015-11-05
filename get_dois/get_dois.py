# -*- coding: utf-8 -*-
"""
Created on Fri Oct 30 14:05:59 2015

@author: dhicks1
"""

#import xml.etree.ElementTree as ET
import xmltodict

infile = 'CSS_Publications_Library-June 2015.xml'
outfile = 'css_dois.txt'
search_string_outfile = 'css_search.txt'

# Open the XML export of the Endnote file
with open(infile, 'r') as readfile:
    readdata = readfile.read()
# Parse the XML to a dict
data = xmltodict.parse(readdata)
# Jump down a couple of levels to the actual records
records = data['xml']['records']['record']

# Initialize list to hold the DOIs and a counter for the errors
dois = []
errors = 0
for record in records:
    try:
        # The DOI is stored as 'http://dx.doi.org/10.555/blah.blah.blah'
        doi_string = record['electronic-resource-num']['style']['#text']
        if 'http' in doi_string:
            doi = doi_string.split('http://dx.doi.org/')[1]
        else:
            doi = doi_string
        print(doi)
        dois += [doi]
    except KeyError:
        # A KeyError is raised if the record wasn't exported with a DOI 
        # (at least, where we're expecting to find the DOI)
        errors += 1
print('Found ' + str(len(dois)) + ' DOIs')
print(str(errors) + ' errors')

# Write the DOIs to a file, as a comma-separated list
with open(outfile, 'w') as writefile:
    writefile.write(', '.join(dois))

# Wrap the DOIs in the Scopus DOI search operator
dois_search = ['DOI(' + doi + ')' for doi in dois]
# Then write them to a file, conjoined with OR
# We should be able to copy-and-paste the query into Scopus advanced search: 
# http://www-scopus-com/search/form.url?zone=TopNavBar&origin=searchadvanced
with open(search_string_outfile, 'w') as writefile:
    writefile.write(' OR '.join(dois_search))
    
'''
After running the script above:  
* Open `css_search.txt`.  Copy and paste the search string into Scopus advanced search:  
    http://www-scopus-com/search/form.url?zone=TopNavBar&origin=searchadvanced
    
* Scopus returns 174 results. 

* In the search results page, select "Select All", then "View Cited By". 

* Scopus returns 911 results.  

* Select "Export" > "CSV" and "Specify fields to be exported" > "DOI" only, then "Export".

* Exported file saved as `gen_1 2015-10-30.csv`.  
'''
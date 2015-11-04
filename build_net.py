# -*- coding: utf-8 -*-
'''
This module uses the dataset built by `run_scrape` to build a citation 
network in GEXF format. 
'''

import json
import networkx as nx
# TODO: for efficiency reasons, consider rewriting this in graph-tool:  
# https://graph-tool.skewed.de/

# The json file with the dataset output from `run_scrape`
infile = 'papers.json'


# Step 1:  Read json file
print('Reading dataset')
with open(infile, 'r') as inread:
    all_papers = json.load(inread)
   
print('Cleaning dataset')
# If the Scopus ID is empty, we don't actually have any metadata on it;
# Drop it from the set of all papers
papers_working = [paper for paper in all_papers if paper['sid'] != '']

# Add an internal ID to each paper
counter = -1
id_from_sid = {}
for paper in papers_working:
    counter += 1
    paper['id'] = counter
    # id_from_sid provides a quick lookup of internal id
    id_from_sid[paper['sid']] = paper['id'] 


# Step 2:  Build citation network
print('Building citation network')
citenet = nx.DiGraph()
citenet.clear()

for paper in papers_working:
    # Define nodes by internal id
    this_node = paper['id']
    # Write metadata to note using the functionality of DiGraph.add_node
    # NB access node attributes using citenet.node[n], not citenet[n]
    citenet.add_node(this_node, attr_dict=paper)
    # Add **incoming** edges for each bibliography item
    for reference in paper['references']:
        if reference in id_from_sid:
            # If the item already has an internal id, look it up            
            inbound_node = id_from_sid[reference]
        else:
            # If not, we need to give it an ID and add some necessary metadata
            counter += 1
            inbound_node = counter
            id_from_sid[reference] = counter
            citenet.add_node(inbound_node, 
                             attr_dict={'core': False, 
                                        'id': counter, 
                                        'sid': reference,
                                        'source': ''})
        citenet.add_edge(inbound_node, this_node)

print('Extracting core connected components')      
# Drop the weakly connected components that don't include core set items
citenet_comps = set()
#nx.number_weakly_connected_components(citenet)
for citenet_sub in nx.weakly_connected_component_subgraphs(citenet):
    for node in citenet_sub.node:
        if citenet_sub.node[node]['core']:
            citenet_comps.add(citenet_sub)
            continue
citenet_core = nx.compose_all(citenet_comps)
print('Total ' + str(len(citenet_core)) + ' nodes in the citation network')

# Step 3:  Save network to disk
# GEXF doesn't like lists as attributes :-/
writenet = citenet_core.copy()
nx.set_node_attributes(writenet, 'authors', '')
nx.set_node_attributes(writenet, 'references', '')
# Some papers have variant ISBNs in the source field; replace these with their first entry
for node in writenet.node:
    if type(writenet.node[node]['source']) is list:
            writenet.node[node]['source'] = writenet.node[node]['source'][0]

# This chunk is useful for debugging errors due to metadata incompatible w/ GEXF
#for node in writenet.node:
#    this_node = writenet.node[node]
#    for key in this_node:
#        this_type = type(this_node[key])
#        if this_type is not str and this_type is not bool and this_type is not int:
#            print(node)
#            print(key)
#            raise Exception()

outfile = 'citenet.gexf'
print('Writing citation network to ' + outfile)
nx.write_gexf(writenet, 'citenet.gexf')
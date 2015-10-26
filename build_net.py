# -*- coding: utf-8 -*-
'''
This module uses the dataset built by `run_scrape` to build a citation 
network in GEXF format. 
'''

import json
import networkx as nx

# The json file with the dataset output from `run_scrape`
infile = 'papers.json'


# Step 1:  Read json file
with open(infile, 'r') as inread:
    all_papers = json.load(inread)

# Add an internal ID to each paper
counter = -1
id_from_pmid = {}
for paper in all_papers:
    counter += 1
    paper['id'] = counter
    # id_from_pmid provides a quick lookup of internal id
    id_from_pmid[paper['pmid']] = paper['id']    


# Step 2:  Build network
citenet = nx.DiGraph()
citenet.clear()

for paper in all_papers:
    # Define nodes by internal id
    this_node = paper['id']
    # Write metadata to note using the functionality of DiGraph.add_node
    # NB access node attributes using citenet.node[n], not citenet[n]
    citenet.add_node(this_node, attr_dict=paper)
    # Add **incoming** edges for each bibliography item
    for reference in paper['references']:
        if reference in id_from_pmid:
            # If the item already has an internal id, look it up            
            inbound_node = id_from_pmid[reference]
        else:
            # Otherwise give it a new internal id
            counter += 1
            inbound_node = counter
            id_from_pmid[reference] = counter
        citenet.add_edge(inbound_node, this_node)
        
# TODO: use weakly_connected_components to drop the components that don't include the core set


# Step 3:  Save network to disk
# GEXF doesn't like lists as attributes :-/
writenet = citenet.copy()
nx.set_node_attributes(writenet, 'authors', '')
nx.set_node_attributes(writenet, 'references', '')

outfile = 'citenet.gexf'
nx.write_gexf(writenet, 'citenet.gexf')
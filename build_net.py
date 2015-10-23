# -*- coding: utf-8 -*-
import json
import networkx as nx

# Step 1:  Read json file
infile = 'papers.json'
with open(infile, 'r') as inread:
    all_papers = json.load(inread)

# Add an internal ID to each paper
counter = -1
id_from_pmid = {}
for paper in all_papers:
    counter += 1
    paper['id'] = counter
    id_from_pmid[paper['pmid']] = paper['id']    

# Step 2:  Build network
'''
initialize empty network
for each article in the list
    add metadata to node
    for each citation
        add inbound links for each citation
'''

citenet = nx.DiGraph()
citenet.clear()

for paper in all_papers:
    this_node = paper['id']
    # NB access node attributes using citenet.node[n], not citenet[n]
    citenet.add_node(this_node, attr_dict=paper)
    for reference in paper['references']:
        try:
            inbound_node = id_from_pmid[reference]
        except KeyError:
            counter += 1
            inbound_node = counter
            id_from_pmid[reference] = counter
        citenet.add_edge(inbound_node, this_node)
        
# TODO: use weakly_connected_components to drop the components that don't include the core set


# Step 3:  Save network to disk

# GEXF doesn't like lists as attributes
writenet = citenet.copy()
nx.set_node_attributes(writenet, 'authors', '')
nx.set_node_attributes(writenet, 'references', '')

outfile = 'citenet.gexf'
nx.write_gexf(writenet, 'citenet.gexf')
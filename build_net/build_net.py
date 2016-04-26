# -*- coding: utf-8 -*-
'''
Using the metadata retrieved from Scopus, build citation and coauthor networks.  
Each of the resulting `graphml` files contains a single connected network.
'''
import graph_tool as gt
import graph_tool.topology as topo

import json
import os.path as path

# The json file with the dataset output from `run_scrape`
infile = 'papers.json'
# Strings to build graphml file names
citenet_outfile_pre = 'citenet'
autnet_outfile_pre = 'autnet'
outfile_suff = '.graphml'


# Step 1:  Read json file
print('Reading dataset')
with open(infile, 'r') as inread:
    all_papers = json.load(inread)
   
print('Cleaning dataset')
# If the Scopus ID is empty, we don't actually have any metadata on it;
# Drop it from the set of all papers
papers_working = [paper for paper in all_papers if paper['sid'] != '']


# Step 2:  Build citation network

if not path.isfile(citenet_outfile_pre + '0' + outfile_suff):
	print('Building citation network')
	citenet = gt.Graph()
	citenet.set_directed(True)

	# Metadata:  
	#  doi, sid, pmid, authors, source, year, references
	#  core status

	doi = citenet.new_vertex_property('string')
	citenet.vertex_properties['doi'] = doi
	sid = citenet.new_vertex_property('string')
	citenet.vertex_properties['sid'] = sid
	pmid = citenet.new_vertex_property('string')
	citenet.vertex_properties['pmid'] = pmid
	authors = citenet.new_vertex_property('vector<string>')
	citenet.vertex_properties['authors'] = authors
	source = citenet.new_vertex_property('string')
	citenet.vertex_properties['source'] = source
	year = citenet.new_vertex_property('int')
	citenet.vertex_properties['year'] = year
	references = citenet.new_vertex_property('vector<string>')
	citenet.vertex_properties['references'] = references
	core = citenet.new_vertex_property('bool')
	citenet.vertex_properties['core'] = core

	# Define a dict to look up a vertex given its sid
	sid_to_gt = {}

	count = 0
	print(str(len(papers_working)) + ' primary entries in dataset')
	for paper in papers_working:
		# Either add a new vertex to the graph, or retrieve the vertex already added
		if paper['sid'] not in sid_to_gt:
			vertex = citenet.add_vertex()
		else:
			vertex = sid_to_gt[paper['sid']]
	
		# Add the metadata
		doi[vertex] = paper['doi']
		sid[vertex] = paper['sid']
		pmid[vertex] = paper['pmid']
		authors[vertex] = paper['authors']
		source[vertex] = paper['source']
		if paper['year'] is not None:
			year[vertex] = paper['year']
		references[vertex] = paper['references']
		core[vertex] = paper['core']
	
		# Add **incoming** edges for each bibliography item
		for reference in paper['references']:
			if reference in sid_to_gt:
				# If the item already has an internal id, look it up            
				inbound = sid_to_gt[reference]
			else:
				# If not, add it a new vertex
				inbound = citenet.add_vertex()
				# Record which vertex in `sid_to_gt`
				sid_to_gt[reference] = inbound
				# And add its sid to its metadata
				sid[inbound] = reference
			# Now we can add the new edge
			citenet.add_edge(inbound, vertex)

		count += 1
		if count % 1000 == 0:
			print(count)
		
	print('Finished building graph')
	print('Total vertices: ' + str(citenet.num_vertices()))
	print('Total edges: ' + str(citenet.num_edges()))



# Step 3:  Drop the weakly connected components that don't include core set items
	print('Extracting core connected components')      
	# `label_components` returns a property map:  
	#  `component_pmap[vertex]` returns the ID for the component containing vertex
	component_pmap = topo.label_components(citenet, directed = False)[0]
	# Extract a list with the distinct component IDs
	component_list = set(component_pmap[vertex] for vertex in list(citenet.vertices()))
	print(str(len(component_list)) + ' weakly connected components found')

	# Find the vertices from the core set
	core_vertices = [vertex for vertex in list(citenet.vertices()) if core[vertex]]
	print(str(len(core_vertices)) + ' core set members found')
	# Extract a list of the component IDs from the core set members
	core_components = {component_pmap[vertex] for vertex in core_vertices}
	print(str(len(core_components)) + ' components with core set members')
	print(core_components)

	# Construct a list of graphs, one for each core component
	citenets = []
	for component in core_components:
		# Define a new pmap for component membership
		core_comp_pmap = citenet.new_vertex_property('bool')
		for vertex in citenet.vertices():
			core_comp_pmap[vertex] = component_pmap[vertex] == component
		# Use this to filter down to the component
		citenet.set_vertex_filter(core_comp_pmap)
		# Copy it
		temp_graph = gt.Graph(citenet, prune = True)
		# Remove the filter
		citenet.set_vertex_filter(None)
		# If the component isn't empty, add it to the list of graphs
		if temp_graph.num_vertices() > 0:
			citenets += [temp_graph]
			print('Component #' + str(component))
			print('Vertices: ' + str(temp_graph.num_vertices()))
			print('Edges: '	+ str(temp_graph.num_edges()))
		else:
			print(component)


# Step 4:  Save citation network to disk
	print('Saving networks to disk')
	for component in citenets:
		outfile = citenet_outfile_pre + str(citenets.index(component)) + outfile_suff
		component.save(outfile)


# Step 5:  Build coauthor network
print('Building coauthor network')
autnet = gt.Graph()
autnet.set_directed(False)

# Author Metadata:  
#  Scopus author ID
#  sources published in
#  no. of papers in the dataset
#  author of a core set paper
id = autnet.new_vertex_property('string')
autnet.vertex_properties['id'] = id
sources = autnet.new_vertex_property('vector<string>')
autnet.vertex_properties['sources'] = sources
num_papers_v = autnet.new_vertex_property('int')
autnet.vertex_properties['num_papers'] = num_papers_v
core = autnet.new_vertex_property('bool')
autnet.vertex_properties['core'] = core

# Edge Metadata:
#  no. papers coauthored
#    needs to be float since we increment it .5 at a time
num_papers_e = autnet.new_edge_property('float')
autnet.edge_properties['num_papers'] = num_papers_e

# Define a dict to look up a vertex given the author ID
aut_to_gt = {}

count = 0
print(str(len(papers_working)) + ' primary entries in dataset')
for paper in papers_working:
	authors = paper['authors']
	
	# If necessary, add a new vertex to the graph
	for author in authors:
		if author not in aut_to_gt:
			vertex = autnet.add_vertex()
			
			aut_to_gt[author] = vertex
			id[vertex] = author
			sources[vertex] = []
			num_papers_v[vertex] = 0
			core[vertex] = False
	
	# Update the author metadata
	for author in authors:
		vertex = aut_to_gt[author]
		#sources[vertex] = sources[vertex].append(paper['source'])
		num_papers_v[vertex] += 1
		core[vertex] = core[vertex] or paper['core']
	
	# Add edges
	for author1 in authors:
		for author2 in authors:
			# Don't self-link
			if author1 == author2:
				continue
			# If there isn't yet an edge, add a new one
			edge = autnet.edge(aut_to_gt[author1], aut_to_gt[author2], 
								add_missing=False)
			if edge is None:
				edge = autnet.edge(aut_to_gt[author1], aut_to_gt[author2], 
									add_missing=True)
				num_papers_e[edge] = 0
			# Since each author1-author2 appears twice, only add .5 to the weight
			num_papers_e[edge] += 0.5

	count += 1
	if count % 1000 == 0:
		print(count)
		
print('Finished building coauthor graph')
print('Total vertices: ' + str(autnet.num_vertices()))
print('Total edges: ' + str(autnet.num_edges()))


# Step 6: Core connected components for coauthor network
#  This is copied from step 3, with `autnet` for `citenet`
print('Extracting core connected components')
# `label_components` returns a property map:  
#  `component_pmap[vertex]` returns the ID for the component containing vertex
component_pmap = topo.label_components(autnet, directed = False)[0]
# Extract a list with the distinct component IDs
component_list = set(component_pmap[vertex] for vertex in list(autnet.vertices()))
print(str(len(component_list)) + ' weakly connected components found')

# Find the vertices from the core set
core_vertices = [vertex for vertex in list(autnet.vertices()) if core[vertex]]
print(str(len(core_vertices)) + ' core set members found')
# Extract a list of the component IDs from the core set members
core_components = set(component_pmap[vertex] for vertex in core_vertices)
print(str(len(core_components)) + ' components with core set members')
print(core_components)

# Construct a list of graphs, one for each core component
autnets = []
for component in core_components:
	# Define a new pmap for component membership
	core_comp_pmap = autnet.new_vertex_property('bool')
	for vertex in autnet.vertices():
		core_comp_pmap[vertex] = component_pmap[vertex] == component
	# Use this to filter down to the component
	autnet.set_vertex_filter(core_comp_pmap)
	# Copy it
	temp_graph = gt.Graph(autnet, prune = True)
	# Remove the filter
	autnet.set_vertex_filter(None)
	# If the component isn't empty, add it to the list of graphs
	if temp_graph.num_vertices() > 0:
		autnets += [temp_graph]
		print('Component #' + str(component))
		print('Vertices: ' + str(temp_graph.num_vertices()))
		print('Edges: '	+ str(temp_graph.num_edges()))
	else:
		print(component)
		

# Step 4:  Save coauthor network to disk
print('Saving coauthor networks to disk')
for component in autnets:
	outfile = autnet_outfile_pre + str(autnets.index(component)) + outfile_suff
	component.save(outfile)

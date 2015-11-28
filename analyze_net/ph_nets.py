# Networkx
#import networkx as nx
#import community
    # http://perso.crans.org/aynaud/communities/index.html

#import igraph

# Use graph-tool instead
#  https://graph-tool.skewed.de/download#note-macos

import graph_tool as gt
import graph_tool.community as comm

import matplotlib.pyplot as plt

import csv
import numpy as np
import os.path as path
import pickle
from random import sample

phnet_infile = 'cit-HepPh.txt'
ptnet_infile = 'cit-HepTh.txt'

phnet_outfile = 'phnet.graphml'
ptnet_outfile = 'ptnet.graphml'

# If the graphml file doesn't exist, 
if not path.isfile(phnet_outfile):
	# Initialize the empty graph
	phnet = gt.Graph()
	# Add a vertex property with the citation network id
	id = phnet.new_vertex_property('string')
	# And make it internal to the graph
	phnet.vertex_properties['phnet_id'] = id
	# Since gt doesn't provide an efficient way to look up vertices given  
	#  a property value, we'll need a dict to do that
	id_to_gt = {}

	# And parse the graph from `infile`
	with open(phnet_infile) as readfile:
		print('reading ' + phnet_infile)
		phnet_read = csv.reader(readfile, delimiter = '\t')
		count = 0
		for line in phnet_read:
			# Skip commented lines
			if line[0][0] == '#':
				continue
			# Each non-commented line generates a list ['12345', '67890']
			#  Entry 0 is the tail, entry 1 is the head
			#print(line)
			tail_id = line[0]
			head_id = line[1]
			#print(tail_id)
			#print(head_id)
			
			# Check whether the tail is already in the lookup table
			if tail_id in id_to_gt:
				tail = id_to_gt[tail_id]
			else:
				# If not, add it to both the net and lookup table
				tail = phnet.add_vertex()
				id[tail] = tail_id
				id_to_gt[tail_id] = tail
			
			# Likewise with the head
			if head_id in id_to_gt:
				head = id_to_gt[head_id]
			else:
				head = phnet.add_vertex()
				id[head] = head_id
				id_to_gt[head_id] = head
			
			# Add the edge and increase the progress counter
			phnet.add_edge(tail, head)
			# Show an update every nth node
			count += 1
			if count % 10000 == 0:
				print(count)

	print('finished reading ' + phnet_infile)
	# Write it to disk so we don't have to do this again later
	phnet.save(phnet_outfile)
	print('finished saving ' + phnet_outfile)
else:
	print('found saved ' + phnet_outfile)
	# Read the saved network
	phnet = gt.load_graph(phnet_outfile)
	# Since vertices as such can't be pickled, we need to reconstruct 
	#  id and id_to_gt manually
	print('finished reading ' + phnet_outfile)
	id = phnet.vertex_properties['phnet_id']
	id_to_gt = {id[vertex]: vertex for vertex in phnet.vertices()}
	
#print(len(id_to_gt))
print('total vertices: ' + str(phnet.num_vertices()))
print('total edges: ' + str(phnet.num_edges()))


n_samples = 100
samples = []
while len(samples) < n_samples:
	# Generate a random partition
	temp_part = sample(list(id_to_gt), 200)
	#print(temp_part)
	# `modularity` gets the groups as a PropertyMap
	temp_part_pmap = phnet.new_vertex_property('bool')
	for vertex in phnet.vertices():
		temp_part_pmap[vertex] = id[vertex] in temp_part
	#print(comm.modularity(phnet, temp_part_pmap))
	samples += [comm.modularity(phnet, temp_part_pmap)]
print(np.mean(samples))
print(np.std(samples))

n, bins, patches = plt.hist(samples, 50)
plt.show()
import graph_tool as gt
import graph_tool.community as comm

#import matplotlib.pyplot as plt

import csv
import json
import numpy as np
import os.path as path
from random import sample, seed

phnet_infile = 'cit-HepPh.txt'
ptnet_infile = 'cit-HepTh.txt'

phnet_outfile = 'phnet.graphml'
ptnet_outfile = 'ptnet.graphml'

phnet_samplesfile = 'phnet_samples.json'
ptnet_samplesfile = 'ptnet_samples.json'

nets = [(phnet_infile, phnet_outfile, phnet_samplesfile), 
		(ptnet_infile, ptnet_outfile, ptnet_samplesfile)]

for infile, outfile, samplesfile in nets:
	# If the graphml file doesn't exist, 
	if not path.isfile(outfile):
		# Initialize the empty graph
		net = gt.Graph()
		# Add a vertex property for the citation network id
		id = net.new_vertex_property('string')
		# And make it internal to the graph
		net.vertex_properties['id'] = id
		# Since gt doesn't provide an efficient way to look up vertices given  
		#  a property value, we'll need a dict to do that
		id_to_gt = {}

		# And parse the graph from `infile`
		with open(infile) as readfile:
			print('reading ' + infile)
			read = csv.reader(readfile, delimiter = '\t')
			count = 0
			for line in read:
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
					tail = net.add_vertex()
					id[tail] = tail_id
					id_to_gt[tail_id] = tail
			
				# Likewise with the head
				if head_id in id_to_gt:
					head = id_to_gt[head_id]
				else:
					head = net.add_vertex()
					id[head] = head_id
					id_to_gt[head_id] = head
			
				# Add the edge and increase the progress counter
				net.add_edge(tail, head)
				# Show an update every nth node
				count += 1
				if count % 10000 == 0:
					print(count)

		print('finished reading ' + infile)
		# Write it to disk so we don't have to do this again later
		net.save(outfile)
		print('finished saving ' + outfile)
	else:
		print('found saved ' + outfile)
		# Read the saved network
		net = gt.load_graph(outfile)
		# Since vertices as such can't be pickled, we need to reconstruct 
		#  id and id_to_gt manually
		print('finished reading ' + outfile)
		id = net.vertex_properties['id']
		id_to_gt = {id[vertex]: vertex for vertex in net.vertices()}
	
	#print(len(id_to_gt))
	print('total vertices: ' + str(net.num_vertices()))
	print('total edges: ' + str(net.num_edges()))

	# How many samples to collect?
	n_samples = 1000
	# Initialize a container for them
	samples = []
	# And set a seed
	seed = 13579
	print('generating ' + str(n_samples) + ' random partitions')
	while len(samples) < n_samples:
		# Generate a random partition
		temp_part = sample(list(id_to_gt), 200)
		#print(temp_part)
		# `modularity` needs the groups passed as a PropertyMap
		temp_part_pmap = net.new_vertex_property('bool')
		for vertex in net.vertices():
			temp_part_pmap[vertex] = id[vertex] in temp_part
		#print(comm.modularity(net, temp_part_pmap))
		# Calculate the modularity and save it in `samples`
		samples += [comm.modularity(net, temp_part_pmap)]
		if len(samples) % 50 == 0:
			print(len(samples))
	print('finished.  writing sample modularities to disc.')
	with open(samplesfile, 'w') as writefile:
		json.dump(samples, writefile)
	print('modularity mean: ' + str(np.mean(samples)))
	print('modularity sd: ' + str(np.std(samples)))

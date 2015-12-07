'''
# citation network
load network
obs network statistics
	degree distribution
	degree dist for core nodes
	modularity for core network
random partition statistics
plot observed vs. sampling distributions
phnet and ptnet statistics
plot

# author network
'''

import graph_tool as gt
import graph_tool.community as comm
import graph_tool.stats as gtstats

from ggplot import *

import numpy as np
import pandas as pd
from random import sample, seed


def load_net(infile, core = False):
	# Output filename
	#  Prefix only, not extension: 
	#  `split('.')` splits `infile` at the periods and returns a list 
	#  `[:-1]` grabs everything except the extension
	#  `'.'.join` recombines everything with periods
	outfile_pre = '.'.join(infile.split('.')[:-1])
	
	print('Loading ' + infile)
	net = gt.load_graph(infile)
	
	# If `core` is true, extract the core set
	if core:
		core_pmap = net.vertex_properties['core']
		core = [vertex for vertex in net.vertices() if core_pmap[vertex]]
	
	# Print basic network statistics
	print('Loaded ' + infile)
	print('Vertices: ' + str(net.num_vertices()))
	if core:
		print('Core vertices: ' + str(len(core)))
	print('Edges: ' + str(net.num_edges()))
	
	if core:
		return net, outfile_pre, core_pmap
	else:
		return net, outfile_pre



def degree_dists(net, outfile_pre, show_plot = False):
	'''
	Plot in, out, and total degree distributions
	'''
	# Calculate degree distributions
	tot_degree_dist = gtstats.vertex_hist(net, deg = 'total')[0]
	in_degree_dist = gtstats.vertex_hist(net, deg = 'in')[0]
	out_degree_dist = gtstats.vertex_hist(net, deg = 'out')[0]
	degrees = range(max(len(tot_degree_dist), 
						len(in_degree_dist), 
						len(out_degree_dist)))

	# Pad if necessary to get everything to the same length
	def _pad(dist):
		#print(dist)
		shortfall = len(degrees) - len(dist)
		dist = np.append(dist, [0] * shortfall)
		cumdist = 1 - np.cumsum(dist) / net.num_vertices()
		#print(dist)
		return(cumdist)
	tot_degree_dist = _pad(tot_degree_dist)
	in_degree_dist = _pad(in_degree_dist)
	out_degree_dist = _pad(out_degree_dist)

	# Combine the distributions into a single data frame
	degree_dists = pd.DataFrame({'degree': degrees,
									'total': tot_degree_dist,
									'in': in_degree_dist,
									'out': out_degree_dist})

	degree_dists_melted = pd.melt(degree_dists, id_vars = 'degree',
												value_vars = ['total', 'in', 'out'],
												var_name = 'distribution')
	#print(degree_dists_melted.head())

	# Build the plot
	dists_plot = ggplot(aes(x = 'degree', ymin = 0, ymax = 'value', fill = 'distribution'), 
						data = degree_dists_melted) +\
			geom_area(alpha = .2) +\
			ylab('1 - cumulative probability density') +\
			scale_x_log10() + scale_y_log10() +\
			scale_color_brewer(type = 'qual', palette = 'Set1') +\
			theme_bw()

	# If requested, show the plot
	if show_plot:
		print(dists_plot)
	
	# Save to disk
	ggsave(filename = outfile_pre + '.pdf', plot = dists_plot)
	return True


# Load network
#infile = 'citenet0.graphml'
#infile = 'autnet0.graphml'
infiles = ['autnet1.graphml']
#infiles = ['citenet0.graphml', 'autnet0.graphml', 'autnet1.graphml']

for infile in infiles:
	net, outfile_pre, core_pmap = load_net(infile, core = True)
	degree_dists(net, outfile_pre)
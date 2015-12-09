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

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from random import sample, seed

from statsmodels.distributions.empirical_distribution import ECDF as ecdf
from statsmodels.nonparametric.kde import KDEUnivariate as kde


def load_net(infile, core = False):
	'''
	Load a `graphml` file.  
	Returns the graph_tool Graph, a prefix for output files, and 
	 (if core is True) the property map for core vertices
	'''
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
		core_vertices = [vertex for vertex in net.vertices() if core_pmap[vertex]]
	
	# Print basic network statistics
	print('Loaded ' + infile)
	print('Vertices: ' + str(net.num_vertices()))
	if core:
		print('Core vertices: ' + str(len(core_vertices)))
	print('Edges: ' + str(net.num_edges()))
	
	if core:
		return net, outfile_pre, core_pmap, core_vertices
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



def p_sample(samples, observation):
	'''
	Given a list of samples and an actual observation, 
	calculate the p-value of the observation against the sample distribution.
	'''
	sample_ecdf = ecdf(samples)
	p = sample_ecdf(observation)
	return(min(p, 1-p))



def plot_sample_dist(samples, observation, stat_label = '$Q$', p_label = None):
	'''
	Given a list of samples and an actual observation, 
	build a plot for the sample distribution.
	''' 
	# Get the kernel density estimate
	sample_dist = kde(samples)
	sample_dist.fit()
	# Normalize
	sample_dist.norm = sample_dist.density / sum(sample_dist.density)
	
	sample_dist_plot = \
		ggplot(aes(x = 'x', y = 'density', ymax = 'density', ymin = 0),
						data = pd.DataFrame({
							'density': sample_dist.norm, 
							 'x': sample_dist.support})) + \
			geom_line(color = 'blue') + \
			geom_area(fill = 'blue', alpha = '.25') + \
			geom_vline(aes(xintercept = modularity), color = 'red')
	if p_label is not None:
		# TODO:  adding a text label screws up the axes
		pass
# 		sample_dist_plot = sample_dist_plot + \
# 				geom_text(aes(x = observation, y = .5*max(sample_dist.norm)), 
# 								label = 'test')
	sample_dist_plot = sample_dist_plot + \
			ylab('density') + \
			xlab(stat_label) + \
			theme_bw()
	return(sample_dist_plot)



# Load comparison networks
phnet_infile = 'cit-HepPh.txt', 
ptnet_infile = 'cit-HepTh.txt'

phnet_outfile = 'phnet.graphml'
ptnet_outfile = 'ptnet.graphml'

#phnet = load_net(phnet_infile, core = False)[0]
#ptnet = load_net(phnet_infile, core = False)[0]

# Load networks for analysis
#infiles = ['citenet0.graphml']
#infiles = ['autnet0.graphml']
infiles = ['autnet1.graphml']
#infiles = ['citenet0.graphml', 'autnet0.graphml', 'autnet1.graphml']

for infile in infiles:
	net, outfile_pre, core_pmap, core_vertices = load_net(infile, core = True)
	
	n_core = len(core_vertices)
	f_core = n_core / len(list(net.vertices()))
	
	#degree_dists(net, outfile_pre)
	
	modularity = comm.modularity(net, core_pmap)
	print('Observed modularity: ' + str(modularity))
	
	# How many samples to collect?
	n_samples = 200
	# Initialize a container for them
	samples = []
	# Set a seed
	seed(1357)
	print('generating ' + str(n_samples) + ' random partitions')
	while len(samples) < n_samples:
		# Generate a random partition
		#print('generating partition')
		temp_part = sample(list(net.vertices()), n_core)
		# `modularity` needs the groups passed as a PropertyMap
		#print('building PropertyMap')
		temp_part_pmap = net.new_vertex_property('bool', val = False)
		for vertex in temp_part:
			temp_part_pmap[vertex] = True
		#print('calculating modularity')
		# Calculate the modularity and save it in `samples`
		samples += [comm.modularity(net, temp_part_pmap)]
		if len(samples) % 100 == 0:
			print(len(samples))
			
	# Calculate p-value
	p = p_sample(samples, modularity)
	print('P-value of modularity: ' + str(p))

	# Plot the sample distribution
	sample_plot = plot_sample_dist(samples, modularity, p_label = p)
	# TODO: save the plot
	print(sample_plot)
	
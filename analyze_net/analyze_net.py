import graph_tool as gt
import graph_tool.centrality as gtcentral
import graph_tool.community as comm
import graph_tool.draw as gtdraw
import graph_tool.stats as gtstats

from ggplot import *

import bottleneck as bn
from datetime import datetime
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from random import sample, seed
#import scipy.stats as stats

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



def summary(data):
	'''
	Report descriptive statistics for the 1D `data`
	'''
	minimum = min(data)
	if type(minimum) is np.array:
		minimum = min(data).item()
	maximum = max(data)
	if type(maximum) is np.array:
		maximum = max(data).item()
	stats = {'count' : int(len(data)),
			'min': minimum,
			'max': maximum,

			'mean': np.average(data),
			'sd': np.std(data),

			'q05': np.percentile(data, 5),
			'q25': np.percentile(data, 25),
			'median': np.median(data),
			'q75': np.percentile(data, 75),
			'q95': np.percentile(data, 95)
			}
	stats['iqr50'] = stats['q75'] - stats['q25']
	stats['iqr90'] = stats['q95'] - stats['q05']
	return(pd.Series(stats))
	


def degree_dist(net, core, show_plot = False, outfile = None, save_plot = True):
	'''
	Plot out-degree empirical CDF
	'''
	# Build degree distribution
	# Out degree for every vertex
	out_degrees = [vertex.out_degree() for vertex in net.vertices()]
	# Write them into the graph
	net.vp['out-degree'] = net.new_vertex_property('int', vals = out_degrees)
	#  x values: degrees
	degrees = list(set(out_degrees))
 	#  Use the ecdf to build the y values
	out_degree_ecdf = ecdf(out_degrees)
	#  Use 1-ecdf for legibility when most nodes have degree near 0
	out_degree_dist = [1 - out_degree_ecdf(degree) for degree in degrees]
	# Write 1-ecdf into the graph
	net.vp['out-degree ecdf'] = \
		net.new_vertex_property('float', 
			vals = [1 - out_degree_ecdf(net.vp['out-degree'][vertex]) 
						for vertex in net.vertices()])
	
	# Rank the vertices by out-degree
	vertex_ranking = len(out_degrees) - bn.rankdata(out_degrees) + 1
	# Write them into the graph
	net.vp['out-degree rank'] = net.new_vertex_property('int', vals = vertex_ranking)
	# Map these against `degree`:  
	#  for each degree, get the index of its first occurrence in the 
	#  vertex-level list `out_degrees`; that index corresponds to the 
	#  index in `vertex_ranking`
	ranking = [vertex_ranking[out_degrees.index(degree)] 
				for degree in degrees]
	
 	# Combine into a single data frame
	degree_dist = pd.DataFrame({'degree': degrees, 
								'density': out_degree_dist, 
								'rank': ranking})
	
	# Grab the degrees and rankings for the core vertices
	out_degrees_core = [net.vp['out-degree'][vertex] for vertex in core]
	out_degree_dist_core = [net.vp['out-degree ecdf'][vertex] for vertex in core]
	ranking_core = [net.vp['out-degree rank'][vertex] for vertex in core]
	degree_dist_core = \
		pd.DataFrame({'degree': out_degrees_core, 
						'density': out_degree_dist_core, 
						'rank': ranking_core})
	#print(degree_dist_core)
	print('Summary statistics for core vertex out-degrees:')
	print(pd.DataFrame({k: summary(degree_dist_core[k]) for k in degree_dist_core}))

	# Build the degree x density plot
	density_plot = ggplot(aes(x = 'degree'),
						data = degree_dist) +\
			geom_area(aes(ymin = 0, ymax = 'density', fill = 'blue'), alpha = .3) +\
			geom_line(aes(y = 'density', color = 'blue'), alpha = .8) +\
			xlab('Out-degree') +\
			ylab('1 - Cumulative probability density') +\
			scale_x_log10() + scale_y_log10() +\
			theme_bw()
	# Add a rug for the core vertices
	density_plot = density_plot + \
		geom_point(aes(x = 'degree', y = 'density'),
				shape = '+', size = 250, alpha = .8, color = 'red',
				data = degree_dist_core)

	# If requested, show the plot
	if show_plot:
		print(density_plot)
	
	# Save to disk
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.degree_density' + '.pdf', plot = density_plot)
		
	# Same thing for degree x ranking
	ranking_plot = ggplot(aes(x = 'degree'), data = degree_dist) +\
			geom_area(aes(ymin = 0, ymax = 'rank', fill = 'blue'), alpha = .3) +\
			geom_line(aes(y = 'rank', color = 'blue'), alpha = .8) +\
			xlab('Out-degree') +\
			ylab('Rank') +\
			scale_x_log10() + scale_y_log10() +\
			theme_bw()
	ranking_plot = ranking_plot +\
		geom_point(aes(x = 'degree', y = 'rank'),
				shape = '+', size = 250, alpha = .8, color = 'red',
				data = degree_dist_core)
	if show_plot:
		print(ranking_plot)
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.degree_rank' + '.pdf', plot = ranking_plot)
	
	return(density_plot, ranking_plot)



def ev_centrality_dist(net, core, show_plot = False, outfile = None, save_plot = True):
	'''
	Calculate and plot eigenvector centrality distributions. 
	'''
	# Calculate eigenvector centrality and write them into the graph
	print('Calculating eigenvector centrality')
	net.vp['evc'] = gtcentral.eigenvector(net, epsilon=1e-03)[1]
	print('Done')
	# Extract them into a useful format
	eigen_central = net.vp['evc'].get_array().tolist()
	# x values: centralities
	centralities = list(set(eigen_central))
	# Use the ecdf to build the y values
	eigen_central_ecdf = ecdf(eigen_central)
	# Use 1-ecdf for legibility when most nodes have centrality near 0
	centrality_distribution = \
		[1 - eigen_central_ecdf(centrality) for centrality in centralities]
	# Write 1-ecdf into the graph
	net.vp['evc ecdf'] = \
		net.new_vertex_property('float',
			vals = [1 - eigen_central_ecdf(net.vp['evc'][vertex])
						for vertex in net.vertices()])

	# Rank the vertices by eigenvector centrality
	vertex_ranking = len(eigen_central) - bn.rankdata(eigen_central) + 1
	# Write them into the graph
	net.vp['evc rank'] = net.new_vertex_property('int', vals = vertex_ranking)
	#print(vertex_ranking)
	print('Mapping rankings to centralities')
	# Map these against `centralities`:  
	#  for each degree, get the index of its first occurrence in the 
	#  vertex-level list `eigen_central`; that index corresponds to the 
	#  index in `vertex_ranking`
	ranking = [vertex_ranking[eigen_central.index(centrality)] 
				for centrality in centralities]
	
 	# Combine into a single data frame
	centrality_dist = pd.DataFrame({'centrality': centralities,
									'density': centrality_distribution,
									'rank': ranking})
	#print(centrality_dist.head())

	# Grab centralities and rankings for the core vertices
	centralities_core = [net.vp['evc'][vertex] for vertex in core]
	centrality_distribution_core = [net.vp['evc ecdf'][vertex] for vertex in core]
	ranking_core = [net.vp['evc rank'][vertex] for vertex in core]
	centrality_dist_core = \
		pd.DataFrame({'centrality': centralities_core,
						'density': centrality_distribution_core,
						'rank': ranking_core})
	#print(centrality_dist_core)
	print('Summary statistics for core vertex centralities:')
	print(pd.DataFrame({k: summary(centrality_dist_core[k]) for k in centrality_dist_core}))
	
	# Build the plot
	density_plot = ggplot(aes(x = 'centrality'), data = centrality_dist) +\
			geom_area(aes(ymin = 0, ymax = 'density', fill = 'blue'), alpha = .3) +\
			geom_line(aes(y = 'density'), color = 'blue', alpha = .8) +\
			xlab('Eigenvector centrality') +\
			ylab('1 - Cumulative probability density') +\
			scale_x_log10() + scale_y_log10() +\
			theme_bw()
	#Add a rug for the core vertices
	density_plot = density_plot + \
		geom_point(aes(x = 'centrality', y = 'density'),
				shape = '+', size = 250, alpha = .8, color = 'red',
				data = centrality_dist_core)
	
	# If requested, show the plot
	if show_plot:
		print(density_plot)
	
	# Save to disk
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.evc_density' + '.pdf', plot = density_plot)
	
	# Same thing for degree x ranking
	ranking_plot = ggplot(aes(x = 'centrality'), data = centrality_dist) +\
			geom_area(aes(ymin = 0, ymax = 'rank', fill = 'blue'), alpha = .3) +\
			geom_line(aes(y = 'rank'), color = 'blue', alpha = .8) +\
			xlab('Eigenvector centrality') +\
			ylab('Rank') +\
			scale_x_log10() + scale_y_log10() +\
			theme_bw()
	ranking_plot = ranking_plot +\
		geom_point(aes(x = 'centrality', y = 'rank'),
				shape = '+', size = 250, alpha = .8, color = 'red',
				data = centrality_dist_core)
	if show_plot:
		print(ranking_plot)
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.evc_rank' + '.pdf', plot = ranking_plot)
	
	return(density_plot, ranking_plot)



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
			geom_vline(aes(xintercept = observation), color = 'red')
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



def modularity_sample_dist(net, n_core, obs_mod, 
							n_samples = 1000, seed_int = None,
							show_plot = False, 
							outfile = None, save_plot = True):
	'''	
	Generate a sample distribution for modularity. 
	'''	
	# Initialize a container for samples
	samples = []
	# Set a seed
	if seed_int is not None:
		seed(seed_int)
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
	p = p_sample(samples, obs_mod)
	print('P-value of modularity: ' + str(p))

	# Plot the sample distribution
	sample_plot = plot_sample_dist(samples, obs_mod, p_label = p)
	
	if show_plot:
		print(sample_plot)
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.mod_sample' + '.pdf', 
				plot = sample_plot)

	return(p)



def optimal_sample_dist(net, obs_mod, 
							n_samples = 500, seed_int = None,
							show_plot = False, 
							outfile = None, save_plot = True):
	'''	
	Generate a sample distribution for modularity. 
	'''	
	# Initialize a container for samples
	samples = []
	# Set a seed
	if seed_int is not None:
		seed(seed_int)
	print('Generating ' + str(n_samples) + ' optimal partitions')
	while len(samples) < n_samples:
		# Generate an optimal partition
		temp_part_pmap = comm.community_structure(net, n_iter = 100, n_spins = 2)
		# Calculate the modularity and save it in `samples`
		samples += [comm.modularity(net, temp_part_pmap)]
		if len(samples) % 100 == 0:
			print(len(samples))
			
	# Calculate p-value
	p = p_sample(samples, obs_mod)
	print('P-value of modularity: ' + str(p))

	# Plot the sample distribution
	sample_plot = plot_sample_dist(samples, obs_mod, p_label = p)
	
	if show_plot:
		print(sample_plot)
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.mod_sample' + '.pdf', 
				plot = sample_plot)

	return(p)



def run_analysis(netfile):
	# Timestamp
	print(datetime.now())
	
	# Load the network
	# --------------------
	net, outfile_pre, core_pmap, core_vertices = load_net(netfile + '.graphml', 
 															core = True)
 	# Add a filter
	print('Adding filter')
	# Recent papers filter for the citation net
	if netfile == 'citenet0':
		year = net.vp['year']
		recent_list = [year[vertex] > 2005 for vertex in net.vertices()]
		recent_pmap = net.new_vertex_property('boolean')
		recent_pmap.a = np.array(recent_list)
		net.set_vertex_filter(recent_pmap)
	# Distance from core set for the author nets
	else:
		net.set_directed(False)
		extended_set_pmap = core_pmap.copy()
		gt.infect_vertex_property(net, extended_set_pmap, vals=[True])
		gt.infect_vertex_property(net, extended_set_pmap, vals=[True])
		net.set_vertex_filter(extended_set_pmap)

	print('Filtered vertices: ' + str(net.num_vertices()))
	print('Filtered edges: ' + str(net.num_edges()))
	
# 
# 	# Plotting
# 	# --------------------
# 	# Calculate the plotting layout
# 	print('Calculating layout')
# 	#net.vp['layout'] = gtdraw.radial_tree_layout(net, core_vertices[0], r = 4)
# 	net.vp['layout'] = gtdraw.sfdp_layout(net, C = .5, p = 6, verbose = True)
# 	print('Plotting')
# 	gtdraw.graphviz_draw(net, vcolor = core_pmap, pos = net.vp['layout'],
# 							vsize = .2, size = (50, 50),
# 							output = outfile_pre + '.net' + '.png'
# 							)
# 	#net.set_vertex_filter(None)
# 	
# 	# Vertex statistics
# 	# --------------------
# 	# ECDF for out-degree distribution
# 	degree_dist(net, core_vertices, outfile = outfile_pre, show_plot = False, save_plot = True)
# 	# ECDF for eigenvector centrality
# 	ev_centrality_dist(net, core_vertices, outfile = outfile_pre, show_plot = False, save_plot = True)
	
	# Modularity
	# --------------------
	# Calculate modularity, using the core vertices as the partition
	modularity = comm.modularity(net, core_pmap)
	print('Observed modularity: ' + str(modularity))
# 
# 	# Calculate the number of core vertices
# 	n_core = len(core_vertices)
# 	# Construct a sampling distribution for the modularity statistic
# 	#  And use it to calculate a p-value for the modularity
# 	p = modularity_sample_dist(net, n_core, modularity, 
# 								outfile = outfile_pre, show_plot = False)
# 	
# 	# Complexity-theoretic partitioning
# 	print('Information-theoretic partitioning')
# 	# Calculate the partition
# 	part_block = comm.minimize_blockmodel_dl(net, min_B = 2, max_B = 2)
# 	# Extract the block memberships as a pmap
# 	net.vp['partition'] = part_block.get_blocks()
# 	# Calculate the modularity
# 	block_modularity = comm.modularity(net, net.vp['partition'])
# 	print('Partion modularity: ' + str(block_modularity))
# 	
# 	print('Plotting')
# 	size_pmap = net.new_vertex_property('float', vals = .2 + .5 * core_pmap.a)
# 	gtdraw.graphviz_draw(net, vcolor = net.vp['partition'], pos = net.vp['layout'],
# 							vsize = size_pmap, size = (50, 50),
# 							output = outfile_pre + '.partition' + '.png'
# 							)
# 	#net.set_vertex_filter(None)
	
	# Modularity optimization
# 	samples = []
# 	while len(samples) < 100:
# 		mod_op_pmap = comm.community_structure(net, n_iter = 100, n_spins = 2)
# 		this_modularity = comm.modularity(net, mod_op_pmap)
# 		samples += [this_modularity]
# 		print(len(samples))
# 	print(summary(np.array(samples)))
#	p = optimal_sample_dist(net, modularity, n_samples = 300, 
# 								outfile = outfile_pre, show_plot = False)

	# TODO: Comparison networks

	# Save output
	#net.save(netfile + '.out' + '.graphml')

	# Timestamp
	print(datetime.now())
	# Visually separate analyses
	print('-'*40)
	
	
# Comparison networks
phnet_infile = 'cit-HepPh.txt', 
ptnet_infile = 'cit-HepTh.txt'

phnet_outfile = 'phnet.graphml'
ptnet_outfile = 'ptnet.graphml'

#phnet = load_net(phnet_infile, core = False)[0]
#ptnet = load_net(phnet_infile, core = False)[0]


if __name__ == '__main__':
	# Load networks for analysis
	netfiles = ['citenet0']
	#netfiles = ['autnet0']
	#netfiles = ['autnet1']
	#netfiles = ['autnet1', 'autnet0', 'citenet0']

	for netfile in netfiles:
		#logfile = netfile + '.log'
		#with open(logfile, 'w') as log:
		# TODO: print ~> logging to logfile
		run_analysis(netfile)

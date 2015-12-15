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



def _degree_dists(net, outfile_pre, core, show_plot = False):
	'''
	Plot in, out, and total degree distributions
	
	DEPRECATED:  We don't actually need all three distributions, just out-degree.
	'''
	# Calculate degree distributions
	tot_degree_dist = gtstats.vertex_hist(net, deg = 'total')[0]
	in_degree_dist = gtstats.vertex_hist(net, deg = 'in')[0]
	out_degree_dist = gtstats.vertex_hist(net, deg = 'out')[0]
	
	degrees = range(max(len(tot_degree_dist), 
						len(in_degree_dist), 
						len(out_degree_dist)))

	in_degrees = [vertex.in_degree() for vertex in net.vertices()]
	
# 	out_degrees = [vertex.out_degree() for vertex in net.vertices()]
# 	#tot_degrees = [vertex.in_degree() + vertex.out_degree() for vertex in net.vertices()]
# 	tot_degrees = np.array(in_degrees) + np.array(out_degrees)
# 	
# 	degrees = range(max(tot_degrees) + 1)
# 	tot_degree_ecdf = ecdf(tot_degrees)
# 	tot_degree_dist = [tot_degree_ecdf(degree) for degree in degrees]
# 	in_degree_ecdf = ecdf(in_degrees)
# 	in_degree_dist = [in_degree_ecdf(degree) for degree in degrees]
# 	out_degree_ecdf = ecdf(out_degrees)
# 	out_degree_dist = [out_degree_ecdf(degree) for degree in degrees]
# 
	in_degree_core = [vertex.in_degree() for vertex in core]
	out_degree_core = [vertex.out_degree() for vertex in core]
	tot_degree_core = np.array(in_degree_core) + np.array(out_degree_core)

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
									#'in': in_degree_dist,
									'out': out_degree_dist
									})
	if max(in_degrees) > 0:
		print('monkey')
		degree_dists['in'] = in_degree_dist
	degree_dists_melted = pd.melt(degree_dists, id_vars = 'degree',
												value_vars = ['total', 'in', 'out'],
												var_name = 'distribution')
												
	# Likewise with the core vertices
	degree_dists_core = pd.DataFrame({'total': tot_degree_core, 
										#'in': in_degree_core,
										'out': out_degree_core
										})
	if max(in_degrees) > 0:
		degree_dists_core['in'] = in_degree_core
	#print(degree_dists_core.head())
	degree_dists_core_melted = pd.melt(degree_dists_core, 
											value_vars = ['total', 'in', 'out'],
											var_name = 'distribution')
	#print(degree_dists_core_melted.head())
	
	# Build the plot
	#dists_plot = ggplot(aes(x = 'degree', fill = 'distribution'), 
	dists_plot = ggplot(aes(fill = 'distribution'),
						data = degree_dists_melted) +\
			geom_area(aes(x = 'degree', ymin = 0, ymax = 'value'), alpha = .2) +\
			ylab('1 - Cumulative probability density') +\
			scale_x_log10() + scale_y_log10() +\
			scale_color_brewer(type = 'qual', palette = 'Set1') +\
			theme_bw()
	dists_plot = dists_plot + \
		geom_jitter(aes(x = 'value', y = 1, color='distribution'),
				shape = '|', size = 1000, alpha = .75, 
				data = degree_dists_core_melted)

	# If requested, show the plot
	if show_plot:
		print(dists_plot)
	
	# Save to disk
	#ggsave(filename = outfile_pre + '.pdf', plot = dists_plot)
	return(dists_plot)



def summary(data):
	'''
	Report descriptive statistics for the 1D `data`
	'''
	stats = {'count' : int(len(data)),
			'min': min(data).item(),
			'max': max(data).item(),

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
	return(stats)
	


def degree_dist(net, core, show_plot = False, outfile = None, save_plot = True):
	'''
	Plot out-degree empirical CDF
	'''
	# Build degree distribution
	#  Out degree for every vertex
	out_degrees = [vertex.out_degree() for vertex in net.vertices()]
	#  x values: degrees
	degrees = list(set(out_degrees))
 	#  Use the ecdf to build the y values
	out_degree_ecdf = ecdf(out_degrees)
	#  Use 1-ecdf for legibility when most nodes have degree near 0
	out_degree_dist = [1 - out_degree_ecdf(degree) for degree in degrees]
	
	# Rank the vertices by out-degree
	vertex_ranking = len(out_degrees) - bn.rankdata(out_degrees) + 1
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
	out_degrees_core = [vertex.out_degree() for vertex in core]
	out_degree_dist_core = [1 - out_degree_ecdf(degree) for degree in out_degrees_core]
	# For efficiency reasons, make a standalone list of vertices
	vertices = list(net.vertices())
	ranking_core = [vertex_ranking[vertices.index(vertex)] for vertex in core]
	degree_dist_core = \
		pd.DataFrame({'degree': out_degrees_core, 
						'density': out_degree_dist_core, 
						'rank': ranking_core})
	#print(degree_dist_core)
	print('Summary statistics for core vertex out-degrees:')
	degree_dist_core_summary = {k: summary(degree_dist_core[k]) for k in degree_dist_core}
	print(pd.DataFrame(degree_dist_core_summary))

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
	# Calculate eigenvector centrality
	eigen_central_pmap = net.new_vertex_property('double')
	print('Calculating eigenvector centrality')
	eigen_central_pmap = gtcentral.eigenvector(net, epsilon=1e-03)[1]
	print('Done')
	# Extract them into a useful format
	eigen_central = eigen_central_pmap.get_array().tolist()
	# x values: centralities
	centralities = list(set(eigen_central))
	# Use the ecdf to build the y values
	eigen_central_ecdf = ecdf(eigen_central)
	# Use 1-ecdf for legibility when most nodes have centrality near 0
	centrality_distribution = \
		[1 - eigen_central_ecdf(centrality) for centrality in centralities]

	# Rank the vertices by eigenvector centrality
	print('Ranking centralities')
	vertex_ranking = len(eigen_central) - bn.rankdata(eigen_central) + 1
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
	centralities_core = [eigen_central_pmap[vertex] for vertex in core]
	centrality_distribution_core = [1 - eigen_central_ecdf(centrality) for centrality in centralities_core]
	# For efficiency, build a standalone list of vertices
	vertices = list(net.vertices())
	ranking_core = [vertex_ranking[vertices.index(vertex)] for vertex in core]
	centrality_dist_core = \
		pd.DataFrame({'centrality': centralities_core,
						'density': centrality_distribution_core,
						'rank': ranking_core})
	#print(centrality_dist_core)
	print('Summary statistics for core vertex centralities:')
	centrality_dist_core_summary = {k: summary(centrality_dist_core[k]) for k in centrality_dist_core}
	print(pd.DataFrame(centrality_dist_core_summary))
	
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
	sample_plot = plot_sample_dist(samples, modularity, p_label = p)
	
	if show_plot:
		print(sample_plot)
	if outfile is not None and save_plot:
		ggsave(filename = outfile + '.mod_sample' + '.pdf', 
				plot = sample_plot)

	return(p)



# Load comparison networks
phnet_infile = 'cit-HepPh.txt', 
ptnet_infile = 'cit-HepTh.txt'

phnet_outfile = 'phnet.graphml'
ptnet_outfile = 'ptnet.graphml'

#phnet = load_net(phnet_infile, core = False)[0]
#ptnet = load_net(phnet_infile, core = False)[0]

# Load networks for analysis
#infiles = ['citenet0.graphml']
infiles = ['autnet0.graphml']
#infiles = ['autnet1.graphml']
#infiles = ['citenet0.graphml', 'autnet0.graphml', 'autnet1.graphml']

# Timestamp
print(datetime.now())

for infile in infiles:
	# Load the network
	net, outfile_pre, core_pmap, core_vertices = load_net(infile, core = True)
	
	# Set up a filter for plotting purposes
	print('Adding filter')
	# Distance from core set filter
	net.set_directed(False)
	extended_set_pmap = core_pmap.copy()
	gt.infect_vertex_property(net, extended_set_pmap, vals=[True])
	gt.infect_vertex_property(net, extended_set_pmap, vals=[True])
	net.set_directed(True)
	net.set_vertex_filter(extended_set_pmap)
	print('Filtered vertices: ' + str(net.num_vertices()))
	
	# Calculate the plotting layout
	print('Calculating layout')
	#layout = gtdraw.radial_tree_layout(net, core_vertices[0])
	layout = gtdraw.sfdp_layout(net, p = 4, verbose = True)
	print('Plotting')
	gtdraw.graphviz_draw(net, vcolor = core_pmap, pos = layout,
							vsize = .2, size = (50, 50),
							output = outfile_pre + '.net' + '.png')
	net.set_vertex_filter(None)
	
	# ECDF for out-degree distribution
	degree_dist(net, core_vertices, outfile = outfile_pre, show_plot = False, save_plot = True)
	# ECDF for eigenvector centrality
	ev_centrality_dist(net, core_vertices, outfile = outfile_pre, show_plot = False, save_plot = True)
	
	# Calculate modularity, using the core vertices as the partition
	modularity = comm.modularity(net, core_pmap)
	print('Observed modularity: ' + str(modularity))

	# Calculate the number of core vertices
	n_core = len(core_vertices)
	# Construct a sampling distribution for the modularity statistic
	#  And use it to calculate a p-value for the modularity
# 	p = modularity_sample_dist(net, n_core, modularity, 
# 								outfile = outfile_pre, show_plot = False)
	
	# Complexity-theoretic partitioning
	print('Complexity-theoretic partitioning')
	# Calculate the partition
	part_block = comm.minimize_blockmodel_dl(net, min_B = 2, max_B = 2)
	# Extract the block memberships as a pmap
	part_block_pmap = part_block.get_blocks()
	# Calculate the modularity
	block_modularity = comm.modularity(net, part_block_pmap)
	print('Partion modularity: ' + str(block_modularity))
	
	print('Plotting')
	#net.set_vertex_filter(extended_set_pmap)
	#gtdraw.graphviz_draw(net, vcolor = part_block_pmap, pos = layout)
	#net.set_vertex_filter(None)
	
	# Modularity optimization
# 	part_block_pmap = gt.community_structure(net, n_iter = 500, n_spins = 2)

	# Timestamp
	print(datetime.now())
	# Visually separate analyses
	print('-'*40)
	
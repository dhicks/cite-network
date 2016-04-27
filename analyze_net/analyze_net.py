# -*- coding: utf-8 -*-
'''
Using the `graphml` files and two "comparison networks," conduct the actual 
network analysis.  

The "comparison networks" are citation networks grabbed from arXiv, with papers 
from January 1993 to April 2003.  They can be found at 
<https://snap.stanford.edu/data/cit-HepPh.html> and 
<https://snap.stanford.edu/data/cit-HepTh.html>.  
'''

# Graph-tool modules
# TODO: import graph_tool.all as gt
import graph_tool.all as gt

# Color schemes used in plotting nets
from matplotlib.cm import PiYG, PiYG_r

# Python port of ggplot
#  Very incomplete and buggy! 
from ggplot import *
from ggplot.utils.exceptions import GgplotError

# Other things we'll need
import bottleneck as bn
from datetime import date, datetime
import logging
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from random import sample, seed
import scipy.stats as spstats

from statsmodels.distributions.empirical_distribution import ECDF as ecdf
from statsmodels.nonparametric.kde import KDEUnivariate as kde


def load_net(infile, core = False, filter = False):
    '''
    Load a `graphml` file.  
    :param infile: The `graphml` file to load.
    :param core: Does the net contain a core vertex property map?  
    :filter: Apply a filter? 
    :return: the graph_tool `Graph`, a prefix for output files, and 
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
    
    if core and filter:
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
        # Remove everything caught in the filter
        net.purge_vertices()
        # Extract the largest component
        net.set_vertex_filter(gt.label_largest_component(net, directed=False))
        net.purge_vertices()
        # Rebuild core
        core_pmap = net.vertex_properties['core']
        core_vertices = [vertex for vertex in net.vertices() if core_pmap[vertex]]

        print('Filtered vertices: ' + str(net.num_vertices()))
        print('Filtered edges: ' + str(net.num_edges()))
        print('Filtered core: ' + str(len(core_vertices)))
    elif filter and not core:
        print('Filter = true with core = false')
    
    if core:
        return net, outfile_pre, core_pmap, core_vertices
    else:
        return net, outfile_pre



def layout_and_plot(net, color_pmap, outfile_pre, filename_mod = '.net',
                    size_pmap = None, reverse_colors = False):
    '''
    Plot the net, using a predefined layout if it's included as a vector property.
    :param net: The network to plot.
    :param color_pmap: Property map on `net` to color nodes.
    :size_pmap: Property map on `net` to set size of verticies.  
    :param outfile_pre: Prefix for output filename.
    :param filename_mod: Extension to use on the output filename.
    '''
    # Define a default size
    if size_pmap is None:
        size_pmap = net.new_vertex_property('float', val = 20)
    # If a layout isn't included, calculate it
    if 'layout' not in net.vp:
        print('Calculating graph layout')
        #net.vp['layout'] = gt.fruchterman_reingold_layout(net)
        net.vp['layout'] = gt.sfdp_layout(net, verbose = True)
        #net.vp['layout'] = gt.radial_tree_layout(net, 0, r=2)
    # Set the colormap
    if not reverse_colors:
        colormap = PiYG
    else:
        colormap = PiYG_r
    # Plot the graph
    gt.graph_draw(net, vertex_fill_color = color_pmap, 
                                vcmap = colormap,
                                vertex_size = size_pmap,
                                edge_pen_width = 1,
                                pos = net.vp['layout'], #pin = True,
                                fit_view = 1,
                                output_size = (2000, 2000),
                                output = outfile_pre + filename_mod + '.png')
    return net.vp['layout']



def summary(data):
    '''
    Report several descriptive statistics for the 1D `data`.
    :param data: The Python list or numpy array to summarize.
    :return: A Pandas Series with the following stats:
        minimum value, maximum value,
        mean, standard deviation,
        5, 25, 50 (median), 75, and 95 percentiles, 
        50 and 90 interquartile range
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
    


def insularity(net, community):
    '''
    Calculates the insularity of a single community, the fraction of its edges 
    that are intracommunity. 
    :param net: The network of interest
    :param community: A Boolean property map on `net`
    :return: The insularity statistic
    '''
    # Community gets passed as a Boolean property map
    # Build a list of nodes where community == True
    community_nodes = set([vertex for vertex in net.vertices() if community[vertex]])
    # The set of all nodes touching the community
    community_edges = set([edge for node in community_nodes for edge in node.all_edges()])
    #print(len(community_edges))
    # Extract the intracommunity edges
    intracommunity_edges = [edge for edge in community_edges 
                                if edge.source() in community_nodes and
                                    edge.target() in community_nodes]
    # Return the fraction
    return(len(intracommunity_edges) / len(community_edges))



def partition_insularity(net, partition):
    '''
    Calculates the insularity for communities defined by the distinct values 
    of the given property map.
    :param net: The network of interest
    :param partition: A discretely-valued property map on `net`
    :return: Dict with {partition_value: insularity}
    '''
    insularities = {}
    for community in set(partition.get_array()):
        temp_pmap = net.new_vertex_property('bool',
                        vals = [partition[vertex] == community
                                for vertex in net.vertices()])
        temp_ins = insularity(net, temp_pmap)
        insularities[community] = temp_ins
    return insularities



def degree_dist(net, core, show_plot = False, save_plot = True, outfile = None):
    '''
    Calculate out degree, an empirical CDF, and ranking for each vertex.  
    Plot both degree x empirical CDF and degree x ranking, highlighting core vertices.
    Note that the plot is saved as a file only if *both* `save_plot` is true and
    output filename are given.  
    
    :param net: The network whose degree distribution we'd like to plot
    :param core: The property map of core vertices
    :param show_plot: Show the plot on the screen?
    :param save_plot: Save the plot as a file?
    :param outfile: Filename to use to save the plot
    
    :return: The CDF and ranking plots. 
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



def ev_centrality_dist(net, core, show_plot = False, save_plot = True, outfile = None):
    '''
    Calculate eigenvector centrality, an empirical CDF, and ranking for each vertex.  
    Plot both centrality x empirical CDF and centrality x ranking, highlighting core vertices.
    Note that the plot is saved as a file only if *both* `save_plot` is true and
    output filename are given.  
    
    :param net: The network whose degree distribution we'd like to plot
    :param core: The property map of core vertices
    :param show_plot: Show the plot on the screen?
    :param save_plot: Save the plot as a file?
    :param outfile: Filename to use to save the plot
    
    :return: The CDF and ranking plots. 
    '''# Calculate eigenvector centrality and write it into the graph
    print('Calculating eigenvector centrality')
    net.vp['evc'] = gt.eigenvector(net, epsilon=1e-03)[1]
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
    
    :param samples: A list or numpy array of sample values.
    :param observation: The observation to compare against.
    :return: The p-value.  Left/right tail is chosen automatically to minimize p. 
    '''
    sample_ecdf = ecdf(samples)
    p = sample_ecdf(observation)
    return(min(p, 1-p))



def plot_sample_dist(samples, observation, stat_label = '$Q$', p_label = None):
    '''
    Given a list of samples and an actual observation, 
    build a plot for the sample distribution.
    
    :param samples: The list or numpy array of samples.
    :param observation: The actual observation to plot against.
    :param stat_label: The string to label the horizontal axis.  
    :p_label: P-value to label on the plot as text.  
        Note that text labels are buggy in the current version of ggplot, 
        so this does nothing right now.  

    :return: The sample distribution plot. 
    ''' 
    # Get the kernel density estimate
    sample_dist = kde(samples)
    sample_dist.fit()
    # Normalize
    sample_dist.norm = sample_dist.density / sum(sample_dist.density)
    #print(sample_dist.support)
    
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
#         sample_dist_plot = sample_dist_plot + \
#                 geom_text(aes(x = observation, y = .5*max(sample_dist.norm)), 
#                                 label = 'test')
    sample_dist_plot = sample_dist_plot + \
            ylab('density') + \
            xlab(stat_label) + \
            theme_bw()
    return(sample_dist_plot)



def modularity_sample_dist(net, n_core, obs_mod, mod_func = gt.modularity,
                            n_samples = 500, seed_int = None,
                            show_plot = False, 
                            save_plot = True, outfile = None):
    '''    
    Generate a sample distribution for modularity using sets of random nodes. 
    :param net: Network of interest
    :param n_core: Number of core vertices
    :param obs_mod: Observed modularity
    :param mod_func: Function used to calculate modularity
    :param n_samples = 1000: Number of samples to draw
    :param seed_int: RNG seed
    :param show_plot: Show the plot on the screen?
    :param save_plot: Save the plot to a file?
    :param outfile: Filename to save the plot
    :return: p-value, fold induction of observation against sample
    '''    
    # Initialize a container for samples
    samples = []
    # Set a seed
    if seed_int is not None:
        seed(seed_int)
    print('Generating ' + str(n_samples) + ' random partitions')
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
        samples += [mod_func(net, temp_part_pmap)]
        if len(samples) % 100 == 0:
            print(len(samples))
            
    # Calculate p-value
    print('Mean sample value: ' + str(np.mean(samples)))
    p = p_sample(samples, obs_mod)
    print('P-value of observed value: ' + str(p))

    # Fold of observation relative to sampling distribution mean
    fold = obs_mod / np.mean(samples)
    print('Fold of observed value: ' + str(fold))

    # Plot the sample distribution
    sample_plot = plot_sample_dist(samples, obs_mod, p_label = p)
    
    if show_plot:
        print(sample_plot)
    if outfile is not None and save_plot:
        if max(samples) == min(samples):
            pass
        else:
            ggsave(filename = outfile + '.mod_sample' + '.pdf', 
                    plot = sample_plot)

    return(p, fold)



def optimal_sample_dist(net, obs_mod, 
                            n_samples = 500, seed_int = None,
                            show_plot = False, 
                            save_plot = True, outfile = None):
    '''    
    Generate a sample distribution for modularity using an algorithm that 
    tried to optimize modularity. 
    :param net: Network of interest
    :param n_core: Number of core vertices
    :param obs_mod: Observed modularity
    :param n_samples = 1000: Number of samples to draw
    :param seed_int: RNG seed
    :param show_plot: Show the plot on the screen?
    :param save_plot: Save the plot to a file?
    :param outfile: Filename to save the plot
    :return: p-value, fold induction of observation against sample
    '''    
	# Initialize a container for samples
    samples = []
    # Set a seed
    if seed_int is not None:
        seed(seed_int)
    print('Generating ' + str(n_samples) + ' optimal partitions')
    while len(samples) < n_samples:
        # Generate an optimal partition
        temp_part_pmap = gt.community_structure(net, n_iter = 100, n_spins = 2)
        # Calculate the modularity and save it in `samples`
        samples += [gt.modularity(net, temp_part_pmap)]
        if len(samples) % 100 == 0:
            print(len(samples))
            
    # Calculate p-value
    sample_mean = np.mean(samples)
    print('Mean sample modularity: ' + str(sample_mean))
    p = p_sample(samples, obs_mod)
    print('P-value of modularity: ' + str(p))
    # TODO: insularities

    # Fold of observation relative to sampling distribution mean
    fold = obs_mod / sample_mean
    if abs(fold) < 1:
        fold = 1 / fold
    print('Fold of observed modularity: ' + str(fold))

    # Plot the sample distribution
    try:
        sample_plot = plot_sample_dist(samples, obs_mod, p_label = p)
    
        if show_plot:
            print(sample_plot)
        if outfile is not None and save_plot:
            ggsave(filename = outfile + '.opt_sample' + '.pdf', 
                    plot = sample_plot)
    except GgplotError:
        print('Caught `GgplotError`. Skipping plot.')

    return(p, fold)



def run_analysis(netfile, compnet_files):
    '''
    Run the analysis.  
    :param netfile: Filename of the network to analyze
    :param compnet_files: List of filenames of the comparison networks, viz.,
        the high-energy physics networks.  
    '''
    
    # Timestamp
    # --------------------
    print(datetime.now())
    
    # Load the network
    # --------------------
    net, outfile_pre, core_pmap, core_vertices = load_net(netfile + '.graphml', 
                                                             core = True,
                                                             filter = True)
    output_folder = 'output/'
    outfile_pre = output_folder + outfile_pre
     
     # Plotting
    print('Plotting')
    layout = layout_and_plot(net, core_pmap, outfile_pre)
    # Store the layout in the net
    net.vp['layout'] = layout
    # Show only the core vertices    
    net.set_vertex_filter(core_pmap)
    layout_and_plot(net, core_pmap, outfile_pre, filename_mod = '.core.net', reverse_colors = True)
    net.set_vertex_filter(None)
    
    # Vertex statistics
    # --------------------
    # ECDF for out-degree distribution
    degree_dist(net, core_vertices, outfile = outfile_pre, 
                show_plot = False, save_plot = True)
    # ECDF for eigenvector centrality
    ev_centrality_dist(net, core_vertices, outfile = outfile_pre, 
                show_plot = False, save_plot = True)
    
    # Modularity
    # --------------------
    # Calculate modularity, using the core vertices as the partition
    modularity = gt.modularity(net, core_pmap)
    print('Observed modularity: ' + str(modularity))
    obs_ins = insularity(net, core_pmap)
    print('Observed insularity: ' + str(obs_ins))
   
    # Calculate the number of core vertices
    n_core = len(core_vertices)
    # Construct a sampling distribution for the modularity statistic
    #  And use it to calculate a p-value for the modularity
    print('Random sample modularity')
    modularity_sample_dist(net, n_core, modularity,
                                outfile = outfile_pre + '.mod', 
                                show_plot = False, save_plot = True)
    print('Random sample insularities')
    modularity_sample_dist(net, n_core, obs_ins, 
                                mod_func = insularity, 
                                outfile = outfile_pre + '.ins',
                                show_plot = False, save_plot = True)
    
    # Information-theoretic partitioning
    print('Information-theoretic partitioning')
    # Calculate the partition
    part_block = gt.minimize_blockmodel_dl(net, min_B = 2, max_B = 2, 
                                                parallel = True)
    # Extract the block memberships as a pmap
    net.vp['partition'] = part_block.get_blocks()
    # Calculate the modularity
    block_modularity = gt.modularity(net, net.vp['partition'])
    print('Partion modularity: ' + str(block_modularity))
    print('Partition insularities')
    block_insularities = partition_insularity(net, net.vp['partition'])
    for community in block_insularities:
        print('Community ' + str(community) + ': ' + 
                str(block_insularities[community]))
    
    print('Plotting')
    size_pmap = gt.prop_to_size(core_pmap, mi = 10, ma = 20)
    layout_and_plot(net, net.vp['partition'], outfile_pre,
                        size_pmap = size_pmap, filename_mod = '.partition')
    
    # Modularity optimization
    optimal_sample_dist(net, modularity, 
                                outfile = outfile_pre, 
                                show_plot = False, save_plot = True)


    # Save results
    # --------------------
    # The above covers all of the analysis to be written into the output files,
    #  so we'll go ahead and save things now.  
    print('Saving')
    # Save in graph-tool's binary format
    net.save(outfile_pre + '.out' + '.gt')
    # Replace vector-type properties with strings
    #net.list_properties()
    properties = net.vertex_properties
    for property_key in properties.keys():
        property = properties[property_key]
        if 'vector' in property.value_type():
            properties[property_key] = property.copy(value_type = 'string')
    # Save as graphml
    net.save(outfile_pre + '.out' + '.graphml')


    # Comparison networks
    # --------------------
    for compnet_file in compnet_files:
        # Load the comparison network
        compnet, compnet_outfile = load_net(compnet_file)
        # Set it to the same directedness as the network of interest
        compnet.set_directed(net.is_directed())
        # Size of compnet
        n_compnet = compnet.num_vertices()
        # Num vertices in compnet to use in each random partition
        k_compnet = round(n_core / net.num_vertices() * n_compnet)
        # Sample distribution based on random partition
        print('Random sample modularities')
        print('Observed modularity: ' + str(modularity))
        modularity_sample_dist(compnet, k_compnet, modularity, 
                                outfile = outfile_pre + '.mod.' + compnet_outfile, 
                                show_plot = False, save_plot = True)
        print('Random sample insularities')
        print('Observed insularity: ' + str(obs_ins))
        modularity_sample_dist(compnet, k_compnet, obs_ins, 
                                mod_func = insularity, 
                                outfile = outfile_pre + '.ins.' + compnet_outfile,
                                show_plot = False, save_plot = True)
        # Sample distribution based on optimizing modularity
#         optimal_sample_dist(compnet, modularity, n_samples = 300, 
#                                 outfile = outfile_pre + '.mod.' + compnet_outfile,  
#                                 show_plot = False)


    # Timestamp
    # --------------------
    print(datetime.now())
    # Visually separate analyses
    print('-'*40)
    
    
if __name__ == '__main__':
    # Networks for analysis
    netfiles = ['citenet0']
    #netfiles = ['autnet0']
    #netfiles = ['autnet1']
    #netfiles = ['autnet1', 'autnet0', 'citenet0']

    # Comparison networks
    #compnet_files = ['phnet.graphml']
    compnet_files = ['phnet.graphml', 'ptnet.graphml']
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format = '%(message)s')
    logger = logging.getLogger()
    logger.addHandler(logging.FileHandler('output/' + str(date.today()) + '.log', 'w'))
    print = logger.info
    
    print('-'*40)
    for netfile in netfiles:
        seed(24680)
        gt.seed_rng(24680)

        run_analysis(netfile, compnet_files)

    print(datetime.now())
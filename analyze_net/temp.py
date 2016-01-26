import graph_tool as gt
import graph_tool.community as gtcomm
#import graph_tool.draw as gtdraw
import graph_tool.topology as gtopo

from matplotlib.cm import OrRd_r, OrRd

from analyze_net import layout_and_plot

net = gt.load_graph('autnet0.out.gt')
core = net.vp['core']
core_vertices = [vertex for vertex in net.vertices() if core[vertex]]

print('total v: ' + str(net.num_vertices()))
print('total core: ' + str(len([vertex for vertex in net.vertices() if core[vertex]])))

# For citenet
# cutoff = 2013
# cutoff_pmap = net.new_vp('bool', vals = [net.vp['year'][vertex] > cutoff for vertex in net.vertices()])
# net.set_vertex_filter(cutoff_pmap)
# core_vertices = [vertex for vertex in net.vertices() if core[vertex]]
# print(cutoff)

# For autnets
cutoff = 0
cutoff_pmap = core.copy()
for i in range(cutoff):
	gt.infect_vertex_property(net, cutoff_pmap, vals = [True])
net.set_vertex_filter(cutoff_pmap)
core_vertices = [vertex for vertex in net.vertices() if core[vertex]]
print('cutoff v: ' + str(net.num_vertices()))
print('cutoff core: ' + str(len(core_vertices)))

print('Extracting core connected components')
# `label_components` returns a property map:  
#  `component_pmap[vertex]` returns the ID for the component containing vertex
component_pmap = gtopo.label_components(net, directed = False)[0]
# Extract a list with the distinct component IDs
component_list = {component_pmap[vertex] for vertex in net.vertices()}
print(str(len(component_list)) + ' weakly connected components found')
# Extract a list of the component IDs from the core set members
core_components = {component_pmap[vertex] for vertex in core_vertices}
print(str(len(core_components)) + ' components with core set members')

# Construct a list of graphs, one for each core component
citenets = []
for component in core_components:
	net.set_vertex_filter(None)
	net.set_vertex_filter(cutoff_pmap)
	# Define a new pmap for component membership
	core_comp_pmap = net.new_vertex_property('bool', vals = [component_pmap[vertex] == component for vertex in net.vertices()])
	# Use this to filter down to the component
	net.set_vertex_filter(core_comp_pmap)
	# Copy it
	temp_graph = gt.Graph(net, prune = True)
	# If the component isn't empty, add it to the list of graphs
	if temp_graph.num_vertices() > 0:
		citenets += [temp_graph]
		print('Component #' + str(component))
		print('Vertices: ' + str(temp_graph.num_vertices()))
		print('Edges: '	+ str(temp_graph.num_edges()))
		print('Core: ' + str(len([vertex for vertex in temp_graph.vertices() if temp_graph.vp['core'][vertex]])))
		#print('Modularity: ' + str(gtcomm.modularity(temp_graph, temp_graph.vp['core'])))
		
		#del temp_graph.vp['layout']
		#layout_and_plot(temp_graph, temp_graph.vp['core'], 'temp' + str(component))
		part_block = gtcomm.minimize_blockmodel_dl(temp_graph, min_B = 2, max_B = 2)
		block_modularity = gtcomm.modularity(temp_graph, part_block.get_blocks())
		print('Partion modularity: ' + str(block_modularity))
	else:
		pass
		#print(component)
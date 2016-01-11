import graph_tool as gt
import json
from random import sample

net = gt.load_graph('citenet0.out.gt')

core_pmap = net.vp['core']
core = [vertex for vertex in net.vertices() if core_pmap[vertex]]
downstream = core_pmap.copy()
gt.infect_vertex_property(net, downstream, vals = [True])

boundary_pmap = net.new_vp('bool', 
							vals = [downstream[vertex] and not core_pmap[vertex] 
									for vertex in net.vertices()])
boundary = [vertex for vertex in net.vertices() if boundary_pmap[vertex]]

core_dois = [net.vp['doi'][vertex] for vertex in core]
core_sids = [net.vp['sid'][vertex] for vertex in core]

core_refs = {}
for paper in boundary:
	core_ref_sids = [sid for sid in net.vp['references'][paper] if sid in core_sids]
	core_ref_papers = [paper for paper in core if net.vp['sid'][paper] in core_ref_sids]
	core_ref_dois = {net.vp['doi'][paper]: 0 for paper in core_ref_papers}

	core_refs[net.vp['doi'][paper]] = core_ref_dois

print('Total boundary items: ' + str(len(boundary)))

boundary_subset = sample(boundary, 25)
boundary_subset_dois = [net.vp['doi'][paper] for paper in boundary_subset]
core_refs_subset = {key:value for key, value in core_refs.items() if key in boundary_subset_dois}
print('Total subset items: ' + str(len(boundary_subset)))

with open('boundary.output.json', 'w') as outfile:
	json.dump(core_refs_subset, outfile, indent = 4)
# Interactive data analysis #

require(dplyr)
require(igraph)
require(ggplot2)
	require(cowplot)
require(lsr)
#require(pwr)
require(xtable)

# ---------- #
# Load the citation network
net = read_graph('citenet0.out.graphml', format = 'graphml')
# Convert it to a data frame for convenience
net_df = get.data.frame(net, what = 'vertices') %>% data.frame
net_df$partition = as.factor(net_df$partition)

#core_net = delete_vertices(net, V(net)[core == FALSE])

# ---------- #
# Eigenvector centrality and out-degree
net_df %>% filter(evc.rank <= 10) %>% View
net_df %>% filter(evc.rank <= 100 & core) %>% View

years = seq(from = min(net_df$year), to = max(net_df$year), by = 2)

# Out degree vs. year
out.v.year <- ggplot(data = net_df, aes(x = year, y = out.degree)) + 
	geom_point(aes(size = core, color = core), alpha = .5, position = 'jitter') +
	#stat_smooth(method = 'lm') +
	stat_summary(fun.y = 'median', geom = 'line', color = 'blue') +
	scale_x_continuous(breaks = years) +
	scale_y_log10() + ylab('out degree')
out.v.year
# Out degree ranking vs. year
ggplot(data = net_df, aes(x = year, y = out.degree.rank)) + 
	geom_point(aes(size = core, color = core), alpha = .5, position = 'jitter') +
	#stat_smooth(method = 'lm') +
	stat_summary(fun.y = 'median', geom = 'line', color = 'blue') +
	scale_x_continuous(breaks = years) +
	ylab('out degree ranking')
# Centrality rank vs. year
evc.v.year <- ggplot(data = net_df, aes(x = year, y = evc.rank)) + 
	geom_point(aes(size = core, color = core), 
			   alpha = .5, position = 'jitter') + 
	#stat_smooth(method = 'lm') +
	stat_summary(fun.y = 'median', geom = 'line', color = 'blue') +
	scale_x_continuous(breaks = years) +
	ylab('centrality ranking')
evc.v.year

out_evc_year <- plot_grid(out.v.year, evc.v.year, align = 'v', nrow = 2)
#save_plot('out_evc_year.png', out_evc_year, base_aspect_ratio = 3)

# Out degree vs. centrality - rankings
ggplot(data = net_df, aes(x = evc.rank, y = out.degree.rank)) +
	geom_point(aes(size = core, color = core), alpha = .5, position = 'jitter') +
	geom_smooth() +
	scale_x_log10() + xlab('centrality ranking') + 
	scale_y_log10() + ylab('out degree ranking')
cor(net_df$evc.rank, net_df$out.degree.rank)**2

# Out degree vs. centrality - raw values
ggplot(data = filter(net_df, evc > 0 & out.degree > 0), aes(x = evc, y = out.degree)) +
	geom_point(aes(size = core, color = core), alpha = .5, position = 'jitter') +
	geom_smooth() +
	scale_x_log10() + xlab('centrality') + 
	scale_y_log10() + ylab('out degree')
cor(net_df$evc, net_df$out.degree)**2

# Out degree vs. centrality ranking
ggplot(data = filter(net_df, out.degree > 0), aes(x = evc.rank, y = out.degree)) +
	geom_point(aes(size = core, color = core), alpha = .5, position = 'jitter') +
	geom_smooth() +
	scale_x_log10() + xlab('centrality ranking') + 
	scale_y_log10() + ylab('out degree')
cor(net_df$evc.rank, net_df$out.degree)**2



# ---------- #
# Correlation between core and information-theoretic partition
# Plot
ggplot(data = net_df) +
	geom_point(aes(x = partition, y = core, color = core, alpha = core), 
			   #alpha = .5,
			   position = position_jitter(width = .4, height = .4)) +
	scale_color_brewer(palette = 'Set1', guide = FALSE) +
	scale_alpha_discrete(guide = FALSE) +
	xlab('calculated partition')

ggplot(data = net_df) +
	geom_point(aes(x = year, y = partition, color = core, alpha = core),
			   position = position_jitter()) +
	scale_x_continuous(breaks = years) +
	scale_color_brewer(palette = 'Set1') +
	scale_alpha_discrete(guide = FALSE)

# Contingency table
corepart_table = table(net_df$core, net_df$partition)
corepart_table
# Odds of being in partition 0 given value of core
corepart_table[,1] / corepart_table[,2]
# Chi-square test
corepart_chisq = chisq.test(corepart_table, correct = FALSE)
corepart_chisq
# Cramer's V
cramersV(corepart_table, correct = FALSE) ** 2

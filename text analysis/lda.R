library(tidyverse)
library(tidytext)
library(topicmodels)
library(reshape2)
library(stringr)

## Setup for parallel processing
library(foreach)
library(doParallel)
cl = makeCluster(4)
registerDoParallel(cl)
getDoParWorkers()

## Load data and prepare a document-term matrix
load('scraped text.Rdata')

token_counts = scraped_text_df %>% 
	select(-url, -title) %>%
	unnest_tokens(format = 'html', word, description) %>%
	anti_join(stop_words) %>%
	group_by(doi, word) %>%
	summarize(n = n()) %>%
	ungroup()

descriptions_dtm = cast_dtm(token_counts, doi, word, n)

## Using a stability method derived from https://arxiv.org/pdf/1404.4606v3.pdf

## If agreement scores have already been calculated, skip this
if (!file.exists('agreement scores.Rdata')) {
## 1. Randomly generate tau samples of the data set, each containing beta * n documents.
## Number of documents
n = nrow(scraped_text_df)
## Fraction to include in each sample
beta = .8
## Total number of samples
tau = 50

## Draw sample corpora, and convert each to DTM
set.seed(54321)
samples = lapply(1:tau, function (x) sample_n(scraped_text_df, size = .8 * n)$doi) %>%
	lapply(function (x) filter(token_counts, doi %in% x)) %>%
	lapply(function (x) cast_dtm(x, doi, word, n))

## 2. For each value of k in [kmin, kmax] :
k_range = 2:12
agree_scores = foreach(k = k_range, 
					   .combine = 'cbind', .verbose = TRUE, 
					   .packages = c('stringr', 'dplyr', 'igraph')) %do% {
 	## 1. Apply the topic modeling algorithm to the complete data set of n documents
 	##    to generate k topics; represent the output as the gamma_ij, the 
	##    posterior probability that topic i is used by document j
 	s0 = LDA(descriptions_dtm, k = k, control = list(seed = 42)) %>%
 		tidy(matrix = 'gamma') %>%
 		spread(topic, gamma, sep = '.')
 	
 	## 2. For each sample Xi:
 	## (a) Apply the topic modeling algorithm to Xi to generate k topics, and
 	##     represent the output as gammas
 	# si = lapply(samples, function (x) {LDA(x, k = k) %>% 
 	# 									tidy(matrix = 'gamma') %>%
 	# 									spread(topic, gamma, sep = '.')})
 	si = foreach(sample = samples, .verbose = TRUE, 
 				 .packages = c('dplyr', 'topicmodels', 'tidytext', 'tidyr')) %dopar% 
 				 {LDA(sample, k = k) %>% 
 				 		tidy(matrix = 'gamma') %>% 
 				 		spread(topic, gamma, sep = '.')}
 	
 	## (b) Calculate the agreement score agree(S0, Si).
 	## We do this using correlations of gammas
 	agreement = function (s0, si) {
 		## Build an adjacency matrix based on correlations
 		aj_adj = right_join(s0, si, by = 'document') %>% 
 			select(-document) %>%
 			cor
 		## Correlations within the same model fit should be 0
 		aj_adj[str_detect(rownames(aj_adj), 'x'),
 					  str_detect(colnames(aj_adj), 'x')] = 0
 		aj_adj[str_detect(rownames(aj_adj), 'y'),
 			   str_detect(colnames(aj_adj), 'y')] = 0
		
 		## To find the maximum, we build a bipartite graph and 
 		## use a bipartite matching algorithm
 		
 		## Build the graph
  		aj_graph = graph_from_adjacency_matrix(aj_adj, weighted = TRUE, 
  											   mode = 'upper')
  		## Set types based on model designator
  		V(aj_graph)$type = str_detect(V(aj_graph)$name, 'x')
  		## This gives the average correlation for the best match
  		max_bipartite_match(aj_graph)$matching_weight / k
 	}
 	
 	agree_scores = sapply(si, function (x) agreement(s0, x))
 	agree_scores
}

## Arrange agreement scores into a dataframe
agreement_scores = agree_scores %>% 
	as_tibble %>%
	melt %>%
	mutate(variable = {str_replace(variable, 'result.', '') %>%
			as.numeric %>% k_range[.]})

save(agreement_scores, file = 'agreement scores.Rdata')
} else {
	## If agreeement scores have already been calculated, use them
	load('agreement scores.Rdata')
	k_range = unique(agreement_scores$variable)
}


## Plot the results
# tikz(height = 5, width = 7, file = 'lda.tex', standAlone = TRUE)
lda_stability_plot = ggplot(agreement_scores, aes(variable, value)) + 
	geom_point() + 
	stat_summary(geom = 'line') +
	scale_x_continuous(name = 'k', breaks = k_range) +
	ylab('agreement score')
# dev.off()

## Since k=2 is the most stable, fit and save that model
## Note that the seed is the same as above
descriptions_lda = LDA(descriptions_dtm, k = 2, control = list(seed = 42))
# descriptions_lda_td = tidy(descriptions_lda)
# descriptions_lda_td %>%
#     group_by(topic) %>%
#     top_n(10, beta) %>%
#     ungroup() %>%
#     arrange(topic, -beta) %>%
#     View
# descriptions_lda_gamma = tidy(descriptions_lda, matrix = 'gamma') %>%
# 	spread(topic, gamma, sep = '.')
if (!file.exists('descriptions lda.Rdata')) {
	save(descriptions_lda, file = 'descriptions lda.Rdata')
}


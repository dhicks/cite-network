library(tidyverse)
library(igraph)
library(httr)


## Only run this if the descriptions data isn't available
if (!file.exists('scraped text.Rdata')) {


## Load graph and identify which DOIs to retrieve
net = read_graph('../2016-04-27/citenet0.out.graphml', format = 'graphml')
dataf = igraph::as_data_frame(net, what = 'vertices')
rm(net)

dois_to_retrieve = dataf %>% 
	filter(core) %>%
	.$doi


## Retrieve abstracts from the Elsevier API

## Get the API key
source('api key.R')

## Build URLs
## Abstract Retrieval API - quota of 10k
url_pre = 'https://api.elsevier.com/content/abstract/doi/'
url_post = paste('?apiKey=', api_key, '&',
				 'httpAccept=application%2Fjson', 
				 sep = '')

urls_to_retrieve = paste(url_pre, dois_to_retrieve, url_post, sep = '')

## Scrape description text
scrape = function (this_url) {
	print(this_url)
	response = GET(this_url)
	response_content = content(response)
	if (!is.null(response_content$`abstracts-retrieval-response`)) {
		## Case: Only 1 item in response
		response_content = response_content$`abstracts-retrieval-response`
	} else if (!is.null(response_content$`abstracts-retrieval-multidoc-response`)) {
		## Case:  Multiple items in response
		## We'll just go with the first one
		response_content = response_content$`abstracts-retrieval-multidoc-response`$`abstracts-retrieval-response`[[1]]
	} else {
		## If we're in some other case, raise an exception
		stop("Scrape received a response that couldn't be parsed")
	}
	if (!is.null(response_content$coredata$`dc:title`)) {
		title_text = response_content$coredata$`dc:title`
	} else {
		title_text = NA
	}
	if (!is.null(response_content$coredata$`dc:description`)) {
		description_text = response_content$coredata$`dc:description`
	} else {
		description_text = NA
	}
	# print(description_text)
	return(tibble(title = title_text, description = description_text))
}

scraped_text = lapply(urls_to_retrieve, scrape) %>% bind_rows

## Organize the scraped data into a data frame and save
scraped_text_df = tibble(doi = dois_to_retrieve, 
					  url = urls_to_retrieve) %>%
				cbind(descriptions) %>%
				filter(!duplicated(.))

save(scraped_text_df, file = 'scraped text.Rdata')
}


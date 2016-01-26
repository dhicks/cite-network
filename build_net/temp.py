import json
import pandas

data = pandas.read_excel('project leads.xlsx')
#print(data[['Scopus ID', 'Topic']])

sid_topic_df = data[['Scopus ID', 'Topic']].to_dict(orient = 'records')
sid_topic = {str(entry['Scopus ID']): entry['Topic'] for entry in sid_topic_df}
#print(sid_topic)

with open('papers.json') as readfile:
	papers = json.load(readfile)

core = [paper for paper in papers if paper['core']]
print(len(core))

assigned = 0
clash = 0
unassigned = 0
for paper in core:
	topic = None
	for author in paper['authors']:
		if author in sid_topic:
			if topic is None:
				topic = sid_topic[author]
				assigned += 1
			else:
				if topic != sid_topic[author]:
					clash += 1
	if topic is None:
		unassigned += 1
print(assigned)
print(clash)
print(unassigned)
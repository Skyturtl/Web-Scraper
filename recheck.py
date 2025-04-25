from database import create_connection, execute_query, update_child_links_batch, update_keyword_freq_batch, update_links_batch
from scraper import run_async_spider


all_links = {}

import time
start_time = time.time()  # Start the timer

# Fetch all last modified dates from the database
connection = create_connection("scraper.db")
last_modified_dates = {}
query = "SELECT url, last_mod_date FROM links"
results = execute_query(connection, query)

# Convert results to a dictionary
last_modified_dates = {url: date for url, date in results}

run_async_spider("testpage.htm", all_links, 300, last_modified_dates)

# Create a list of tuples for batch insertion
links_batch = []
keyword_freq_batch = []
child_links_batch = []

# Add the scraped data to the database
for endpoint, data in all_links.items():
  if not data:
    continue

  title = data['title'].replace("'", "''")
  stem_title = data['stem_title'].replace("'", "''")
  links_batch.append((data['index'], title, stem_title, data['last_mod_date'], data['size'], data['url']))

  parent_group = data['index']
  child_links_batch.extend((parent_group, link) for link in data['links'])

  keyword_counts = {keyword: data['keywords'].count(keyword) for keyword in set(data['keywords'])}
  keyword_freq_batch.extend((keyword, parent_group, count) for keyword, count in keyword_counts.items())

update_links_batch(connection, links_batch)
update_child_links_batch(connection, child_links_batch)
update_keyword_freq_batch(connection, keyword_freq_batch)   


end_time = time.time()  # End the timer
print(f"Execution time: {end_time - start_time:.2f} seconds")
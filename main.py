from database import create_connection, clear_database, create_table, add_links_batch, add_keyword_freq_batch, add_child_links_batch,add_index_body_positions_batch,add_index_title_positions_batch
from scraper import run_async_spider,get_inverted_index_body, get_inverted_index_title
from collections import defaultdict

# Database setup
#update Added parent links
create_links_table = """
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY,
  title TEXT,
  stem_title TEXT,
  url TEXT NOT NULL,
  last_mod_date TEXT,
  size INTEGER,
  parent_links TEXT  
);
"""

create_keywords_freq_table = """
CREATE TABLE IF NOT EXISTS keywords_freq (
  freq_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword text,
  parent_group INTEGER,
  frequency INTEGER,
  FOREIGN KEY (parent_group) REFERENCES links (id)
  FOREIGN KEY (keyword) REFERENCES keywords (keyword)
);
"""

create_child_links_table = """
CREATE TABLE IF NOT EXISTS child_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER,
  parent_group INTEGER,
  url TEXT NOT NULL,
  FOREIGN KEY (parent_group) REFERENCES links (id)
  ForeIGN KEY (child_id) REFERENCES links (id)
);
"""

#update
create_body_positions_table = """
CREATE TABLE IF NOT EXISTS body_positions (
    word TEXT,
    parent_group INTEGER,
    positions TEXT,  
    FOREIGN KEY (parent_group) REFERENCES links (id)
);
"""

create_title_positions_table = """
CREATE TABLE IF NOT EXISTS title_positions (
    word TEXT,
    parent_group INTEGER,
    positions TEXT,
    FOREIGN KEY (parent_group) REFERENCES links (id)
);
"""

connection = create_connection("scraper.db")
clear_database(connection)
create_table(connection, create_links_table)
create_table(connection, create_keywords_freq_table)
create_table(connection, create_child_links_table)
create_table(connection, create_body_positions_table)
create_table(connection, create_title_positions_table)

all_links = {}
import time
start_time = time.time()  # Start the timer

run_async_spider("testpage.htm", all_links, 300)

inverted_index_body = get_inverted_index_body()
inverted_index_title = get_inverted_index_title()
title_counts = defaultdict(dict)
for word, pages in inverted_index_title.items():
    for endpoint, positions in pages.items():
        title_counts[endpoint][word] = len(positions)

# Create a list of tuples for batch insertion
links_batch = []
keyword_freq_batch = []
child_links_batch = []
body_positions_batch = []
title_positions_batch = []

for word, pages in inverted_index_body.items():
    for endpoint, positions in pages.items():
        parent_group = all_links[endpoint]['index']
        if not isinstance(positions, list):
            positions = [positions]  # Ensure positions are a list
        body_positions_batch.append((word, parent_group, ",".join(map(str, positions))))

for word, pages in inverted_index_title.items():
    for endpoint, positions in pages.items():
        parent_group = all_links[endpoint]['index']
        if not isinstance(positions, list):
            positions = [positions]  # Ensure positions are a list
        title_positions_batch.append((word, parent_group, ",".join(map(str, positions))))


# Add the scraped data to the database
for endpoint, data in all_links.items():
  if not data:
    continue

  parent_group = data['index']
  title = data['title'].replace("'", "''")
  stem_title = data['stem_title'].replace("'", "''")
  parent_links = ";".join(data['parent'])
  links_batch.append((parent_group, title, stem_title, data['url'], data['last_mod_date'], data['size'], parent_links))
  #keyword_counts = {keyword: len(data['keywords'][keyword]) for keyword in data['keywords']}
  #keyword_freq_batch.extend((keyword, parent_group, count) for keyword, count in keyword_counts.items())
  body_counts = {kw: len(positions) for kw, positions in data['keywords'].items()}
  title_counts_for_endpoint = title_counts.get(endpoint, {})
    
  # Merge counts
  combined_counts = defaultdict(int)
  for kw, cnt in body_counts.items():
      combined_counts[kw] += cnt
  for kw, cnt in title_counts_for_endpoint.items():
      combined_counts[kw] += cnt
    
  # Add to keyword batch
  keyword_freq_batch.extend(
        (kw, parent_group, cnt) 
        for kw, cnt in combined_counts.items()
  )
add_links_batch(connection, links_batch) 

for endpoint, data in all_links.items():
  if not data:
    continue

  parent_group = data['index']
  for child_link in data['links']:
    if child_link in all_links:
      child_id = all_links[child_link]['index']
      child_links_batch.append((child_id, parent_group, child_link))
      
add_child_links_batch(connection, child_links_batch)
add_keyword_freq_batch(connection, keyword_freq_batch)   
# Insert the batches into the database
add_index_body_positions_batch(connection, body_positions_batch)
add_index_title_positions_batch(connection, title_positions_batch)

end_time = time.time()  # End the timer
print(f"Execution time: {end_time - start_time:.2f} seconds")
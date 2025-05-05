from database import create_connection, clear_database, create_table, add_links_batch, add_keyword_freq_batch, add_child_links_batch,add_index_body_positions_batch,add_index_title_positions_batch

from scraper import run_async_spider,get_inverted_index_body, get_inverted_index_title

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
  child_id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_group INTEGER,
  url TEXT NOT NULL,
  FOREIGN KEY (parent_group) REFERENCES links (id)
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

  child_links_batch.extend((parent_group, link) for link in data['links'])

  keyword_counts = {keyword: data['keywords'].count(keyword) for keyword in set(data['keywords'])}
  keyword_freq_batch.extend((keyword, parent_group, count) for keyword, count in keyword_counts.items())

add_links_batch(connection, links_batch) 
add_child_links_batch(connection, child_links_batch)
add_keyword_freq_batch(connection, keyword_freq_batch)   
# Insert the batches into the database
add_index_body_positions_batch(connection, body_positions_batch)
add_index_title_positions_batch(connection, title_positions_batch)

end_time = time.time()  # End the timer
print(f"Execution time: {end_time - start_time:.2f} seconds")
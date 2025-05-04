from database import create_connection, clear_database, create_table, add_links_batch, add_keyword_freq_batch, add_child_links_batch
from scraper import run_async_spider

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

connection = create_connection("scraper.db")
clear_database(connection)
create_table(connection, create_links_table)
create_table(connection, create_keywords_freq_table)
create_table(connection, create_child_links_table)

all_links = {}
import time
start_time = time.time()  # Start the timer

run_async_spider("testpage.htm", all_links, 300)

# Create a list of tuples for batch insertion
links_batch = []
keyword_freq_batch = []
child_links_batch = []

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

end_time = time.time()  # End the timer
print(f"Execution time: {end_time - start_time:.2f} seconds")
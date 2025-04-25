from database import create_connection, clear_database, execute_query, add_links_batch, add_keyword_freq_batch, add_child_links_batch, add_parent_links_batch
from scraper import run_async_spider
import sys

first = False
n = len(sys.argv)
if n == 2:
  if sys.argv[1] == "first":
    first = True
elif n == 1:
  pass
else:
  print("Invalid arguments. Usage: python main.py [first]")
  sys.exit(1)
  
connection = create_connection("scraper.db")
if first:
  # Database setup
  create_links_table = """
  CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    stem_title TEXT,
    url TEXT NOT NULL,
    last_mod_date TEXT,
    size INTEGER
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

  create_parent_links_table = """
  CREATE TABLE IF NOT EXISTS parent_links (
    parent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_group INTEGER,
    url TEXT NOT NULL,
    FOREIGN KEY (parent_group) REFERENCES links (id)
  );
  """

  clear_database(connection)
  execute_query(connection, create_links_table)
  execute_query(connection, create_keywords_freq_table)
  execute_query(connection, create_child_links_table)
  execute_query(connection, create_parent_links_table)

all_links = {}
import time
start_time = time.time()  # Start the timer

run_async_spider("testpage.htm", all_links, 300)

# Write the scraped data to a file in a readable format
with open("scraped_data.txt", "w", encoding="utf-8") as file:
  for endpoint, data in all_links.items():
    file.write(f"Endpoint: {endpoint}\n")
    if data:
      file.write(f"  Title: {data['title']}\n")
      file.write(f"  Stem Title: {data['stem_title']}\n")
      file.write(f"  URL: {data['url']}\n")
      file.write(f"  Last Modified Date: {data['last_mod_date']}\n")
      file.write(f"  Size: {data['size']}\n")
      file.write(f"  Links: {', '.join(data['links'])}\n")
      file.write(f"  Keywords: {', '.join(data['keywords'])}\n")
      file.write(f"  Parent: {', '.join(data['parent']) if data['parent'] else 'None'}\n")
    else:
      file.write("  No data available.\n")
    file.write("\n")

# Create a list of tuples for batch insertion
links_batch = []
keyword_freq_batch = []
child_links_batch = []
parent_links_batch = []

# Add the scraped data to the database
for endpoint, data in all_links.items():
  if data:
    title = data['title'].replace("'", "''")
    stem_title = data['stem_title'].replace("'", "''")
    links_batch.append((title, stem_title, data['url'], data['last_mod_date'], data['size']))
    
    parent_group = data['index']
    for link in data['links']:
      child_links_batch.append((parent_group, link))
    
    temp = set()
    for keyword in data['keywords']:
      if keyword not in temp:
        temp.add(keyword)
        keyword_freq_batch.append((keyword, parent_group, data['keywords'].count(keyword)))
    
    if data['parent']:
      for parent in data['parent']:
        parent_links_batch.append((parent_group, parent))
    else:
      parent_links_batch.append((parent_group, None))

add_links_batch(connection, links_batch)
add_parent_links_batch(connection, parent_links_batch)   
add_child_links_batch(connection, child_links_batch)
add_keyword_freq_batch(connection, keyword_freq_batch)   

end_time = time.time()  # End the timer
print(f"Execution time: {end_time - start_time:.2f} seconds")
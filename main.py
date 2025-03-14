from database import create_connection, clear_database, execute_query, add_link, add_keyword, add_child_link, add_parent_link
from scraper import spider

# Database setup
create_links_table = """
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  url TEXT NOT NULL,
  last_mod_date TEXT,
  size INTEGER
);
"""

create_keywords_table = """
CREATE TABLE IF NOT EXISTS keywords (
  keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_group INTEGER,
  keyword TEXT,
  FOREIGN KEY (parent_group) REFERENCES links (id)
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

connection = create_connection("scraper.db")
clear_database(connection)
execute_query(connection, create_links_table)
execute_query(connection, create_keywords_table)
execute_query(connection, create_child_links_table)
execute_query(connection, create_parent_links_table)

all_links = {}

# Start the scraper
spider("testpage.htm", all_links, "", 10)

# Add the scraped data to the database
for endpoint, data in all_links.items():
  if data:
    add_link(connection, data['title'], data['url'], data['last_mod_date'], data['size'])
    parent_group = data['index']
    for link in data['links']:
      add_child_link(connection, parent_group, link)
    for keyword in data['keywords']:
      add_keyword(connection, parent_group, keyword)
    if data['parent']:
      for parent in data['parent']:
        add_parent_link(connection, parent_group, parent)
    else:
      add_parent_link(connection, parent_group, None)

# Print the database
cursor = connection.cursor()
cursor.execute("SELECT title, url FROM links")
print("Links:")
for row in cursor.fetchall():
  print(row)
cursor.execute("SELECT * FROM keywords")
print("\nKeywords:")
for row in cursor.fetchall():
  print(row)
cursor.execute("SELECT * FROM child_links")
print("\nChild Links:")
for row in cursor.fetchall():
  print(row)
cursor.execute("SELECT * FROM parent_links")
print("\nParent Links:")
for row in cursor.fetchall():
  print(row)
connection.close()
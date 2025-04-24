import sqlite3
from sqlite3 import Error

def create_connection(path):
  connection = None
  try:
    connection = sqlite3.connect(path)
    print("Connection to SQLite DB successful")
  except Error as e:
    print(f"The error '{e}' occurred")

  return connection
  
def execute_query(connection, query):
  cursor = connection.cursor()
  try:
    cursor.execute(query)
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")

def clear_database(connection):
  cursor = connection.cursor()
  try:
    cursor.execute("DROP TABLE IF EXISTS links")
    cursor.execute("DROP TABLE IF EXISTS keywords")
    cursor.execute("DROP TABLE IF EXISTS child_links")
    cursor.execute("DROP TABLE IF EXISTS parent_links")
    cursor.execute("DROP TABLE IF EXISTS keywords_freq")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    
def add_links_batch(connection, links):
  cursor = connection.cursor()
  try:
    cursor.executemany(
      """
      INSERT INTO links (title, stem_title, url, last_mod_date, size) 
      VALUES (?, ?, ?, ?, ?)
      """, 
      links
    )
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    
def add_keyword_freq_batch(connection, keyword_freqs):
  cursor = connection.cursor()
  try:
    cursor.executemany(
      """
      INSERT INTO keywords_freq (keyword, parent_group, frequency) 
      VALUES (?, ?, ?)
      """, 
      keyword_freqs
    )
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")

def add_child_links_batch(connection, child_links):
  cursor = connection.cursor()
  try:
    cursor.executemany(
      """
      INSERT INTO child_links (parent_group, url) 
      VALUES (?, ?)
      """, 
      child_links
    )
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")

def add_parent_links_batch(connection, parent_links):
  cursor = connection.cursor()
  try:
    cursor.executemany(
      """
      INSERT INTO parent_links (parent_group, url) 
      VALUES (?, ?)
      """, 
      parent_links
    )
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
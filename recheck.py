from database import create_connection, clear_database, execute_query, add_links_batch, add_keyword_freq_batch, add_child_links_batch, add_parent_links_batch
from scraper import run_async_spider


all_links = {}

# Fetch all last modified dates from the database
connection = create_connection("scraper.db")
last_modified_dates = {}
query = "SELECT url, last_mod_date FROM links"
results = execute_query(connection, query)

# Convert results to a dictionary
last_modified_dates = {url: date for url, date in results}

run_async_spider("testpage.htm", all_links, 300, last_modified_dates)


# Web-Scraper
For HKUST class COMP4321 <br> By: William Chen, Po Wa Ho, Fung Ming Sze

## Prerequisites:
- Python 3.x
- Required Python libraries(requests, beautifulsoup4, nltk, sqlite3, aiohttp)
- Internet connection (for downloading NLTK tokenizer)
  
## Project Structure: 
- main.py
- scraper.py
- database.py
- stopwords.txt
- scraper.db
- spider_result.py
- spider_result.txt

## Design Choices:
- The database schema and design is explained in the document `Database_design.docx`.
- The pages are crawled through based on a priority queue/bfs implementation.
- Symbols were removed after tokenizing the content of the page because it was creating problems with the SQL queries as well as having many symbols to have to sort through, may revisit this problem in the second phase.
- Numbers were kept as some have a deeper meaning such as year or as a page title.
- A copy of stemmed page titles are stored in a database for future use if needed.
- The child list currently is stored as a list of endpoints but simply because I don't have time to rewrite this section, when outputted they are reformatted to include the full url. 
- Added ve to the stopwords list as you've or other words that end in 've are non-important and additionally ve just means have.

## How to run:
To build and execute the web crawler, start by setting up the database. 
1. Download all the necessary libraries as listed in [Prerequisites](#prerequisites)
   1. Can be done using **`pip install <library_name>`**
3. Ensure that `scraper.db` and `spider_result.txt` does not exist if you want a fresh run. 
   1. This is only for clairty purposes, the table is cleared each run and the text file is overwritten
4. Run the command **`python main.py`** to initialize the database and start the web crawler. 
   1. This command will create the necessary tables in the SQLite database, begin crawling from the specified seed URL (defined in `main.py`), and store the extracted data, including links, keywords, and parent-child relationships, in `scraper.db`.
5. Run **`python spider_result.py`**
   1. After we have indexed all the necessary pages and generated a corresponding database, we need to generate the spider result. This command will fetch the indexed data from the database and create a formatted `spider_result.txt` file that contains the pages, keywords, and child links.
6. Finally, you can view the output. The `scraper.db` file will contain the indexed data, while the `spider_result.txt` file will hold the final results in the required format.

## Specifications:
May need to use `py -m pip install <library>` and `py <file_name.py>` instead of `python` because of PATH issues. 

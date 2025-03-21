# Web-Scraper
For HKUST class COMP4321

Prerequisites:**Python 3.x,Required Python libraries(requests,beautifulsoup4,nltk,sqlite3),Internet connection (for downloading NLTK tokenizer)**

Project Structure:**main.py,scraper.py,database.py,stopwords.txt,scraper.db,spider_result.py,spider_result.txt**

To build and execute the web crawler, start by setting up the database. First, ensure that `scraper.db` does not exist if you want a fresh run. Then, run the command **`python main.py`** to initialize the database and start the web crawler. This command will create the necessary tables in the SQLite database, begin crawling from the specified seed URL (defined in `main.py`), and store the extracted data, including links, keywords, and parent-child relationships, in `scraper.db`.

Once the crawler has indexed the pages, the next step is to generate the spider result. To do this, run **`python spider_result.py`**, which will fetch the indexed data from the database and create a formatted `spider_result.txt` file that contains the pages, keywords, and child links.

Finally, you can view the output. The `scraper.db` file will contain the indexed data, while the `spider_result.txt` file will hold the final results in the required format.

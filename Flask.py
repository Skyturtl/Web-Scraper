import sqlite3
import math
from flask import Flask, request, render_template

app = Flask(__name__)

# Modified calculate_tfidf function
def calculate_tfidf(query):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    query_terms = query.lower().split()
    cursor.execute("SELECT COUNT(*) FROM links")
    total_documents = int(cursor.fetchone()[0])

    doc_scores = {}
    total_freqs = {}  # Track total keyword appearances
    calc_details = {}  # Store calculation details

    for term in query_terms:
        condition = "LIKE"
        term_value = f"%{term}%"

        # Get document count containing the term
        cursor.execute(f"""
            SELECT COUNT(DISTINCT parent_group) FROM keywords_freq WHERE keyword {condition} ?
        """, (term_value,))
        doc_count = cursor.fetchone()[0] or 1

        # Calculate IDF
        idf = math.log(total_documents / doc_count) if doc_count else 0

        # Get term frequencies
        cursor.execute(f"""
            SELECT parent_group, frequency FROM keywords_freq WHERE keyword {condition} ?
        """, (term_value,))
        term_data = cursor.fetchall()

        for parent_group, frequency in term_data:
            # Get total terms in document
            cursor.execute("""
                SELECT SUM(frequency) FROM keywords_freq WHERE parent_group = ?
            """, (parent_group,))
            total_terms = cursor.fetchone()[0] or 1

            # Calculate TF and TF-IDF
            tf = frequency / total_terms
            tfidf = tf * idf

            # Store calculation details
            calc_details.setdefault(parent_group, {}).setdefault(term, {
                'tf': round(tf, 4),
                'idf': round(idf, 4),
                'tfidf': round(tfidf, 4),
                'doc_count': doc_count,
                'total_terms': total_terms,
                'term_freq': frequency
            })

            # Update scores and frequencies
            doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
            total_freqs[parent_group] = total_freqs.get(parent_group, 0) + frequency

    # Normalize scores
    if query_terms:
        num_terms = len(query_terms)
        for doc in doc_scores:
            doc_scores[doc] /= num_terms

    conn.close()
    return doc_scores, total_freqs, calc_details, total_documents

def fetch_ranked_results(query):
    doc_scores, total_freqs, calc_details, total_docs = calculate_tfidf(query)
    ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    for rank, (parent_group, score) in enumerate(ranked_docs[:50], start=1):
        # Fetch the page details from the links table
        cursor.execute("""
            SELECT title, url, last_mod_date, size FROM links WHERE id = ?
        """, (parent_group,))
        link_row = cursor.fetchone()
        if not link_row:
            continue
        title, url, last_mod_date, size = link_row

        # Fetch up to 5 most frequent keywords for the parent group
        cursor.execute("""
            SELECT keyword, frequency FROM keywords_freq 
            WHERE parent_group = ? 
            ORDER BY frequency DESC LIMIT 5
        """, (parent_group,))
        keywords = cursor.fetchall()
        keyword_details = "; ".join([f"{kw} {freq}" for kw, freq in keywords])

        # Fetch all parent links
        cursor.execute("""
            SELECT url FROM links WHERE id = ?
        """, (parent_group,))
        parent_links = [row[0] for row in cursor.fetchall()]

        # Fetch all child links
        cursor.execute("""
            SELECT url FROM child_links WHERE parent_group = ?
        """, (parent_group,))
        child_links = [row[0] for row in cursor.fetchall()]

        # Add the result in the required format
        results.append({
            "rank": rank,
            "score": round(score, 3),
            "keyword_count": total_freqs.get(parent_group, 0),
            "calc_details": calc_details.get(parent_group, {}),
            "total_docs": total_docs,
            "page_detail": {
                "title": title,
                "url": url,
                "last_modified": last_mod_date,
                "size": size,
                "keywords": keyword_details,
                "parent_links": parent_links,
                "child_links": child_links
            }
        })

    conn.close()
    return results

def fetch_similar_pages(url):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    # Fetch keywords for the given URL
    cursor.execute("""
        SELECT parent_group FROM links WHERE url = ?
    """, (url,))
    parent_group = cursor.fetchone()
    if not parent_group:
        conn.close()
        return []

    cursor.execute("""
        SELECT keyword FROM keywords_freq WHERE parent_group = ?
    """, (parent_group[0],))
    keywords = [row[0] for row in cursor.fetchall()]

    # Fetch pages that share these keywords
    results = []
    for keyword in keywords:
        cursor.execute("""
            SELECT DISTINCT parent_group FROM keywords_freq WHERE keyword = ?
        """, (keyword,))
        related_groups = cursor.fetchall()
        for group in related_groups:
            if group[0] != parent_group[0]:
                cursor.execute("""
                    SELECT title, url FROM links WHERE id = ?
                """, (group[0],))
                link_row = cursor.fetchone()
                if link_row:
                    results.append({
                        "title": link_row[0],
                        "url": link_row[1]
                    })

    conn.close()
    return results

@app.route("/index.html", methods=["GET", "POST"])
def index():
    results = []
    similar_pages = []
    query = ""

    if request.method == "POST":
        query = request.form["query"]
        sort_order = request.form.get("sort_order", "desc")
        results = fetch_ranked_results(query)

        # Fetch similar pages if a URL is clicked
        similar_url = request.form.get("similar_url")
        if similar_url:
            similar_pages = fetch_similar_pages(similar_url)

    return render_template(
        "index.html",
        query=query,
        results=results,
        similar_pages=similar_pages
    )
if __name__ == "__main__":
    app.run(debug=True)

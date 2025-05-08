import sqlite3
import math
from flask import Flask, request, render_template,session
import re
from collections import Counter  
from textblob import TextBlob  # Add this for spelling correction
import time  # Add this import at the top

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

# Helper function to find the longest matching stem in the database
def find_stem_in_database(term, cursor):
    while len(term) > 1:  # Stop if the term length is 1 and still no match
        # Query the database for the current term
        cursor.execute("""
            SELECT COUNT(*) FROM keywords_freq WHERE keyword LIKE  ?
        """, (term,))   # Use wildcard to match stems
        if cursor.fetchone()[0] > 0:  # If there is at least one match
            return term  # Return the matched stem
        term = term[:-1]  # Remove the last character and continue
    return term  # Return the shortest form if no match is found

# Spelling correction helper function
def suggest_correction(query):
    """Suggest spelling corrections for the given query."""
    blob = TextBlob(query)
    corrected_query = str(blob.correct())  # Automatically correct the query
    return corrected_query if corrected_query.lower() != query.lower() else None

# Helper function to extract phrases and terms
def extract_phrases_and_terms(query):
    phrases = re.findall(r'"(.*?)"', query)
    remaining_query = re.sub(r'"(.*?)"', '', query).strip()
    terms = re.findall(r'\b\w+\b', remaining_query)
    phrase_terms = set()
    for phrase in phrases:
        terms_in_phrase = re.findall(r'\b\w+\b', phrase)
        phrase_terms.update(terms_in_phrase)
    terms = [term for term in terms if term not in phrase_terms]
    return phrases, terms

# Cosine Similarity Function
def calculate_cosine_similarity(query_vector, doc_vector):
    """Calculate cosine similarity between query and document vectors."""
    # Compute dot product
    dot_product = sum(query_vector[key] * doc_vector.get(key, 0) for key in query_vector)
    # Compute magnitudes
    query_magnitude = math.sqrt(sum(value**2 for value in query_vector.values()))
    doc_magnitude = math.sqrt(sum(value**2 for value in doc_vector.values()))
    # Avoid division by zero
    if query_magnitude == 0 or doc_magnitude == 0:
        return 0
    return dot_product / (query_magnitude * doc_magnitude)


# Calculate TF-IDF function 
def calculate_tfidf(query,title_boost_factor=3):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()
    phrases, query_terms = extract_phrases_and_terms(query)
    cursor.execute("SELECT COUNT(*) FROM links")
    total_documents = int(cursor.fetchone()[0])

    doc_scores = {}
    total_freqs = {}
    calc_details = {}
    query_vector = Counter(phrases+query_terms)  # For cosine similarity
    phrase_docs_list = []

    # Process phrases
    for phrase in phrases:
        phrase_terms = phrase.split()
        phrase_docs = set()
        total_occurrences = Counter()

        # Check both body and title positions
        for table in ['body_positions', 'title_positions']:
            # Get positions for each term in the phrase
            term_positions = {}
            for term in phrase_terms:
                cursor.execute(f"""
                    SELECT parent_group, positions FROM {table} WHERE word = ?
                """, (term,))
                term_positions[term] = {}
                for parent_group, positions in cursor.fetchall():
                    term_positions[term][parent_group] = list(map(int, positions.split(',')))

            # Find matching documents with consecutive positions
            for parent_group in set.intersection(*[set(term_positions[t].keys()) for t in phrase_terms]):
                all_positions = [term_positions[t][parent_group] for t in phrase_terms]
                
                # Check for consecutive sequences
                occurrences = 0
                for first_pos in all_positions[0]:
                    consecutive = True
                    for i in range(1, len(phrase_terms)):
                        if (first_pos + i) not in all_positions[i]:
                            consecutive = False
                            break
                    if consecutive:
                        occurrences += 1
                
                if occurrences > 0:
                    phrase_docs.add(parent_group)
                    total_occurrences[parent_group] += occurrences

        # Calculate TF-IDF for matching documents
        doc_count = len(phrase_docs) or 1
        idf = math.log(total_documents / doc_count)

        for parent_group in phrase_docs:
            # Get total terms in document
            cursor.execute("""
                SELECT SUM(frequency) FROM keywords_freq WHERE parent_group = ?
            """, (parent_group,))
            total_terms = cursor.fetchone()[0] or 1

            # Calculate TF and TF-IDF
            tf = total_occurrences[parent_group] / total_terms
            tfidf = tf * idf

            # Check if phrase appears in title
            boost_applied = False
            cursor.execute("""
                SELECT stem_title FROM links WHERE id = ?
            """, (parent_group,))
            title = cursor.fetchone()
            if title and all(t in title[0].lower() for t in phrase_terms):
                tfidf *= title_boost_factor
                boost_applied = True

            # Update scores and details
            doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
            calc_details.setdefault(parent_group, {}).setdefault(phrase, {
                'tf': round(tf, 4),
                'idf': round(idf, 4),
                'tfidf': round(tfidf, 4),
                'doc_count': doc_count,
                'occurrences': total_occurrences[parent_group],
                'boost_applied': boost_applied
            })
            

        # Process individual terms
    for term in query_terms:
        #condition = "LIKE"
        #term_value = f"%{term}%"
        original_term = term
        matching_stem = find_stem_in_database(term, cursor)

        # Get document count containing the term
        cursor.execute("""
        SELECT COUNT(DISTINCT parent_group) FROM keywords_freq WHERE keyword = ?
        """, (matching_stem,))
        doc_count = cursor.fetchone()[0] or 1

        # Calculate IDF
        idf = math.log(total_documents / doc_count) if doc_count else 0

        # Get term frequencies
        cursor.execute("""
        SELECT parent_group, frequency FROM keywords_freq WHERE keyword = ?
        """, (matching_stem,))
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

            # Check if the term is in the title for Title Match Boosting
            cursor.execute(f"""
                SELECT stem_title FROM links WHERE id = ?
            """, (parent_group,))
            title = cursor.fetchone()
            boost_applied = False
            if title and term in title[0].lower():
                tfidf *= title_boost_factor  # Apply the boost factor
                boost_applied = True  # Mark that boost was applied

            # Store calculation details
            calc_details.setdefault(parent_group, {}).setdefault(matching_stem, {
                'tf': round(tf, 4),
                'idf': round(idf, 4),
                'tfidf': round(tfidf, 4),
                'doc_count': doc_count,
                'total_terms': total_terms,
                'term_freq': frequency,
                'boost_applied': boost_applied  # Add boost visibility
            })

            # Update scores and frequencies
            doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
            total_freqs[parent_group] = total_freqs.get(parent_group, 0) + frequency

    # Normalize scores
    if query_terms or phrases:
        for doc, score in doc_scores.items():
            doc_vector = Counter(calc_details[doc].keys())
            doc_scores[doc] = calculate_cosine_similarity(query_vector, doc_vector) * score

    conn.close()
    return doc_scores, total_freqs, calc_details, total_documents

# Fetch ranked results
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
        base_url = "https://www.cse.ust.hk/~kwtleung/COMP4321/"

        # Fetch all parent links
        cursor.execute("""
            SELECT parent_links FROM links WHERE id = ?
        """, (parent_group,))
        row = cursor.fetchone()
        parent_links_str = row[0] if row else ""
        parent_links = [base_url + link for link in parent_links_str.split(';')] if parent_links_str else []

        # Fetch all child links
        cursor.execute("""
            SELECT url FROM child_links WHERE parent_group = ?
        """, (parent_group,))
        child_links = [base_url + row[0] for row in cursor.fetchall()]

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

@app.route("/index.html", methods=["GET", "POST"])
def index():
    results = []
    query = ""
    suggestion = None  # Variable to hold spelling suggestions
    apply_correction = session.get("apply_correction", "yes")  # Default to "yes"
    search_time = None

    if request.method == "POST":
        query = request.form["query"]
        apply_correction = request.form.get("apply_correction", "yes")
        session["apply_correction"] = apply_correction
    else:  # GET request
        query = request.args.get("query", "")
    
    if query:
        start_time = time.time()
        if apply_correction == "yes":
            suggestion = suggest_correction(query)
            query_to_use = suggestion if suggestion else query
        else:
            query_to_use = query

        results = fetch_ranked_results(query_to_use) 
        end_time = time.time()  # Record end time
        search_time = round(end_time - start_time, 2) 
              
        #results = fetch_ranked_results(query, mode)

    return render_template(
        "index.html",
        query=query,
        results=results,
        suggestion=suggestion,
        apply_correction=apply_correction,
        search_time=search_time
    )

if __name__ == "__main__":
    app.run(debug=True)
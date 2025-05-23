import sqlite3
import math
from flask import Flask, request, render_template,session
import re
from collections import Counter  
from textblob import TextBlob
import time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

def normalize_text(text):
    return text.lower() if text else ""

# Helper function to find the longest matching stem in the database
def find_stem_in_database(term, cursor):
    term = normalize_text(term)
    while len(term) > 1:  # Stop if the term length is 1 and still no match
        # Query the database for the current term
        cursor.execute("""
            SELECT COUNT(*) FROM keywords_freq WHERE LOWER(keyword) LIKE  ?
        """, (term,))   # Use wildcard to match stems
        if cursor.fetchone()[0] > 0:  # If there is at least one match
            return term  # Return the matched stem
        term = term[:-1]  # Remove the last character and continue
    return term  # Return the shortest form if no match is found

# Spelling correction helper function
def suggest_correction(query):
    """Suggest spelling corrections for the given query."""
    query = normalize_text(query)
    blob = TextBlob(query)
    corrected_query = str(blob.correct())  # Automatically correct the query
    return corrected_query if corrected_query.lower() != query.lower() else None

# Helper function to extract phrases and terms
def extract_phrases_and_terms(query):
    query = normalize_text(query)
    
    negative_terms = re.findall(r'\s-\s*(\w+)', query)
    query = re.sub(r'\s-\s*\w+', '', query)
    quoted_phrases = re.findall(r'"(.*?)"', query)
    remaining_query = re.sub(r'"(.*?)"', '', query)
    
    tokens = re.findall(r'\*{1,3}|\b\w+\b', remaining_query.strip())
    
    phrases = quoted_phrases
    wildcard_sequences = []  # only contain wildcard
    query_terms = []  # only query
    
    current_sequence = []
    for token in tokens:
        if token.startswith('*'):
            # if * was found, create new wildcard
            if current_sequence and current_sequence[-1]['type'] == 'terms':
                query_terms.extend(current_sequence[-1]['value'])  # extract query
                current_sequence = []
            current_sequence.append({
                'type': 'wildcard',
                'pattern': token,
                'min_gap': 1 if len(token) == 1 else 4 if len(token) == 2 else 7,
                'max_gap': 3 if len(token) == 1 else 6 if len(token) == 2 else 9
            })
        else:
            # query: if has wildcard, append wildcard query. Else normal query
            if current_sequence and any(item['type'] == 'wildcard' for item in current_sequence):
                if current_sequence and current_sequence[-1]['type'] == 'terms':
                    current_sequence[-1]['value'].append(token)
                else:
                    current_sequence.append({'type': 'terms', 'value': [token]})
            else:
                query_terms.append(token)
    
    # remained query
    if current_sequence and not any(item['type'] == 'wildcard' for item in current_sequence):
        query_terms.extend([t for item in current_sequence if item['type'] == 'terms' for t in item['value']])
    else:
        wildcard_sequences = [current_sequence] if current_sequence else []
    
    return phrases, wildcard_sequences, query_terms, negative_terms

def find_wildcard_matches(parent_group, sequence, cursor):
    """Check if a document matches a wildcard sequence and return occurrences."""
    processed_sequence = []
    for item in sequence:
        if item['type'] == 'terms':
            for term in item['value']:
                processed_sequence.append({'type': 'term', 'value': term})
        else:
            processed_sequence.append(item)
    
    positions = {}

    for item in processed_sequence:
        if item['type'] != 'term':
            continue

        term = item['value']
        cursor.execute("""
            SELECT positions FROM body_positions 
            WHERE parent_group = ? AND LOWER(word) = ?
            UNION ALL
            SELECT positions FROM title_positions 
            WHERE parent_group = ? AND LOWER(word) = ?
        """, (parent_group, term, parent_group, term))
        pos_list = []
        for row in cursor.fetchall():
            pos_list.extend(map(int, row[0].split(',')))
        positions[term] = sorted(pos_list)
    
    from collections import deque
    queue = deque([(0, -1)])  # (sequence_index, last_position)
    matches = 0
    
    while queue:
        idx, last_pos = queue.popleft()
        if idx >= len(processed_sequence):
            matches += 1
            continue
        
        current = processed_sequence[idx]
        if current['type'] == 'term':
            term_pos = positions.get(current['value'], [])
            for pos in term_pos:
                if last_pos == -1 or pos > last_pos:
                    queue.append((idx + 1, pos))
        elif current['type'] == 'wildcard':
            # Generate every possible gap
            for gap in range(current['min_gap'], current['max_gap'] + 1):
                queue.append((idx + 1, last_pos + gap + 1))
    
    return matches

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

# Helper function to find consecutive positions
def find_consecutive_positions(positions_list):
    """Returns the number of times the phrase appears consecutively in the document."""
    if not positions_list:
        return 0
    first_term_pos = positions_list[0]
    count = 0
    for pos in first_term_pos:
        is_consecutive = True
        for i in range(1, len(positions_list)):
            if (pos + i) not in positions_list[i]:
                is_consecutive = False
                break
        if is_consecutive:
            count += 1
    return count


# Calculate TF-IDF function 
def calculate_tfidf(query,title_boost_factor=3):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()
    phrases, wildcard_sequences, query_terms, negative_terms = extract_phrases_and_terms(query)
    cursor.execute("SELECT COUNT(*) FROM links")
    total_documents = int(cursor.fetchone()[0])

    doc_scores = {}
    total_freqs = {}
    calc_details = {}
    query_vector = Counter(phrases+query_terms)  # For cosine similarity
    phrase_docs_list = {phrase: set() for phrase in phrases}
    wildcard_doc_sets = []

    final_required_docs = None
    has_special_criteria = False

    # Extract negative match
    negative_docs = set()
    for neg_term in negative_terms:
        matching_stem = find_stem_in_database(neg_term, cursor)
        cursor.execute("""
            SELECT parent_group FROM keywords_freq WHERE LOWER(keyword) = ?
        """, (matching_stem,))
        negative_docs.update([row[0] for row in cursor.fetchall()])
    

    def process_term_or_phrase(term, is_phrase=False):
        term_docs = set()
        term_occurrences = Counter()
        phrase_terms = term.split()

        if is_phrase:
            # Check both body and title positions
            for table in ['body_positions', 'title_positions']:
                # Get positions for each term in the phrase
                term_positions = {}
                for t in phrase_terms:
                    cursor.execute(f"""
                        SELECT parent_group, positions FROM {table} WHERE LOWER(word) = ?
                    """, (t,))
                    term_positions[t] = {}
                    for parent_group, positions in cursor.fetchall():
                        term_positions[t][parent_group] = list(map(int, positions.split(',')))
                
                # Find matching documents with consecutive positions
                common_docs = set.intersection(*[set(term_positions[t].keys()) for t in phrase_terms])
                for pg in common_docs:
                    positions_list = [term_positions[t][pg] for t in phrase_terms]
                    # Check for consecutive positions (e.g., term1 at pos i, term2 at i+1, ...)
                    consecutive_occurrences = find_consecutive_positions(positions_list)
                    if consecutive_occurrences > 0:
                        term_docs.add(pg)
                        term_occurrences[pg] += consecutive_occurrences

            phrase_docs_list[term].update(term_docs)
        else:
            matching_stem = find_stem_in_database(term, cursor)
            
            # Get document count containing the term
            cursor.execute("""
                SELECT parent_group, frequency FROM keywords_freq WHERE LOWER(keyword) = ?
            """, (matching_stem,))
            
            for parent_group, frequency in cursor.fetchall():
                term_docs.add(parent_group)
                term_occurrences[parent_group] = frequency
        
        # Calculate TF-IDF for matching documents
        doc_count = len(term_docs) or 1
        idf = math.log(total_documents / doc_count) if doc_count else 0
        
        for parent_group in term_docs:
            # Get total terms in document
            cursor.execute("""
                SELECT SUM(frequency) FROM keywords_freq WHERE parent_group = ?
            """, (parent_group,))
            total_terms = cursor.fetchone()[0] or 1
            
            # Calculate TF and TF-IDF
            tf = term_occurrences[parent_group] / total_terms
            tfidf = tf * idf
            
            # Check if the term is in the title for Title Match Boosting
            boost_applied = False
            cursor.execute("""SELECT stem_title FROM links WHERE id = ?""", (parent_group,))
            title = cursor.fetchone()[0] or ""
            title = normalize_text(title)
            title_terms = title.split()
            is_title_match = all(
                title_terms[i] == phrase_terms[i]
                for i in range(len(phrase_terms))
                if (i + len(phrase_terms)) <= len(title_terms)
            )
            if is_title_match:
                tfidf *= title_boost_factor
            
            # Store calculation details
            doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
            calc_details.setdefault(parent_group, {})[term] = {
                'tf': round(tf, 4),
                'idf': round(idf, 4),
                'tfidf': round(tfidf, 4),
                'doc_count': doc_count,
                'boost_applied': boost_applied
            }
    
    # Process wildcard sequences
    def process_wildcard_sequence(seq):
        term_docs = set()
        term_occurrences = Counter()
        cursor.execute("SELECT id FROM links")
        for doc in cursor.fetchall():
            doc_id = doc[0]
            matches = find_wildcard_matches(doc_id, seq, cursor)
            if matches > 0:
                term_docs.add(doc_id)
                term_occurrences[doc_id] = matches

        doc_count = len(term_docs) or 1
        idf = math.log(total_documents / doc_count) if doc_count else 0
        
        for parent_group in term_docs:
            cursor.execute("SELECT SUM(frequency) FROM keywords_freq WHERE parent_group = ?", (parent_group,))
            total_terms = cursor.fetchone()[0] or 1
            tf = term_occurrences[parent_group] / total_terms
            tfidf = tf * idf
            doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
        
        return term_docs

    # Process all wildcard sequence
    for seq in wildcard_sequences:
        print("debug1")
        matched_docs = process_wildcard_sequence(seq)
        wildcard_doc_sets.append(matched_docs)
 
    if wildcard_doc_sets and any(wildcard_doc_sets):
        required_wildcard_docs = set.intersection(*[set(docs) for docs in wildcard_doc_sets if docs])
        has_special_criteria = True
    else:
        required_wildcard_docs = None
    
    # Execute "process phrase and term"
    for phrase in phrases:
        process_term_or_phrase(phrase, is_phrase=True)
    for term in query_terms:
        process_term_or_phrase(term, is_phrase=False)

    # Filter doc without phrase
    if phrases:
        required_phrase_docs = set.intersection(*[docs for docs in phrase_docs_list.values() if docs])
        has_special_criteria = True
    else:
        required_phrase_docs = None

    # Every special critiria
    if has_special_criteria:
        final_required_docs = set()
        if required_wildcard_docs is not None:
            final_required_docs.update(required_wildcard_docs)
        if required_phrase_docs is not None:
            if final_required_docs:
                final_required_docs.intersection_update(required_phrase_docs)
            else:
                final_required_docs.update(required_phrase_docs)
    
    if final_required_docs is not None:
        doc_scores = {k: v for k, v in doc_scores.items() if k in final_required_docs}

    if doc_scores and negative_docs:
        doc_scores = {k: v for k, v in doc_scores.items() if k not in negative_docs}
    
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
    results_count = 0  # Initialize results count

    if "query_history" not in session:
        session["query_history"] = []


    if request.method == "POST":
        if 'keywords' in request.form:
            # Extract keywords and convert to space-separated terms
            keywords_str = request.form['keywords']
            keyword_entries = [entry.strip() for entry in keywords_str.split(';') if entry.strip()]
            query = ' '.join([entry.split()[0] for entry in keyword_entries])
            apply_correction = "no"  # Disable correction for keyword-based search
        # Handle regular search
        else:
            query = request.form.get("query", "")
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
        results_count = "50+" if len(results) >= 50 else len(results)
        
        end_time = time.time()  # Record end time
        search_time = round(end_time - start_time, 2) 
        
        query_item = {
            "query": query,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        session["query_history"].append(query_item)
        session.modified = True               
        
        #results = fetch_ranked_results(query, mode)

    return render_template(
        "index.html",
        query=query,
        results=results,
        suggestion=suggestion,
        apply_correction=apply_correction,
        search_time=search_time,
        results_count=results_count,
        query_history=session.get("query_history", []),
    )

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from dotenv import load_dotenv
import uuid
import requests
import random
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('db/quiz.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        points INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        topic TEXT,
        score INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            username = request.form['username']
            password = request.form['password']
            conn = sqlite3.connect('db/quiz.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = c.fetchone()
            conn.close()
            if user:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['seen_questions'] = []  # Initialize seen questions
                return render_template('quiz.html', step='select_topic')
            else:
                flash("Invalid credentials. Register or try again.")
                return render_template('quiz.html', step='login')
        elif action == 'register':
            username = request.form['username']
            password = request.form['password']
            user_id = str(uuid.uuid4())
            conn = sqlite3.connect('db/quiz.db')
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (id, username, password, points) VALUES (?, ?, ?, 0)", (user_id, username, password))
                conn.commit()
                session['user_id'] = user_id
                session['username'] = username
                session['seen_questions'] = []
                return render_template('quiz.html', step='select_topic')
            except sqlite3.IntegrityError:
                flash("Username already exists.")
                conn.close()
                return render_template('quiz.html', step='login')
            conn.close()
        elif action == 'start_quiz':
            topic = request.form.getlist('topic')  # Allow multiple topics
            if not topic:
                flash("Please select at least one topic.")
                return render_template('quiz.html', step='select_topic')
            questions = generate_quiz_questions(topic)
            session['questions'] = questions
            session['current_question'] = 0
            session['score'] = 0
            session['user_answers'] = []
            return render_template('quiz.html', step='question', question=questions[0], question_num=1, total_questions=len(questions))
        elif action == 'answer':
            answer = request.form.get('answer')
            if not answer:
                flash("Please select an answer.")
                current = session['current_question']
                questions = session['questions']
                return render_template('quiz.html', step='question', question=questions[current], question_num=current+1, total_questions=len(questions))
            current = session['current_question']
            questions = session['questions']
            session['user_answers'].append({
                'question': questions[current]['question'],
                'user_answer': answer,
                'correct_answer': questions[current]['correct_answer'],
                'is_correct': answer == questions[current]['correct_answer']
            })
            if answer == questions[current]['correct_answer']:
                session['score'] += 10
            session['current_question'] += 1
            if session['current_question'] < len(questions):
                return render_template('quiz.html', step='question', question=questions[session['current_question']], question_num=session['current_question']+1, total_questions=len(questions))
            else:
                conn = sqlite3.connect('db/quiz.db')
                c = conn.cursor()
                c.execute("INSERT INTO quiz_results (user_id, topic, score) VALUES (?, ?, ?)", (session['user_id'], ','.join(request.form.getlist('topic')), session['score']))
                c.execute("UPDATE users SET points = points + ? WHERE id = ?", (session['score'], session['user_id']))
                conn.commit()
                conn.close()
                return render_template('quiz.html', step='result', score=session['score'], user_answers=session['user_answers'])
        elif action == 'play_again':
            return render_template('quiz.html', step='select_topic')
    return render_template('quiz.html', step='login' if 'user_id' not in session else 'select_topic')

def generate_quiz_questions(topics):
    topic_mapping = {
        "Python": {"category": "science", "keywords": ["python", "programming", "code", "software"]},
        "JavaScript": {"category": "science", "keywords": ["javascript", "programming", "code", "web"]},
        "DevOps": {"category": "science", "keywords": ["devops", "docker", "kubernetes", "ci/cd"]},
        "Databases": {"category": "science", "keywords": ["database", "sql", "nosql", "mongodb"]},
        "Food": {"category": "food_and_drink", "keywords": ["food", "cuisine", "cooking", "recipe"]},
        "Science": {"category": "science", "keywords": ["science", "physics", "biology", "chemistry"]},
        "Technology": {"category": "science_and_technology", "keywords": ["technology", "computer", "software", "hardware"]},
        "History": {"category": "history", "keywords": ["history", "event", "era", "war"]},
        "Arts": {"category": "art_and_literature", "keywords": ["art", "literature", "painting", "book"]},
        "Sports": {"category": "sport_and_leisure", "keywords": ["sport", "athlete", "game", "team"]},
        "Movies": {"category": "film_and_tv", "keywords": ["movie", "film", "actor", "director"]},
        "Music": {"category": "music", "keywords": ["music", "song", "band", "artist"]},
        "Geography": {"category": "geography", "keywords": ["geography", "country", "city", "map"]},
        "Literature": {"category": "art_and_literature", "keywords": ["literature", "book", "author", "novel"]},
        "Mathematics": {"category": "science", "keywords": ["math", "algebra", "geometry", "calculus"]},
        "Health": {"category": "science", "keywords": ["health", "medicine", "nutrition", "exercise"]},
        "Nature": {"category": "science", "keywords": ["nature", "animals", "plants", "ecology"]},
        "Space": {"category": "science", "keywords": ["space", "astronomy", "planets", "stars"]},
        "Fashion": {"category": "arts_and_entertainment", "keywords": ["fashion", "clothing", "design", "style"]},
        "Business": {"category": "science", "keywords": ["business", "marketing", "finance", "economy"]}
    }
    
    # Mock questions as fallback
    mock_questions = {
        "Python": [
            {"question": "What is the output of print(2 ** 3)?", "options": ["6", "8", "9", "12"], "correct_answer": "8", "topic": "Python"},
            {"question": "Which keyword is used to define a function in Python?", "options": ["func", "def", "function", "lambda"], "correct_answer": "def", "topic": "Python"},
            {"question": "What does the len() function do?", "options": ["Returns the length of an object", "Converts to string", "Loops through a list", "Checks type"], "correct_answer": "Returns the length of an object", "topic": "Python"},
            {"question": "Which of these is a Python data structure?", "options": ["Array", "List", "Record", "Table"], "correct_answer": "List", "topic": "Python"},
            {"question": "What is used to handle exceptions in Python?", "options": ["try/except", "if/else", "for/while", "do/catch"], "correct_answer": "try/except", "topic": "Python"}
        ],
        "JavaScript": [
            {"question": "What is the use of 'let' in JavaScript?", "options": ["Declare a constant", "Declare a block-scoped variable", "Declare a global variable", "Define a function"], "correct_answer": "Declare a block-scoped variable", "topic": "JavaScript"},
            {"question": "Which method adds an element to the end of an array?", "options": ["pop()", "shift()", "push()", "unshift()"], "correct_answer": "push()", "topic": "JavaScript"},
            {"question": "What does 'NaN' stand for?", "options": ["Not a Number", "Null and None", "New Array Number", "Negative and Null"], "correct_answer": "Not a Number", "topic": "JavaScript"},
            {"question": "How do you define an arrow function?", "options": ["function() {}", "=> {}", "() => {}", "func() {}"], "correct_answer": "() => {}", "topic": "JavaScript"},
            {"question": "What is the DOM?", "options": ["Document Object Model", "Data Object Method", "Dynamic Output Model", "Document Order Map"], "correct_answer": "Document Object Model", "topic": "JavaScript"}
        ],
        "DevOps": [
            {"question": "What is CI/CD?", "options": ["Continuous Integration/Continuous Deployment", "Code Inspection/Code Delivery", "Continuous Improvement/Continuous Design", "Code Integration/Code Deployment"], "correct_answer": "Continuous Integration/Continuous Deployment", "topic": "DevOps"},
            {"question": "Which tool is used for containerization?", "options": ["Docker", "Jenkins", "Git", "Ansible"], "correct_answer": "Docker", "topic": "DevOps"},
            {"question": "What does IaC stand for?", "options": ["Infrastructure as Code", "Integration as Code", "Information as Code", "Interface as Code"], "correct_answer": "Infrastructure as Code", "topic": "DevOps"},
            {"question": "Which command starts a Docker container?", "options": ["docker run", "docker build", "docker push", "docker pull"], "correct_answer": "docker run", "topic": "DevOps"},
            {"question": "What is Kubernetes used for?", "options": ["Container orchestration", "Version control", "CI/CD pipeline", "Monitoring"], "correct_answer": "Container orchestration", "topic": "DevOps"}
        ],
        "Databases": [
            {"question": "What is a primary key?", "options": ["A unique identifier for a record", "A foreign key reference", "A table index", "A database backup"], "correct_answer": "A unique identifier for a record", "topic": "Databases"},
            {"question": "Which SQL command retrieves data?", "options": ["INSERT", "UPDATE", "SELECT", "DELETE"], "correct_answer": "SELECT", "topic": "Databases"},
            {"question": "What is MongoDB?", "options": ["A NoSQL database", "A relational database", "A graph database", "A key-value store"], "correct_answer": "A NoSQL database", "topic": "Databases"},
            {"question": "What does ACID stand for?", "options": ["Atomicity, Consistency, Isolation, Durability", "Access, Control, Integration, Data", "Analysis, Calculation, Isolation, Design", "Atomicity, Control, Indexing, Durability"], "correct_answer": "Atomicity, Consistency, Isolation, Durability", "topic": "Databases"},
            {"question": "Which command joins tables in SQL?", "options": ["MERGE", "JOIN", "UNION", "GROUP"], "correct_answer": "JOIN", "topic": "Databases"}
        ],
        "Food": [
            {"question": "What is the main ingredient in guacamole?", "options": ["Tomato", "Avocado", "Onion", "Pepper"], "correct_answer": "Avocado", "topic": "Food"},
            {"question": "Which country is known for sushi?", "options": ["China", "Japan", "Thailand", "Korea"], "correct_answer": "Japan", "topic": "Food"},
            {"question": "What type of pasta is shaped like small tubes?", "options": ["Spaghetti", "Penne", "Fusilli", "Tagliatelle"], "correct_answer": "Penne", "topic": "Food"},
            {"question": "What is the primary ingredient in hummus?", "options": ["Chickpeas", "Lentils", "Beans", "Peas"], "correct_answer": "Chickpeas", "topic": "Food"},
            {"question": "Which spice is known as the most expensive by weight?", "options": ["Cinnamon", "Saffron", "Paprika", "Turmeric"], "correct_answer": "Saffron", "topic": "Food"}
        ],
        "Science": [
            {"question": "What is the chemical symbol for water?", "options": ["H2O", "CO2", "O2", "N2"], "correct_answer": "H2O", "topic": "Science"},
            {"question": "Which planet is known as the Red Planet?", "options": ["Venus", "Mars", "Jupiter", "Mercury"], "correct_answer": "Mars", "topic": "Science"},
            {"question": "What is the primary source of energy for Earth?", "options": ["Moon", "Sun", "Wind", "Geothermal"], "correct_answer": "Sun", "topic": "Science"},
            {"question": "What gas do plants absorb during photosynthesis?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "correct_answer": "Carbon Dioxide", "topic": "Science"},
            {"question": "What is the unit of electric current?", "options": ["Volt", "Watt", "Ampere", "Ohm"], "correct_answer": "Ampere", "topic": "Science"}
        ],
        "Technology": [
            {"question": "What does CPU stand for?", "options": ["Central Processing Unit", "Computer Program Utility", "Control Power Unit", "Central Program Utility"], "correct_answer": "Central Processing Unit", "topic": "Technology"},
            {"question": "Which company developed the Windows operating system?", "options": ["Apple", "Microsoft", "Google", "IBM"], "correct_answer": "Microsoft", "topic": "Technology"},
            {"question": "What is the main function of a router?", "options": ["Store data", "Connect networks", "Run software", "Cool hardware"], "correct_answer": "Connect networks", "topic": "Technology"},
            {"question": "What does HTML stand for?", "options": ["Hyper Text Markup Language", "High Tech Machine Language", "Hyper Transfer Markup Language", "Home Tool Markup Language"], "correct_answer": "Hyper Text Markup Language", "topic": "Technology"},
            {"question": "Which protocol is used for secure web browsing?", "options": ["HTTP", "FTP", "HTTPS", "SMTP"], "correct_answer": "HTTPS", "topic": "Technology"}
        ],
        "History": [
            {"question": "Who was the first president of the United States?", "options": ["Abraham Lincoln", "George Washington", "Thomas Jefferson", "John Adams"], "correct_answer": "George Washington", "topic": "History"},
            {"question": "In which year did World War II end?", "options": ["1943", "1944", "1945", "1946"], "correct_answer": "1945", "topic": "History"},
            {"question": "Which ancient civilization built the pyramids?", "options": ["Romans", "Greeks", "Egyptians", "Mayans"], "correct_answer": "Egyptians", "topic": "History"},
            {"question": "What was the name of the ship that sank in 1912?", "options": ["Lusitania", "Titanic", "Britannic", "Olympic"], "correct_answer": "Titanic", "topic": "History"},
            {"question": "Which country was led by Nelson Mandela?", "options": ["South Africa", "Kenya", "Nigeria", "Ghana"], "correct_answer": "South Africa", "topic": "History"}
        ],
        "Arts": [
            {"question": "Who painted the Mona Lisa?", "options": ["Vincent van Gogh", "Leonardo da Vinci", "Pablo Picasso", "Claude Monet"], "correct_answer": "Leonardo da Vinci", "topic": "Arts"},
            {"question": "Which author wrote 'Pride and Prejudice'?", "options": ["Jane Austen", "Charlotte Brontë", "Emily Dickinson", "Virginia Woolf"], "correct_answer": "Jane Austen", "topic": "Arts"},
            {"question": "What is the name of Shakespeare's famous tragedy about a Danish prince?", "options": ["Macbeth", "Othello", "Hamlet", "King Lear"], "correct_answer": "Hamlet", "topic": "Arts"},
            {"question": "Which art movement is associated with Andy Warhol?", "options": ["Impressionism", "Cubism", "Pop Art", "Surrealism"], "correct_answer": "Pop Art", "topic": "Arts"},
            {"question": "Which instrument is known as the 'king of instruments'?", "options": ["Piano", "Violin", "Organ", "Trumpet"], "correct_answer": "Organ", "topic": "Arts"}
        ],
        "Sports": [
            {"question": "Which sport is known as 'the beautiful game'?", "options": ["Basketball", "Soccer", "Tennis", "Cricket"], "correct_answer": "Soccer", "topic": "Sports"},
            {"question": "How many players are on a basketball team on the court?", "options": ["5", "6", "7", "8"], "correct_answer": "5", "topic": "Sports"},
            {"question": "Which country has won the most Olympic gold medals?", "options": ["United States", "China", "Russia", "Germany"], "correct_answer": "United States", "topic": "Sports"},
            {"question": "What is the maximum score in a single frame of ten-pin bowling?", "options": ["100", "200", "300", "400"], "correct_answer": "300", "topic": "Sports"},
            {"question": "Which tennis tournament is played on clay courts?", "options": ["Wimbledon", "US Open", "Australian Open", "French Open"], "correct_answer": "French Open", "topic": "Sports"}
        ],
        "Movies": [
            {"question": "Who directed the movie 'Inception'?", "options": ["Steven Spielberg", "Christopher Nolan", "Quentin Tarantino", "Martin Scorsese"], "correct_answer": "Christopher Nolan", "topic": "Movies"},
            {"question": "Which movie won the Best Picture Oscar in 2020?", "options": ["1917", "Joker", "Parasite", "Ford v Ferrari"], "correct_answer": "Parasite", "topic": "Movies"},
            {"question": "What is the name of the fictional African country in 'Black Panther'?", "options": ["Wakanda", "Zamunda", "Genovia", "Sokovia"], "correct_answer": "Wakanda", "topic": "Movies"},
            {"question": "Which actor played Jack Sparrow in 'Pirates of the Caribbean'?", "options": ["Johnny Depp", "Orlando Bloom", "Brad Pitt", "Tom Cruise"], "correct_answer": "Johnny Depp", "topic": "Movies"},
            {"question": "Which movie is known for the line 'May the Force be with you'?", "options": ["Star Trek", "Star Wars", "The Matrix", "Avatar"], "correct_answer": "Star Wars", "topic": "Movies"}
        ],
        "Music": [
            {"question": "Which band performed the song 'Bohemian Rhapsody'?", "options": ["The Beatles", "Queen", "Led Zeppelin", "The Rolling Stones"], "correct_answer": "Queen", "topic": "Music"},
            {"question": "What instrument does a pianist play?", "options": ["Guitar", "Piano", "Drums", "Violin"], "correct_answer": "Piano", "topic": "Music"},
            {"question": "Which genre is associated with Bob Marley?", "options": ["Jazz", "Reggae", "Hip-Hop", "Classical"], "correct_answer": "Reggae", "topic": "Music"},
            {"question": "Who is known as the 'King of Pop'?", "options": ["Elvis Presley", "Michael Jackson", "Prince", "Justin Bieber"], "correct_answer": "Michael Jackson", "topic": "Music"},
            {"question": "Which song begins with 'Is this the real life? Is this just fantasy?'", "options": ["Stairway to Heaven", "Bohemian Rhapsody", "Hotel California", "Imagine"], "correct_answer": "Bohemian Rhapsody", "topic": "Music"}
        ],
        "Geography": [
            {"question": "What is the capital city of Brazil?", "options": ["Rio de Janeiro", "São Paulo", "Brasília", "Salvador"], "correct_answer": "Brasília", "topic": "Geography"},
            {"question": "Which continent is the largest by land area?", "options": ["Africa", "Asia", "Australia", "Europe"], "correct_answer": "Asia", "topic": "Geography"},
            {"question": "What is the longest river in the world?", "options": ["Amazon", "Nile", "Yangtze", "Mississippi"], "correct_answer": "Nile", "topic": "Geography"},
            {"question": "Which country has the most deserts?", "options": ["Australia", "Antarctica", "Saudi Arabia", "Chile"], "correct_answer": "Antarctica", "topic": "Geography"},
            {"question": "What is the highest mountain peak in the world?", "options": ["K2", "Kangchenjunga", "Everest", "Lhotse"], "correct_answer": "Everest", "topic": "Geography"}
        ],
        "Literature": [
            {"question": "Who wrote the novel '1984'?", "options": ["George Orwell", "Aldous Huxley", "Ray Bradbury", "J.K. Rowling"], "correct_answer": "George Orwell", "topic": "Literature"},
            {"question": "What is the name of the hobbit in 'The Lord of the Rings'?", "options": ["Bilbo Baggins", "Frodo Baggins", "Samwise Gamgee", "Peregrin Took"], "correct_answer": "Frodo Baggins", "topic": "Literature"},
            {"question": "Which play by Shakespeare features the character Lady Macbeth?", "options": ["Hamlet", "Macbeth", "Othello", "Romeo and Juliet"], "correct_answer": "Macbeth", "topic": "Literature"},
            {"question": "What is the first book in the 'Harry Potter' series?", "options": ["Chamber of Secrets", "Philosopher’s Stone", "Prisoner of Azkaban", "Goblet of Fire"], "correct_answer": "Philosopher’s Stone", "topic": "Literature"},
            {"question": "Who wrote 'To Kill a Mockingbird'?", "options": ["Harper Lee", "John Steinbeck", "F. Scott Fitzgerald", "Ernest Hemingway"], "correct_answer": "Harper Lee", "topic": "Literature"}
        ],
        "Mathematics": [
            {"question": "What is 5 + 7?", "options": ["10", "11", "12", "13"], "correct_answer": "12", "topic": "Mathematics"},
            {"question": "What is the value of π (pi) approximately?", "options": ["2.14", "3.14", "4.14", "5.14"], "correct_answer": "3.14", "topic": "Mathematics"},
            {"question": "What is the area of a circle with radius 2?", "options": ["4π", "6π", "8π", "12π"], "correct_answer": "4π", "topic": "Mathematics"},
            {"question": "What is the square root of 16?", "options": ["2", "3", "4", "5"], "correct_answer": "4", "topic": "Mathematics"},
            {"question": "What is 10% of 50?", "options": ["2", "5", "10", "15"], "correct_answer": "5", "topic": "Mathematics"}
        ],
        "Health": [
            {"question": "What vitamin is primarily obtained from sunlight?", "options": ["Vitamin A", "Vitamin C", "Vitamin D", "Vitamin E"], "correct_answer": "Vitamin D", "topic": "Health"},
            {"question": "How many chambers are in the human heart?", "options": ["2", "3", "4", "5"], "correct_answer": "4", "topic": "Health"},
            {"question": "What is the recommended daily water intake for adults?", "options": ["1L", "2L", "3L", "4L"], "correct_answer": "2L", "topic": "Health"},
            {"question": "Which organ filters blood in the body?", "options": ["Liver", "Kidneys", "Lungs", "Heart"], "correct_answer": "Kidneys", "topic": "Health"},
            {"question": "What is the primary source of energy for the body?", "options": ["Protein", "Carbohydrates", "Fats", "Vitamins"], "correct_answer": "Carbohydrates", "topic": "Health"}
        ],
        "Nature": [
            {"question": "What is the largest land animal?", "options": ["Elephant", "Giraffe", "Hippopotamus", "Rhinoceros"], "correct_answer": "Elephant", "topic": "Nature"},
            {"question": "Which gas makes up most of Earth's atmosphere?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Argon"], "correct_answer": "Nitrogen", "topic": "Nature"},
            {"question": "What is the tallest type of tree?", "options": ["Oak", "Pine", "Redwood", "Maple"], "correct_answer": "Redwood", "topic": "Nature"},
            {"question": "Which ocean is the largest?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "correct_answer": "Pacific", "topic": "Nature"},
            {"question": "What is the primary source of energy for Earth's climate?", "options": ["Geothermal", "Solar", "Wind", "Tidal"], "correct_answer": "Solar", "topic": "Nature"}
        ],
        "Space": [
            {"question": "Which planet is known as the Red Planet?", "options": ["Venus", "Mars", "Jupiter", "Saturn"], "correct_answer": "Mars", "topic": "Space"},
            {"question": "What is the largest planet in our solar system?", "options": ["Earth", "Jupiter", "Saturn", "Uranus"], "correct_answer": "Jupiter", "topic": "Space"},
            {"question": "What is the name of the first human to walk on the moon?", "options": ["Buzz Aldrin", "Neil Armstrong", "Yuri Gagarin", "Alan Shepard"], "correct_answer": "Neil Armstrong", "topic": "Space"},
            {"question": "Which constellation includes the North Star?", "options": ["Orion", "Ursa Major", "Cassiopeia", "Ursa Minor"], "correct_answer": "Ursa Minor", "topic": "Space"},
            {"question": "What gas makes up most of the Sun?", "options": ["Oxygen", "Hydrogen", "Helium", "Nitrogen"], "correct_answer": "Hydrogen", "topic": "Space"}
        ],
        "Fashion": [
            {"question": "Which designer is known for the 'little black dress'?", "options": ["Coco Chanel", "Yves Saint Laurent", "Christian Dior", "Giorgio Armani"], "correct_answer": "Coco Chanel", "topic": "Fashion"},
            {"question": "What material is commonly used for denim jeans?", "options": ["Cotton", "Wool", "Silk", "Polyester"], "correct_answer": "Cotton", "topic": "Fashion"},
            {"question": "Which color is associated with the Pantone Color of the Year 2022?", "options": ["Green", "Blue", "Purple", "Very Peri"], "correct_answer": "Very Peri", "topic": "Fashion"},
            {"question": "What accessory is known as a 'four-in-hand'?", "options": ["Hat", "Tie", "Scarf", "Belt"], "correct_answer": "Tie", "topic": "Fashion"},
            {"question": "Which fashion house is known for its monogram pattern?", "options": ["Gucci", "Louis Vuitton", "Prada", "Hermès"], "correct_answer": "Louis Vuitton", "topic": "Fashion"}
        ],
        "Business": [
            {"question": "What does CEO stand for?", "options": ["Chief Executive Officer", "Chief Economic Officer", "Chief Engineering Officer", "Chief Efficiency Officer"], "correct_answer": "Chief Executive Officer", "topic": "Business"},
            {"question": "Which company is known for the iPhone?", "options": ["Samsung", "Apple", "Google", "Microsoft"], "correct_answer": "Apple", "topic": "Business"},
            {"question": "What is the primary function of marketing?", "options": ["Product Design", "Customer Engagement", "Financial Planning", "Supply Chain"], "correct_answer": "Customer Engagement", "topic": "Business"},
            {"question": "What is the stock market index for the U.S.?", "options": ["FTSE", "Nikkei", "S&P 500", "DAX"], "correct_answer": "S&P 500", "topic": "Business"},
            {"question": "Which term refers to a company's total revenue?", "options": ["Profit", "Revenue", "Equity", "Liability"], "correct_answer": "Revenue", "topic": "Business"}
        ]
    }

    # Fetch questions from The Trivia API
    try:
        # Handle multiple topics by combining categories and keywords
        all_questions = []
        seen_questions = session.get('seen_questions', [])
        for topic in topics:
            category = topic_mapping.get(topic, {"category": "science"})["category"]
            keywords = topic_mapping.get(topic, {"keywords": ["programming"]})["keywords"]
            difficulties = ["easy", "medium", "hard"]
            difficulty = random.choice(difficulties)
            url = f"https://the-trivia-api.com/v2/questions?limit=15&categories={category}&difficulties={difficulty}"
            logger.debug(f"Fetching questions for topic: {topic}, category: {category}, difficulty: {difficulty}, URL: {url}")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            api_questions = response.json()

            # Filter out seen questions and match keywords (loosened condition)
            filtered_questions = [
                q for q in api_questions
                if q["id"] not in seen_questions and
                any(keyword.lower() in q["question"]["text"].lower() or keyword.lower() in q["correctAnswer"].lower() or True for keyword in keywords)
            ]
            logger.debug(f"Found {len(filtered_questions)} questions for {topic} after filtering")

            # Process each question
            for q in filtered_questions[:5]:  # Limit to 5 per topic
                options = q["incorrectAnswers"] + [q["correctAnswer"]]
                random.shuffle(options)
                all_questions.append({
                    "question": q["question"]["text"],
                    "options": options,
                    "correct_answer": q["correctAnswer"],
                    "topic": topic
                })
                seen_questions.append(q["id"])

        logger.debug(f"Total API questions collected: {len(all_questions)}")
        # Update seen questions in session
        session['seen_questions'] = seen_questions[-1000:]  # Limit storage to avoid session bloat

        # Only supplement with mock questions if no API questions are found
        if not all_questions:
            logger.warning("No API questions found. Using mock questions for all topics.")
            for topic in topics:
                mock = mock_questions.get(topic, mock_questions["Python"])
                random.shuffle(mock)
                all_questions.extend(mock[:5])
        elif len(all_questions) < 5:
            logger.info(f"Only {len(all_questions)} API questions found. Supplementing with mock questions.")
            remaining = 5 - len(all_questions)
            for topic in topics:
                mock = mock_questions.get(topic, mock_questions["Python"])
                random.shuffle(mock)
                all_questions.extend(mock[:remaining // len(topics) + 1])
                if len(all_questions) >= 5:
                    break

        random.shuffle(all_questions)
        return all_questions[:5]

    except (requests.RequestException, ValueError) as e:
        logger.error(f"API error: {e}. Using mock questions for {topics}.")
        all_questions = []
        for topic in topics:
            mock = mock_questions.get(topic, mock_questions["Python"])
            random.shuffle(mock)
            all_questions.extend(mock[:5])
        return all_questions[:5]

@app.route('/leaderboard')
def leaderboard():
    conn = sqlite3.connect('db/quiz.db')
    c = conn.cursor()
    c.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
    leaders = c.fetchall()
    conn.close()
    return render_template('leaderboard.html', leaders=leaders)

@app.route('/redeem', methods=['GET', 'POST'])
def redeem():
    if 'user_id' not in session:
        flash("Please log in to redeem points.")
        return redirect(url_for('quiz'))
    conn = sqlite3.connect('db/quiz.db')
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE id = ?", (session['user_id'],))
    points = c.fetchone()[0]
    if request.method == 'POST':
        if points >= 100:
            c.execute("UPDATE users SET points = points - 100 WHERE id = ?", (session['user_id'],))
            conn.commit()
            flash("Successfully redeemed Rs 100 Amazon voucher! Check your email (mock).")
        else:
            flash("Insufficient points. Need at least 100 points.")
    c.execute("SELECT points FROM users WHERE id = ?", (session['user_id'],))
    points = c.fetchone()[0]
    conn.close()
    return render_template('redeem.html', points=points)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        flash("Please log in to delete your account.")
        return redirect(url_for('quiz'))
    conn = sqlite3.connect('db/quiz.db')
    c = conn.cursor()
    c.execute("DELETE FROM quiz_results WHERE user_id = ?", (session['user_id'],))
    c.execute("DELETE FROM users WHERE id = ?", (session['user_id'],))
    conn.commit()
    conn.close()
    session.clear()
    flash("Account deleted successfully.")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
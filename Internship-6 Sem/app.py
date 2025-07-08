from flask import Flask, render_template, request, redirect, url_for, session
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
from datetime import datetime
import pandas as pd
import openai
import os
from flask import jsonify
# Flask Setup
app = Flask(__name__)
app.secret_key = 'e408b55fc137d0da4215909cc2ff7d6a935e726e6c4fc453'
CORS(app)

# MongoDB Setup
client = MongoClient("mongodb+srv://bhattpalak080:palak1925@cluster0.suco1sn.mongodb.net/")
db = client['expense_tracker']
users_collection = db['users']
expenses_collection = db['expenses']

@app.route('/')
def index():
    return render_template('login.html')

# Login Route
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = users_collection.find_one({'email': email})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['user'] = email
        return redirect(url_for('desktop'))
    else:
        return render_template('login.html', error="Invalid email or password")

@app.route('/desktop')
def desktop():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_email = session['user']
    expenses = list(expenses_collection.find({'user': user_email}))

    # Convert ObjectId and datetime for Jinja compatibility
    for expense in expenses:
        expense['id'] = str(expense['_id'])  # for URLs
        expense['date'] = expense['date'].strftime('%Y-%m-%d')

    return render_template('desktop.html', user=user_email, expenses=expenses)


# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        print("Received:", username, email)

        if not username or not email or not password:
            print("Missing fields!")
            return render_template('signup.html', error="Please fill all fields.")

        # Proceed with saving to DB
        return redirect('/desktop')

    return render_template('signup.html')



# Logout Route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# Add Expense
# @app.route('/analysis', methods=['POST'])
# def analysis():
#     if 'user' not in session:
#         return redirect(url_for('index'))

#     title = request.form['title']
#     try:
#         amount = float(request.form['amount'])
#     except ValueError:
#         return "Invalid amount", 400

#     date_str = request.form['date']
#     category = request.form['category']

#     try:
#         date = datetime.strptime(date_str, '%Y-%m-%d')
#     except ValueError:
#         return "Invalid date format", 400

#     expense = {
#         'title': title,
#         'amount': amount,
#         'date': date,
#         'category': category,
#         'user': session['user']
#     }

#     expenses_collection.insert_one(expense)
#     return redirect(url_for('desktop'))
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user' not in session:
        return redirect('/login')

    title = request.form.get('title')
    amount = request.form.get('amount')
    date = request.form.get('date')
    category = request.form.get('category')

    if not title or not amount or not date or not category:
        return "Missing fields", 400

    expense = {
        'user': session['user'],
        'title': title,
        'amount': float(amount),
        'date': datetime.strptime(date, '%Y-%m-%d'),
        'category': category
    }

    expenses_collection.insert_one(expense)
    return redirect('/desktop')


@app.route('/analysis')
def analysis():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    expenses = list(expenses_collection.find({'user': user}))

    # Safety check
    if not expenses:
        return render_template("analysis.html",
                               labels=[],
                               amounts=[],
                               categories=[],
                               category_totals=[])

    labels = [str(exp['date']) if 'date' in exp else 'Unknown' for exp in expenses]
    amounts = [float(exp['amount']) for exp in expenses if 'amount' in exp]

    category_summary = {}
    for exp in expenses:
        cat = exp.get('category', 'Other')
        category_summary[cat] = category_summary.get(cat, 0) + float(exp.get('amount', 0))

    categories = list(category_summary.keys())
    category_totals = list(category_summary.values())

    return render_template("analysis.html",
                           labels=labels,
                           amounts=amounts,
                           categories=categories,
                           category_totals=category_totals)

# Delete Expense
@app.route('/delete_expense/<expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user' not in session:
        return redirect(url_for('index'))

    expenses_collection.delete_one({'_id': ObjectId(expense_id)})
    return redirect(url_for('desktop'))

# Edit Expense
@app.route("/edit_expense/<expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if "user" not in session:
        return redirect(url_for("index"))

    expense = expenses_collection.find_one({"_id": ObjectId(expense_id)})

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            date = datetime.strptime(request.form["date"], '%Y-%m-%d')
        except ValueError:
            return "Invalid input", 400

        updated_data = {
            "title": request.form["title"],
            "amount": amount,
            "date": date,
            "category": request.form["category"]
        }
        expenses_collection.update_one(
            {"_id": ObjectId(expense_id)},
            {"$set": updated_data}
        )
        return redirect(url_for("desktop"))

    return render_template("edit_expense.html", expense=expense)

@app.route('/estimate')
def estimate():
    user_email = session.get('user')
    if not user_email:
        return redirect(url_for('login'))

    # Get user expenses
    user_expenses = expenses_collection.find({'email': user_email})

    # Optional: Do a basic projection logic (e.g., yearly avg * 12 months)
    total = 0
    count = 0
    for exp in user_expenses:
        total += float(exp['amount'])
        count += 1

    avg_monthly = (total / count) if count else 0
    future_year_estimate = round(avg_monthly * 12, 2)

    return render_template('estimate.html', estimate=future_year_estimate)




    

@app.route('/filter_graphs')
def filter_graphs():
    period = request.args.get('period')
    
    # Example dummy data logic based on period (you should fetch and aggregate from DB)
    if period == 'yearly':
        pie_data = {...}
        bar_data = {...}
        line_data = {...}
    elif period == 'monthly':
        ...
    elif period == 'weekly':
        ...
    elif period == 'daily':
        ...
    
    return jsonify({
        'pieData': pie_data,
        'barData': bar_data,
        'lineData': line_data
    })


@app.route('/chat', methods=['POST'])
def ask_gpt3_5(question):
    try:
        # Making a request to OpenAI API
        response = openai.Completion.create(
            engine="text-davinci-003",  # GPT-3.5 model engine
            prompt=question,
            max_tokens=150,  # Controls response length
            temperature=0.7,  # Controls randomness in responses
        )
        # Extracting and returning the answer
        return response.choices[0].text.strip()
    except openai.error.RateLimitError:
        return "Quota exceeded! Please check your usage."
    except Exception as e:
        return str(e)

# Sample chatbot interaction
def chat():
    print("Chatbot is ready to answer any questions!")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        answer = ask_gpt3_5(user_input)
        print(f"ChatGPT: {answer}")

    
@app.route('/contact.html')
def contact():
    return render_template('contact.html')

# Run the Flask App
if __name__ == '__main__':
    app.run(port=5000, debug=True)

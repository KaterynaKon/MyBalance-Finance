from flask import Flask, render_template, redirect, url_for, request, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app=Flask(__name__)
app.secret_key='a74c82b6c13d4218ac43e32e8d1d9f67'
DATABASE='MyBalance.db'

#DataBase Setup

def get_db_conn():
     conn=sqlite3.connect(DATABASE)
     conn.row_factory=sqlite3.Row
     return conn
def init_db():
    conn=get_db_conn()
    c=conn.cursor()
    c.execute(''' CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              email TEXT,
              password TEXT NOT NULL)

              ''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              date TEXT,
              type TEXT,
              category TEXT,
              amount REAL,
              description TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
              )
              ''')
    conn.commit()
    conn.close()

init_db()

    #--Routes--
@app.route('/')
def home():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('home.html')
    
@app.route('/register', methods=['GET','POST'])
def register():
        if request.method=='POST':
            username=request.form['username']
            email=request.form['email']
            password=generate_password_hash(request.form['password'])

            conn=get_db_conn()
            c=conn.cursor()
            c.execute('INSERT INTO users (username, email, password) VALUES(?,?,?)',(username, email, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        return render_template('register.html')
    
@app.route('/login', methods=['GET', 'POST'])
def login():
        if request.method=='POST':
            username=request.form['username']
            password=request.form['password']

            conn=get_db_conn()
            c=conn.cursor()
            c.execute('SELECT id, password FROM users WHERE username=?',(username,))
            user=c.fetchone()
            conn.close()
                      
            if user and check_password_hash(user[1],password):
                session['user_id'] = user[0]
                return redirect(url_for('dashboard'))
            else:
                return "Login failed"
        return render_template('login.html')
   
@app.route('/dashboard')
def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn=get_db_conn()
        c=conn.cursor()
        c.execute('SELECT id, date, type, category, amount, description FROM transactions WHERE user_id=? ORDER BY date DESC',(session['user_id'],) )
        transactions=c.fetchall()
        conn.close()
        return render_template('dashboard.html', transactions=transactions)

@app.route('/add', methods=['GET','POST'])
def add():
     if 'user_id' not in session:
          return redirect(url_for('login'))
     
     if request.method=='POST':
          date=request.form['date']
          ttype=request.form['type']
          category=request.form['category']
          amount=request.form['amount']
          description=request.form['description']
          if not description.strip():
               error='Description cannot be empty'
               return render_template('add.html', error=error, date=date,type=ttype, category=category, amount=amount, description=description)

          conn=get_db_conn()
          c=conn.cursor()
          c.execute('''INSERT INTO transactions (user_id, date, type, category, amount, description) VALUES (?,?,?,?,?,?)''',
                    (session ['user_id'], date, ttype, category, amount, description))
          conn.commit()
          conn.close()
          return redirect(url_for('dashboard'))
     return render_template('add.html')



@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if 'user_id' not in session:
          return redirect(url_for('login'))

    conn=get_db_conn()
    c=conn.cursor()
    c.execute('DELETE FROM transactions WHERE id=? AND user_id=?', (id,session['user_id']))              
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))
   
@app.route('/confirm_delete/<int:id>')
def confirm_delete(id):
     return render_template('confirm_delete.html', id=id)


@app.route('/amend/<int:id>', methods=['GET'])
def amend(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
     
    conn=get_db_conn()
    
    line=conn.execute('SELECT * FROM transactions WHERE id=? AND user_id=?', (id, session['user_id'])).fetchone()
    if line is None:
         return "Access denied", 403
    conn.close()
    return render_template('edit.html', line=line)

@app.route('/amend/<int:id>', methods=['POST'])
def update(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    new_date=request.form['date']
    new_ttype=request.form['type']
    new_category=request.form['category']
    new_amount=request.form['amount']
    new_description=request.form['description']

    conn=get_db_conn()
    conn.execute('UPDATE transactions SET user_id=?, date=?, type=?, category=?, amount=?, description=? WHERE id=?', (session['user_id'],new_date,new_ttype,new_category,new_amount,new_description, id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))
     
     



@app.route('/logout')
def logout():
     session.pop('user_id', None)
     return redirect(url_for('home'))

if __name__=='__main__':
     app.run(debug=True)
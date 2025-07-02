from flask import Flask, render_template, redirect, url_for, request, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app=Flask(__name__)
app.secret_key='a74c82b6c13d4218ac43e32e8d1d9f67'
DATABASE='MyBalance.db'
UPLOAD_FOLDER='static/uploads'
ALLOWED_EXTENSIONS={'png','jpg','jpeg','pdf','gif'}
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']=2*1024*1024

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
              attachment TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id)
              )
              ''')
    conn.commit()
    conn.close()

def allowed_file(filename):
     return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
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
        
        sort_by=request.args.get('sort_by','date')
        order=request.args.get('order','desc')

        if sort_by not in ['date','type','amount', 'category']:
             sort_by='date'
        if order not in ['asc', 'desc']:
             order='desc'

        date_from=request.args.get('from')
        date_to=request.args.get('to')

        query='''
            SELECT id, date, type, category, amount, description, attachment 
            FROM transactions
            WHERE user_id=?
        '''
        params=[session['user_id']]

        if date_from:
             query+=" AND date>=?"
             params.append(date_from)
        if date_to:
             query+=" AND date<=?"
             params.append(date_to)
        query+= f"ORDER BY {sort_by} {order}"
             

        conn=get_db_conn()
        c=conn.cursor()
       
        c.execute(query, tuple(params))
        transactions=c.fetchall()

        c.execute('''
                    SELECT COALESCE(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0)-
                    COALESCE(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0)
                    FROM transactions
                    WHERE user_id=?
                  
                  ''',(session['user_id'],))
        balance=c.fetchone()[0] or 0
        conn.close()
        return render_template('dashboard.html', transactions=transactions, sort_by=sort_by, order=order, date_from=date_from, 
                               date_to=date_to, balance=balance)


@app.route('/add', methods=['GET','POST'])
def add():
    if 'user_id' not in session:
          return redirect(url_for('login'))

    ttype=request.values.get('type','Income') 
    income_categories=['Salary','Freelance','Business','Rental income','Dividends',
                 'Interest','Gifts','Pension','Scholarship','Government benefits',
                   'Investment income', 'Tax refund', 'Lottery or prize','Other']
    expense_categories=['Food','Transport','Utilities','Rent','Healthcare','Education',
                        'Entertainment','Clothing','Travel','Insurance', 'Debt payments', 'Other']
   
    categories=income_categories if ttype=='Income' else expense_categories
    if request.method=='POST':
          date=request.form['date']
          category=request.form['category']
          amount=request.form['amount']
          description=request.form['description']
          attachment_file=request.files.get('attachment')
          filename=None
          if attachment_file and allowed_file(attachment_file.filename):
               filename=secure_filename(attachment_file.filename)
               attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
          if not description.strip():
               error='Description cannot be empty'
               return render_template('add.html', error=error, date=date,type=ttype, category=category, amount=amount, description=description, categories=categories)

          conn=get_db_conn()
          c=conn.cursor()
          c.execute('''INSERT INTO transactions (user_id, date, type, category, amount, description, attachment) VALUES (?,?,?,?,?,?,?)''',
                    (session ['user_id'], date, ttype, category, amount, description, filename))
          conn.commit()
          conn.close()
          return redirect(url_for('dashboard'))
    return render_template('add.html', type=ttype, categories=categories)



@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if 'user_id' not in session:
          return redirect(url_for('login'))

    conn=get_db_conn()
    c=conn.cursor()
    transaction=c.execute('SELECT attachment FROM transactions WHERE id=? AND user_id=?', (id,session['user_id'])).fetchone()
    if transaction and transaction['attachment']:
         file_path=os.path.join(app.config['UPLOAD_FOLDER'], transaction['attachment']) 
         if os.path.exists(file_path):
              os.remove(file_path)  
    c.execute('DELETE FROM transactions WHERE id=? AND user_id=?', (id,session['user_id']))        
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))
   
@app.route('/confirm_delete/<int:id>')
def confirm_delete(id):
    target=request.args.get('target','record')
    if target=='attachment':
          form_action=url_for('delete_attachment',id=id)
    else:
         form_action=url_for('delete',id=id)
    return render_template('confirm_delete.html', id=id, target=target,form_action=form_action)

@app.route('/delete_attachment/<int:id>', methods=['POST'])
def delete_attachment(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_conn()
    c = conn.cursor()
    transaction = c.execute('SELECT attachment FROM transactions WHERE id=? AND user_id=?', (id, session['user_id'])).fetchone()
    if transaction and transaction['attachment']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], transaction['attachment'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    c.execute('UPDATE transactions SET attachment=NULL WHERE id=? AND user_id=?', (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('update', id=id))



@app.route('/amend/<int:id>', methods=['GET','POST'])
def update(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn=get_db_conn()
    c=conn.cursor()

    transaction=c.execute('SELECT * FROM transactions WHERE id=? AND user_id=?',(id, session['user_id'])).fetchone()
    if request.method=='POST':
        new_date=request.form['date']
        new_ttype=request.form['type']
        new_category=request.form['category']
        new_amount=request.form['amount']
        new_description=request.form['description']
        new_attachment_file=request.files.get('attachment')
        filename=transaction['attachment']
        if new_attachment_file and allowed_file(new_attachment_file.filename):
            filename=secure_filename(new_attachment_file.filename)
            new_attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        if not new_description.strip():
            error='Description cannot be empty'
            income_categories=[...]  
            expense_categories=[...] 
            categories=income_categories if new_ttype=='Income' else expense_categories     
            return render_template('edit.html', error=error, date=new_date,type=new_ttype, category=new_category, amount=new_amount, description=new_description, categories=categories)

      
        c.execute('''
                  UPDATE transactions SET 
                  date=?, type=?, category=?, amount=?, 
                  description=?, attachment=? WHERE id=? AND user_id=?''',(new_date,new_ttype,new_category,new_amount,new_description,filename,id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    conn.close()
    return render_template('edit.html', transaction=transaction)    
     



@app.route('/logout')
def logout():
     session.pop('user_id', None)
     return redirect(url_for('home'))

if __name__=='__main__':
     app.run(debug=True)
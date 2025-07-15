from flask import Flask, render_template, redirect, url_for, request, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from datetime import date, timedelta
import io
import csv
import pandas as pd

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

        preset=request.args.get('preset')
        today=date.today()
        if preset=='this_week':
             
             start_of_week=today-timedelta(days=today.weekday())
             date_from=start_of_week.isoformat()
             date_to=today.isoformat()
        
        elif preset=='last_7_days':
             date_from=(today-timedelta(days=6)).isoformat()
             date_to=today.isoformat()
        
        elif preset=='this_month':
             date_from=(today.replace(day=1)).isoformat()
             date_to=today.isoformat()
        
        elif preset=='last_30_days':
             date_from=(today-timedelta(days=29)).isoformat()
             date_to=today.isoformat()

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
        
        query_current = '''SELECT 
                        COALESCE(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0) -
                        COALESCE(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0) AS balance
                        FROM transactions
                        WHERE user_id=?'''
        c.execute(query_current, (session['user_id'],))
        current_balance = c.fetchone()['balance']
        query_totals='''
                    SELECT 
                    COALESCE(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0)-
                    COALESCE(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0) AS balance,
                    COALESCE(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0) AS total_income,
                    COALESCE(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0) AS total_expenses
                    FROM transactions
                    WHERE user_id=?
                  
                  '''
        params_totals=[session['user_id']]
        if date_from:
            query_totals+= ' AND date>=?'
            params_totals.append(date_from)
        if date_to:
            query_totals+= ' AND date<=?'
            params_totals.append(date_to)
        c.execute(query_totals, tuple(params_totals))
        row=c.fetchone()
        total_income=row['total_income']
        total_expenses=row['total_expenses']
        balance=row['balance']
        conn.close()
        return render_template('dashboard.html', transactions=transactions, sort_by=sort_by, order=order, date_from=date_from, 
                               date_to=date_to, balance=balance, total_income=total_income,total_expenses=total_expenses, current_balance=current_balance)


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

@app.route('/import', methods=['GET','POST'])
def import_transactions():
     if 'user_id' not in session:
          return redirect (url_for('login'))
     if request.method=='POST':
          file=request.files['file']
          if file.filename.endswith('.csv'):
               stream=io.StringIO(file.stream.read().decode("UTF8"),newline=None)
               csv_input=csv.reader(stream)
               next(csv_input)
               conn=get_db_conn()
               c=conn.cursor()
               for row in csv_input:
                    if not row:
                        continue 
                    date, ttype, category, amount, description=row
                    c.execute('''INSERT INTO transactions (user_id, date, type, category, amount, description) VALUES (?,?,?,?,?,?)''',
                    (session ['user_id'], date, ttype, category, amount, description))
               conn.commit()
               conn.close()
               return redirect(url_for('dashboard'))
     return render_template('upload_tr.html')

@app.route('/export/<filetype>')
def export_transactions(filetype):
     if 'user_id' not in session:
          return redirect(url_for('login'))
     start_date=request.args.get('start_date') or None
     end_date=request.args.get('end_date') or None

     conn=get_db_conn()
     sql='SELECT * FROM transactions WHERE user_id=?'
     params=[session['user_id']]
     if start_date:
        sql+=' AND date>=?'
        params.append(start_date)
     if end_date:
        sql+=' AND date<=?'
        params.append(end_date)
     print(sql, params)
     df=pd.read_sql_query(sql, conn, params=params)
     conn.close()
     
     if start_date and end_date:
          download_name=f"transactions_{start_date}_to_{end_date}"
     elif start_date:
          download_name=f"transactions_from_{start_date}"
     elif end_date:
          download_name=f"transactions_to_{end_date}"
     else:
          download_name=f"transactions_all"
     if filetype=='csv':
          output=io.StringIO()
          df.to_csv(output,index=False)
          output.seek(0)
          return send_file(
               io.BytesIO(output.getvalue().encode('utf-8')),
               mimetype='text/csv',
               as_attachment=True,
               download_name=download_name+'.csv'
          )
     elif filetype=='excel':
        output=io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
          df.to_excel(writer, index=False, sheet_name='Transactions')
        output.seek(0)
        return send_file(
               output,
               mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
               as_attachment=True,
               download_name=download_name+'.xlsx'
          )
     else:
        return 'Invalid file type',400 

               
     

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
     
@app.route('/reports')
def reports():
     if 'user_id' not in session:
        return redirect(url_for('login'))
     return render_template('reports.html')  

@app.route('/reports/categories') 
def report_categories():
     if 'user_id' not in session:
        return redirect(url_for('login'))
     date_from=request.args.get('from')
     date_to=request.args.get('to')

     preset=request.args.get('preset')
     today=date.today()
     if preset=='this_week':
             
             start_of_week=today-timedelta(days=today.weekday())
             date_from=start_of_week.isoformat()
             date_to=today.isoformat()
        
     elif preset=='last_7_days':
             date_from=(today-timedelta(days=6)).isoformat()
             date_to=today.isoformat()
        
     elif preset=='this_month':
             date_from=(today.replace(day=1)).isoformat()
             date_to=today.isoformat()
        
     elif preset=='last_30_days':
             date_from=(today-timedelta(days=29)).isoformat()
             date_to=today.isoformat()
     query='''
                SELECT date, category, type, SUM(amount) AS total_amount
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
    
     query+=" GROUP BY category, type ORDER BY date, type, total_amount DESC"
     conn=get_db_conn()
     c=conn.cursor()
     c.execute(query, tuple(params))
     report_data=c.fetchall()
     conn.close()
     return render_template('report_categories.html', report_data=report_data, date_from=date_from, date_to=date_to)  

@app.route('/logout')
def logout():
     session.pop('user_id', None)
     return redirect(url_for('home'))

if __name__=='__main__':
     app.run(debug=True)
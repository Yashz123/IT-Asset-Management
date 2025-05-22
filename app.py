import io
from flask import Flask, flash, render_template, request, redirect, url_for, session, send_file
import pymysql
from pymysql.cursors import DictCursor
import pandas as pd
import xlsxwriter

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def get_db_connection():
    return pymysql.connect(
        host='yourhost',
        user='username',
        password='yourpassword',
        database='db_name',
        cursorclass=DictCursor
    )

@app.route('/')
def home():
    return redirect('/asset')

@app.route('/asset', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']  # 👈 Save role in session
            return redirect('/dashboard')
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/dashboard', methods=['GET'])
def dashboard():
    search = request.args.get('search', '').strip()
    fields = ['allocated_to', 'department', 'make', 'model', 'asset_type', 'site','category','floor','asset_status']

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if search:
        like_pattern = f"%{search}%"
        where_clauses = " OR ".join([f"{field} LIKE %s" for field in fields])
        query = f"SELECT * FROM assets WHERE {where_clauses}"
        params = [like_pattern] * len(fields)
        cursor.execute(query, params)
    else:
        query = "SELECT * FROM assets"
        cursor.execute(query)

    assets = cursor.fetchall()
    asset_count = len(assets)

    cursor.close()
    conn.close()

    return render_template('dashboard.html', assets=assets, asset_count=asset_count)


@app.route('/add', methods=['GET', 'POST'])
def add_asset():
    if request.method == 'POST':
        form = request.form
        data = {
            'allocated_to': form.get('allocated_to'),
            'make': form.get('make'),
            'model': form.get('model'),
            'model_no': form.get('model_no'),
            'service_tag': form.get('service_tag'),
            'department': form.get('department'),
            'office_asset_tag': form.get('office_asset_tag'),
            'host_name': form.get('host_name'),
            'ip_address': form.get('ip_address'),
            'asset_status': form.get('asset_status'),
            'asset_type': form.get('asset_type'),
            'asset_description': form.get('asset_description'),
            'warranty_status': form.get('warranty_status'),
            'warranty_date': form.get('warranty_date') or None,
            'functional_manager': form.get('functional_manager'),
            'designation': form.get('designation'),
            'site': form.get('site'),
            'floor': form.get('floor'),
            'workstation_no': form.get('workstation_no'),
            'category': form.get('category')
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ', '.join(['%s'] * len(data))
        columns = ', '.join(data.keys())
        query = f"INSERT INTO assets ({columns}) VALUES ({placeholders})"
        cursor.execute(query, list(data.values()))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('add_asset.html')



@app.route('/edit/<int:asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form

        update_query = """
            UPDATE assets SET 
                allocated_to=%s, make=%s, model=%s, model_no=%s, service_tag=%s,
                department=%s, office_asset_tag=%s, host_name=%s, ip_address=%s,
                asset_status=%s, asset_type=%s, asset_description=%s, warranty_status=%s,
                warranty_date=%s, functional_manager=%s, designation=%s, site=%s,
                floor=%s, workstation_no=%s, category=%s
            WHERE id=%s
        """

        values = (
            data['allocated_to'], data['make'], data['model'], data['model_no'], data['service_tag'],
            data['department'], data['office_asset_tag'], data['host_name'], data['ip_address'],
            data['asset_status'], data['asset_type'], data['asset_description'], data['warranty_status'],
            data['warranty_date'] or None, data['functional_manager'], data['designation'], data['site'],
            data['floor'], data['workstation_no'], data['category'], asset_id
        )

        cursor.execute(update_query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/dashboard')

    else:
        cursor.execute("SELECT * FROM assets WHERE id = %s", (asset_id,))
        asset = cursor.fetchone()
        cursor.close()
        conn.close()

        return render_template('edit_asset.html', asset=asset)


@app.route('/delete/<int:id>', methods=['POST'])
def delete_asset(id):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assets WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Asset deleted successfully.', 'success')
    return redirect('/dashboard')


@app.route('/export_excel')
def export_excel():
    search = request.args.get('search', '').strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    base_query = "SELECT * FROM assets"
    if search:
        fields = ['allocated_to', 'department', 'make', 'model', 'asset_type', 'site']
        where_clause = " OR ".join([f"LOWER({field}) LIKE %s" for field in fields])
        query = f"{base_query} WHERE {where_clause}"
        params = [f"%{search}%"] * len(fields)
        cursor.execute(query, params)
    else:
        cursor.execute(base_query)

    rows = cursor.fetchall()

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    if rows:
        headers = rows[0].keys()
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        for row_num, row in enumerate(rows, 1):
            for col_num, (key, value) in enumerate(row.items()):
                worksheet.write(row_num, col_num, str(value))

    workbook.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name='assets.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                           (username, password, role))
            conn.commit()
            flash('User created successfully!', 'success')
        except Exception as e:
            flash('Error creating user: ' + str(e), 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect('/dashboard')

    return render_template('create_user.html')

@app.route('/manage_users')
def manage_users():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username != %s", (session['username'],))
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('manage_users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect('/dashboard')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully', 'success')
    return redirect('/manage_users')


@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect('/dashboard')
    username = request.form['username']
    role = request.form['role']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET username = %s, role = %s WHERE id = %s", (username, role, user_id))
    conn.commit()
    conn.close()
    flash('User updated successfully', 'success')
    return redirect('/manage_users')

@app.route('/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect('/dashboard')
    new_password = request.form['new_password']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, user_id))
    conn.commit()
    conn.close()
    flash('Password reset successfully', 'success')
    return redirect('/manage_users')





@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)

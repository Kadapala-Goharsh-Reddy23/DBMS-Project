from flask import Flask, request, jsonify, render_template, redirect, session
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="KGReddy@23",   # ← change this
    database="blood_donor_db"
)

cursor = db.cursor(dictionary=True)


@app.route('/')
def home():
    return render_template('index.html')


app.secret_key = "secret123"

@app.route('/add_donor', methods=['POST'])
def add_donor():

    name = request.form['name']
    age = request.form['age']
    gender = request.form['gender']
    blood = request.form['blood_group']
    phone = request.form['phone']
    city = request.form['address']

    cursor.execute("""
    INSERT INTO Donors(Name, Age, Gender, Blood_Group, Phone, Address)
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, age, gender, blood, phone, city))

    db.commit()

    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form

        query = """
        INSERT INTO Donors 
        (Donor_ID, Name, Age, Gender, Blood_Group, Phone, Address, Last_Donation_Date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            data['id'], data['name'], data['age'], data['gender'],
            data['blood_group'], data['phone'], data['address'], data['last_donation']
        )

        cursor.execute(query, values)
        db.commit()

        return redirect('/admin')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form['id']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM Admins WHERE Username=%s AND Password=%s",
            (username, password)
        )

        admin = cursor.fetchone()

        if admin:
            session['admin'] = username
            return redirect('/admin')
        else:
            return "Invalid Credentials!"

    return render_template('login.html')

@app.route('/admin')
def admin():

    if not session.get('admin'):
        return redirect('/login')

    cursor.execute("SELECT * FROM Donors")
    donors = cursor.fetchall()

    cursor.execute("SELECT * FROM Requests")
    requests = cursor.fetchall()

    cursor.execute("""
    SELECT Blood_Group, SUM(Units_Available) AS Units
    FROM Blood_Inventory
    GROUP BY Blood_Group
    """)
    inventory = cursor.fetchall()

    cursor.execute("""
    SELECT b.Location AS City, i.Blood_Group, SUM(i.Units_Available) AS Units
    FROM Blood_Inventory i
    JOIN Blood_Banks b ON i.Bank_Id = b.Bank_Id
    GROUP BY b.Location, i.Blood_Group
    ORDER BY b.Location, i.Blood_Group
    """)
    city_data = cursor.fetchall()

    return render_template('admin.html',
                           donors=donors,
                           requests=requests,
                           inventory=inventory,
                           city_data=city_data)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

@app.route('/search')
def search():
    blood = request.args.get('blood_group')
    city = request.args.get('city')

    query = "SELECT Name, Blood_Group, Phone, Address FROM Donors WHERE 1=1"
    values = []

    if blood:
        query += " AND Blood_Group = %s"
        values.append(blood)

    if city:
        query += " AND Address LIKE %s"
        values.append(f"%{city}%")

    cursor.execute(query, tuple(values))
    return jsonify(cursor.fetchall())

@app.route('/delete/<int:id>')
def delete(id):
    cursor.execute("DELETE FROM Donors WHERE Donor_Id=%s", (id,))
    db.commit()
    return redirect('/admin')

@app.route('/delete_request/<int:id>')
def delete_request(id):
    cursor.execute("DELETE FROM Requests WHERE Request_ID=%s", (id,))
    db.commit()
    return redirect('/admin')

@app.route('/availability')
def availability():
    blood = request.args.get('blood_group')

    query = """
    SELECT Blood_Group, SUM(Units_Available) AS Total_Units
    FROM Blood_Inventory
    WHERE Blood_Group = %s
    GROUP BY Blood_Group
    """

    cursor.execute(query, (blood,))
    db.commit()
    return jsonify(cursor.fetchall())

@app.route('/request_blood', methods=['POST'])
def request_blood():

    name = request.form['name']
    blood = request.form['blood']
    city = request.form['city']
    units = request.form['units']

    cursor.execute("""
    INSERT INTO Requests(Name, Blood_Group, City, Units_Required, Status)
    VALUES (%s, %s, %s, %s, 'Pending')
    """, (name, blood, city, units))

    db.commit()

    return redirect('/')

@app.route('/approve/<int:id>')
def approve(id):

    cursor.execute("SELECT * FROM Requests WHERE Request_ID=%s", (id,))
    req = cursor.fetchone()

    if not req:
        return "Request not found"

    blood = req['Blood_Group']
    units_needed = int(req['Units_Required'])
    city = req['City'] 

    # Get all banks with this blood (highest first)
    cursor.execute("""
    SELECT i.Inventory_Id, i.Units_Available
    FROM Blood_Inventory i
    JOIN Blood_Banks b ON i.Bank_Id = b.Bank_Id
    WHERE i.Blood_Group=%s
    AND b.Location=%s
    AND i.Units_Available > 0
    ORDER BY i.Units_Available DESC
    """, (blood, city))

    rows = cursor.fetchall()

    if not rows:
        return "No blood available"

    for row in rows:
        if units_needed <= 0:
            break

        available = row['Units_Available']

        if available >= units_needed:
            new_units = available - units_needed
            units_needed = 0
        else:
            new_units = 0
            units_needed -= available

        cursor.execute("""
        UPDATE Blood_Inventory
        SET Units_Available=%s
        WHERE Inventory_Id=%s
        """, (new_units, row['Inventory_Id']))

    if units_needed > 0:
        return "Not enough blood available"

    # Update request status
    cursor.execute("""
    UPDATE Requests
    SET Status='Completed'
    WHERE Request_ID=%s
    """, (id,))

    db.commit()

    return redirect('/admin')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if request.method == 'POST':
        data = request.form

        query = """
        UPDATE Donors SET 
        Name=%s, Age=%s, Gender=%s, Blood_Group=%s,
        Phone=%s, Address=%s
        WHERE Donor_ID=%s
        """

        values = (
            data['name'], data['age'], data['gender'],
            data['blood_group'], data['phone'],
            data['address'], id
        )

        cursor.execute(query, values)
        db.commit()

        return redirect('/admin')

    cursor.execute("SELECT * FROM Donors WHERE Donor_ID=%s", (id,))
    donor = cursor.fetchone()
    return render_template('update.html', donor=donor)

@app.route('/reset')
def reset():

    cursor.execute("TRUNCATE TABLE Blood_Inventory")

    cursor.execute("""
    INSERT INTO Blood_Inventory
    SELECT * FROM Inventory_Backup
    """)

    cursor.execute("DELETE FROM Requests")

    db.commit()

    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
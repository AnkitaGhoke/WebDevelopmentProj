from geopy.distance import geodesic
import sqlite3
import bcrypt
from datetime import datetime
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import googlemaps
import json


app = Flask(__name__)
app.secret_key = 'SHAAN'

gmaps = googlemaps.Client(key='AIzaSyDYy2MLowsg4DUg4iakgE53D-yhFk78rhQ')


db_path = 'database.db'



def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
            CREATE TABLE IF NOT EXISTS User (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                FirstName TEXT NOT NULL,
                LastName TEXT NOT NULL,
                PhoneNumber TEXT NOT NULL,
                Username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
    # Create Provider table if not exists
    c.execute('''
            CREATE TABLE IF NOT EXISTS Provider (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                FirstName TEXT NOT NULL,
                LastName TEXT NOT NULL,
                Address TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                PhoneNumber TEXT NOT NULL,
                Email TEXT NOT NULL,
                VehicleType TEXT NOT NULL,
                CostPerHour FLOAT NOT NULL
            )
        ''')
    # Create Booking table if not exists
    c.execute('''
            CREATE TABLE IF NOT EXISTS Booking (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                ProviderFirstName TEXT NOT NULL,
                ProviderLastName TEXT NOT NULL,
                ProviderAddress TEXT NOT NULL,
                VehicleType TEXT NOT NULL,
                CostPerHour FLOAT NOT NULL,
                UserFirstName TEXT NOT NULL,
                UserLastName TEXT NOT NULL,
                BookingDate DATE NOT NULL,
                BookingTime TIME NOT NULL,
                TimeDuration INTEGER NOT NULL,
                BookingAmount FLOAT NOT NULL,
                Availability BOOLEAN NOT NULL DEFAULT 1,  -- Assuming 1 means available
                FOREIGN KEY (UserFirstName, UserLastName) REFERENCES User(FirstName, LastName),
                FOREIGN KEY (ProviderFirstName, ProviderLastName, ProviderAddress, VehicleType, CostPerHour) 
                    REFERENCES Provider(FirstName, LastName, Address, VehicleType, CostPerHour)
            )
        ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/Register', methods=['GET', 'POST'])
def Register():
    return render_template('Register.html')

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        try:
            # Get the user data from the form
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            phonenumber = request.form['phonenumber']
            username = request.form['username']
            email = request.form['email']
            createpassword = request.form['createpassword']

            # Hash password before storing
            hashed_password = bcrypt.hashpw(createpassword.encode('utf-8'), bcrypt.gensalt())

            conn = get_db_connection()
            c = conn.cursor()

            # Check if username already exists
            c.execute("SELECT * FROM User WHERE Username = ?", (username,))
            existing_user = c.fetchone()
            if existing_user:
                conn.close()
                return jsonify({'message': 'Username already taken!'}), 409

            # Check if email already exists
            c.execute("SELECT * FROM User WHERE email = ?", (email,))
            existing_email = c.fetchone()
            if existing_email:
                conn.close()
                return jsonify({'message': 'Email already registered!'}), 409

            # Insert the user data into the User table with hashed password
            c.execute("""
                INSERT INTO User (FirstName, LastName, PhoneNumber, Username, email, password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (firstname, lastname, phonenumber, username, email, hashed_password.decode('utf-8')))

            # Commit the changes to the database
            conn.commit()
            conn.close()

            # Send a response back to the client
            return jsonify({'message': 'Registered successfully!'})
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'message': 'Registration failed!'}), 500

@app.route('/Login', methods=['GET', 'POST'])
def Login():
    return render_template('Login.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    print(f"Received data: {data}")  # Debugging line
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    c = conn.cursor()

    # Check if the username exists in the User table
    c.execute("SELECT * FROM User WHERE Username = ?", (username,))
    user = c.fetchone()

    if user:
        print(f"User found: {user['Username']}")  # Debugging line
        # Retrieve hashed password from the database
        stored_password_hash = user['password']
        print(f"Stored password hash: {stored_password_hash}")  # Debugging line

        # Check if the provided password matches the hashed password
        if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
            # Set session variables
            session['user_id'] = user['ID']  # Store user ID in session
            conn.close()
            return jsonify({'message': 'Login successful!'})
        else:
            print("Invalid password")  # Debugging line
            conn.close()
            return jsonify({'message': 'Invalid username or password entered.'}), 401
    else:
        print("User not found")  # Debugging line
        conn.close()
        return jsonify({'message': 'User not registered'}), 401


@app.route('/logout', methods=['GET'])
def logout():
    # Clear the session (logout user)
    session.clear()
    # Invalidate cache
    response = redirect(url_for('home'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.after_request
def add_cache_control(response):
    if 'user_id' in session:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


@app.route('/home1')
def home1():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('home'))  # Redirect to login if user is not logged in

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM User WHERE ID = ?', (user_id,)).fetchone()
    conn.close()

    if user is None:
        return redirect(url_for('Login'))  # Redirect to login if user is not found

    user_initial = user['FirstName'][0].upper() + user['LastName'][0].upper()

    return render_template('home1.html', user=user, user_initial=user_initial, isLoggedIn=True)


@app.route('/forgotpass')
def forgotpass():
    return render_template('forgotpass.html')

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')  # Corrected field name

    conn = get_db_connection()
    c = conn.cursor()

    # Check if email exists in the User table
    c.execute("SELECT * FROM User WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()

    if user:
        # Here you would send an email with a password reset link
        # For demonstration purposes, we'll just return success
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'User not found'}), 404

@app.route('/EnlistProperty', methods=['GET', 'POST'])
def EnlistProperty():
    is_logged_in = 'user_id' in session
    return render_template('enlistproperty.html', my_secret=os.environ.get('GooglemapsAPI'), is_logged_in=is_logged_in)



# Geocode function to get latitude and longitude
def geocode_address(address):
    try:
        geocode_result = gmaps.geocode(address)

        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, None
    except Exception as e:
        print(f"Error geocoding address: {e}")
        return None, None

@app.route('/enlistproperty', methods=['POST'])
def enlistproperty():
    if request.method == 'POST':
        try:
            create_tables()  # Ensure the Provider and Booking tables exist

            # Extract data from the form
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            address = request.form['address']
            phone = request.form['phone']
            email = request.form['email']
            vehicle_type = request.form['vehicle_type']
            cost_per_hour = float(request.form['cost_per_hour'])  # Convert to float

            # Geocode address to get latitude and longitude
            lat, lng = geocode_address(address)

            if lat is None or lng is None:
                return jsonify({'success': False, 'message': 'Failed to geocode the address!'}), 400

            conn = get_db_connection()
            c = conn.cursor()

            # Check if the property already exists
            c.execute("SELECT * FROM Provider WHERE Address = ?", (address,))
            existing_property = c.fetchone()
            if existing_property:
                conn.close()
                return jsonify({'success': False, 'message': 'Property already enlisted!'}), 409

            # Insert into Provider table in the database
            c.execute('''
                INSERT INTO Provider (FirstName, LastName, Address, lat, lng, PhoneNumber, Email, VehicleType, CostPerHour)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (first_name, last_name, address, lat, lng, phone, email, vehicle_type, cost_per_hour))

            
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Property enlisted successfully!'})
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'success': False, 'message': 'Failed to enlist property!'}), 500

        return redirect(url_for('home'))


@app.route('/account_details')
def account_details():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM User WHERE ID = ?', (user_id,)).fetchone()
    conn.close()

    if not user:
        return redirect(url_for('login'))  # Redirect to login if user is not found

    return render_template('Accountdetails.html', user=user)

@app.route('/update_user', methods=['POST'])
def update_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'User not logged in!'}), 401

    try:
        # Extract data from the form
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        phonenumber = request.form['phonenumber']
        email = request.form['email']

        conn = get_db_connection()
        c = conn.cursor()

        # Update the user details in the User table
        c.execute('''
            UPDATE User
            SET FirstName=?, LastName=?, PhoneNumber=?, email=?
            WHERE ID=?
        ''', (firstname, lastname, phonenumber, email, user_id))

        conn.commit()
        conn.close()

        return jsonify({'message': 'User details updated successfully!'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'Failed to update user details!'}), 500


@app.route('/findparking')
def findparking():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('Login'))  # Redirect to login if user is not logged in

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM User WHERE ID = ?', (user_id,)).fetchone()
    conn.close()

    if user is None:
        return redirect(url_for('Login'))  # Redirect to login if user is not found

    user_details = {
        'firstName': user['FirstName'] or 'FirstName',
        'lastName': user['LastName'] or 'LastName'
    }

    logged_in = user_id is not None

    return render_template('findparking.html', user=user_details, logged_in=logged_in)


@app.route('/get_parking_spaces')
def get_parking_spaces():
    vehicle_type = request.args.get('vehicle_type', type=str)
    time_duration = request.args.get('time_duration', type=int)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT FirstName, LastName, Address, VehicleType, CostPerHour, lat, lng
        FROM Provider
        WHERE VehicleType = ?
    ''', (vehicle_type,))
    parking_spaces = c.fetchall()
    conn.close()

    formatted_spaces = []
    for space in parking_spaces:
        formatted_spaces.append({
            'firstName': space['FirstName'],
            'lastName': space['LastName'],
            'address': space['Address'],
            'latitude': space['lat'],
            'longitude': space['lng'],
            'vehicleType': space['VehicleType'],
            'costPerHour': space['CostPerHour'],

        })

    return jsonify(formatted_spaces)

@app.route('/get_parking_locations', methods=['GET'])
def get_parking_locations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch latitude and longitude data from provider table
        cursor.execute('SELECT lat, lng, firstName, lastName, address, vehicleType, costPerHour FROM provider')
        parking_locations = cursor.fetchall()

        # Structure data in a format suitable for JSON response
        parking_data = []
        for location in parking_locations:
            firstName, lastName, address, lat, lng, vehicleType, costPerHour = location
            parking_data.append({
                'firstName': firstName,
                'lastName': lastName,
                'address': address,
                'lat': lat,
                'lng': lng,
                'vehicleType': vehicleType,
                'costPerHour': costPerHour
            })

        return jsonify({'success': True, 'parking_locations': parking_data})

    except Exception as e:
        print(f"Error fetching parking locations: {e}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if conn:
            conn.close()


@app.route('/book_parking', methods=['POST'])
def book_parking():
    if 'user_id' not in session:
        return jsonify(success=False, message="User not logged in"), 401

    data = request.json

    user_id = session['user_id']

    provider_first_name = data.get('provider_first_name')
    provider_last_name = data.get('provider_last_name')

    # Ensure required fields are provided
    if not (provider_first_name and provider_last_name):
        return jsonify(success=False, message="Missing required fields"), 400

    conn = get_db_connection()
    c = conn.cursor()

    # Fetch user details
    c.execute("SELECT FirstName, LastName FROM User WHERE ID = ?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify(success=False, message="User not found"), 404

    user_first_name = user['FirstName']
    user_last_name = user['LastName']

    # Fetch provider details
    c.execute('''
        SELECT Address, VehicleType, CostPerHour 
        FROM Provider 
        WHERE FirstName = ? AND LastName = ?
    ''', (provider_first_name, provider_last_name))
    provider = c.fetchone()
    if not provider:
        conn.close()
        return jsonify(success=False, message="Provider not found"), 404

    provider_address = provider['Address']
    vehicle_type = provider['VehicleType']
    cost_per_hour = provider['CostPerHour']

    booking_date = data.get('booking_date')
    booking_time = data.get('booking_time')
    time_duration = data.get('time_duration')
    booking_amount = cost_per_hour * time_duration
    availability = data.get('availability', True)

    # Ensure required booking fields are provided
    if not (booking_date and booking_time and time_duration):
        return jsonify(success=False, message="Missing required booking fields"), 400

    try:
        # Insert booking details into the Booking table
        c.execute('''
            INSERT INTO Booking (ProviderFirstName, ProviderLastName, ProviderAddress, VehicleType, CostPerHour, UserFirstName, UserLastName, BookingDate, BookingTime, TimeDuration, BookingAmount, Availability)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (provider_first_name, provider_last_name, provider_address, vehicle_type, cost_per_hour, user_first_name,
              user_last_name, booking_date, booking_time, time_duration, booking_amount, availability))

        conn.commit()
        conn.close()

        return jsonify(success=True, message="Parking booked successfully")
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify(success=False, message="Failed to book parking", error=str(e))

@app.route('/bookingconfirmation')
def booking_confirmation():
    return render_template('bookingconfirmation.html')

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
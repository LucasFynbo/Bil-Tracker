import os
from flask import Flask, request, jsonify
import mysql.connector as mysql
from mysql.connector import Error, OperationalError
import secrets
import bcrypt
import time

app = Flask(__name__)

class DatabaseConnection:
    def __init__(self):
        self.db = None
        self.mycursor = None
        self.connect()

    def connect(self):
        try:
            self.db = mysql.connect(
                unix_socket="/var/run/mysqld/mysqld.sock",
                user="tracker",
                passwd=os.getenv("MY_DB_PASSWORD"),
                database="biltracker",
                connection_timeout=300
            )
            self.mycursor = self.db.cursor(dictionary=True)
            print("Connected to database")
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def reconnect(self):
        if self.db is None or not self.db.is_connected():
            self.connect()

    def execute_query(self, query, params=None):
        self.reconnect()
        try:
            self.mycursor.execute(query, params)
        except OperationalError as err:
            if err.errno in (mysql.errorcode.CR_SERVER_LOST, mysql.errorcode.CR_SERVER_GONE_ERROR):
                print("Lost connection to MySQL server, attempting to reconnect...")
                self.reconnect()
                self.mycursor.execute(query, params)
            else:
                print(f"Error executing query: {err}")
                raise

    def fetchall(self):
        return self.mycursor.fetchall()

    def fetchone(self):
        return self.mycursor.fetchone()

    def fetchone_column(self, column):
        row = self.fetchone()
        if row:
            return row.get(column)
        return None

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def get_row_count(self):
        return self.mycursor.rowcount


class DataHandler:
    def __init__(self):
        self.db_connection = DatabaseConnection()

    def received_coords(self, lat=None, long=None, tracker_id=None):
        """
            Successful tracker-id verification, results in a "result" variable value of:
                result = {'Tracker_id': 'Tracker#53355'} 

            If verification fails, "result" value is of NoneType.
        """
        try:
            # Tjek 'Tracker_enheder' tabellen om 'Tracker_id' eksisterer.
            query = "SELECT Tracker_id FROM Tracker_enheder WHERE Tracker_id = %s"
            self.db_connection.execute_query(query, (tracker_id,))
            result:str = self.db_connection.fetchone()

            if result is None:
                return {"status": "error", "message": "Tracker identification not found"}, 404

            query = "INSERT INTO Lokation_log (latitude, longitude, Tracker_id, Tidspunkt) VALUES (%s, %s, %s, NOW())"
            self.db_connection.execute_query(query, (lat, long, tracker_id,))
            self.db_connection.commit()

            return {"status": "success", "message": "Coordinates insertion successful"}, 200

        except Exception as e:
            print(f"Exception in received_coords:", e)
            self.db_connection.rollback()
            return {"status": "error", "message": "Error during coordinates insertion"}, 500

    def get_coords(self, tracker_id=None, tracker_password=None):
        """
            Runs bcrypt password check before sending coordinates to client device.

            This is to implement a layer of security if spoofing of tracker device occurs.

            A successful "result = self.db_connection.fetchone()" value:
                result = {'Password': '$2b$12$s.NgSTS72KVed0mEXZ5r9ObbCtph3PtpfeefsjibgO10tFnwCpvSW'}

            If fetchone is not successful (wrong tracker-id in this case), result is of NoneType.
        """

        try:
            query = "SELECT Password FROM Tracker_enheder WHERE Tracker_id = %s"
            self.db_connection.execute_query(query, (tracker_id,))
            result:str = self.db_connection.fetchone()

            if bcrypt.checkpw(tracker_password.encode('utf-8'), result['Password'].encode('utf-8')):

                query = "SELECT Latitude, Longitude FROM Lokation_log WHERE Tracker_id = %s ORDER BY Tidspunkt DESC LIMIT 1;"
                self.db_connection.execute_query(query, (tracker_id,))
                coordinates = self.db_connection.fetchone()

                latitude = float(coordinates['Latitude'])
                longitude = float(coordinates['Longitude'])

                return {"status": "success", 
                        "message": "Received coordinates successfully", 
                        "longitude": longitude, "latitude": latitude}, 200

        except Exception as e:
            print(f"Exception in get_coords:", e)
            return {"status": "error", "message": "Error retrieving coordinate data"}, 500

    def generate_tracker_id(self):
        """
            Generates tracker id when requested. Loops until fetchone request of the generated ID results in 'None'.

            If generated ID exists, result of fetch will return the row containing the already existing ID and password - this data is not used:

            "result = self.db_connection.fetchone()" result if ID exists already:
                
                result = {'Tracker_id': 'Tracker#26349', 'Password': None}

            "result = self.db_connection.fetchone()" result if ID doesn't exists already:

                result = None

        """

        while True:
            rtal = secrets.choice(range(10000, 99999))
            tracker_id = ('Tracker#' + str(rtal))

            query = "SELECT * FROM Tracker_enheder WHERE Tracker_id = %s"
            self.db_connection.execute_query(query, (tracker_id,))
            result:str = self.db_connection.fetchone()

            if result is None:
                try:
                    query = "INSERT INTO Tracker_enheder (Tracker_id) VALUES (%s)"
                    self.db_connection.execute_query(query, (tracker_id,))
                    self.db_connection.commit()

                    print('[+] Tracker identification number successfully generated: %s' % (tracker_id))

                    time.sleep(2)

                    return {"status": "success", 
                            "message": "Successfully generated tracker identification", 
                            "tracker_id": tracker_id}, 200

                except Exception as e:
                    print(f"Exception in generate_tracker_id:", e)
                    self.db_connection.rollback()
                    return {"status": "error", "message": "Error generating tracker identification"}, 500
            else:
                print('[!] Device ID: %s already exist in the database, retrying...' % tracker_id)

    def password_reset(self, tracker_id):
        try:
            delete_log_query = "DELETE FROM Lokation_log WHERE Tracker_id = %s"
            self.db_connection.execute_query(delete_log_query, (tracker_id,))

            query = "UPDATE Tracker_enheder SET Password = NULL WHERE Tracker_id = %s"
            self.db_connection.execute_query(query, (tracker_id,))
            
            self.db_connection.commit()

            return {"status": "success", "message": "Password reset procedure exited successfully"}, 200

        except Exception as e:
            print(f"Exception in password_reset:", e)
            self.db_connection.rollback()
            return {"status": "error", "message": "Error executing password reset procedure."}, 500

    def password_update(self, tracker_id, tracker_password):
        """
            Successful tracker-id verification, results in a "result" variable value of:
                result = {'Tracker_id': 'Tracker#53355'} 

            If verification fails, "result" value is of NoneType.

            Password update only suceeds on Tracker'ids with currently non-set password values (NULL).
        """

        # Tjek 'Tracker_enheder' tabellen om 'Tracker_id' eksisterer.
        query = "SELECT Tracker_id FROM Tracker_enheder WHERE Tracker_id = %s"
        self.db_connection.execute_query(query, (tracker_id,))
        result:str = self.db_connection.fetchone()

        if result is None:
            return {"status": "error", "message": "Tracker identification not found"}, 404

        try:
            hashed_password = bcrypt.hashpw(tracker_password.encode('utf-8'), bcrypt.gensalt())

            query = "UPDATE Tracker_enheder SET Password = %s WHERE Tracker_id = %s AND Password IS NULL"
            self.db_connection.execute_query(query, (hashed_password.decode('utf-8'), tracker_id,))
            rows_updated = self.db_connection.get_row_count()
            self.db_connection.commit()

            if rows_updated > 0:
                return {"status": "success", "message": "Password updated successfully"}, 200
            else:
                return {"status": "error", "message": "Password update failed. Password may already be set or Tracker_id is invalid."}, 400

        except Exception as e:
            print(f"Exception in password_reset:", e)
            self.db_connection.rollback()
            return {"status": "error", "message": "Error executing password update procedure."}, 500


data_handler = DataHandler()
@app.route('/', methods=['POST'])
def handle():
    data = request.json

    print(data)

    subject = data.get('data')

    match(subject):
        case "received coords":
            coords_lat = data.get('coords_lat')
            coords_long = data.get('coords_long')
            tracker_id = data.get('tracker_id')

            if not coords_lat or not coords_long or not tracker_id:
                return jsonify({"status": "error", "message": "No coordinates or tracker identification specified in received data"}), 400

            result, status_code = data_handler.received_coords(lat=coords_lat, long=coords_long, tracker_id=tracker_id)
            return jsonify(result), status_code

        case "get coords":
            tracker_id = data.get('tracker_id')
            tracker_password = data.get('password')

            if not tracker_id or not tracker_password:
                return jsonify({"status": "error", "message": "No tracker identification or password specified in received data"}), 400

            result, status_code = data_handler.get_coords(tracker_id=tracker_id, tracker_password=tracker_password)
            return jsonify(result), status_code

        case "tracker id request":
            result, status_code = data_handler.generate_tracker_id()
            return jsonify(result), status_code

        case "reset password request":
            tracker_id = data.get('tracker_id')

            if not tracker_id:
                return jsonify({"status": "error", "message": "No tracker identification specified in received data"}), 400

            result, status_code = data_handler.password_reset(tracker_id)
            return jsonify(result), status_code

        case "update password request":
            tracker_id = data.get('tracker_id')
            tracker_password = data.get('tracker_password')

            if not tracker_id or not tracker_password:
                return jsonify({"status": "error", "message": "No tracker identification or password specified in received data"}), 400

            result, status_code = data_handler.password_update(tracker_id, tracker_password)
            return jsonify(result), status_code

        case _:
            return jsonify({"status": "error", "message": "Error handeling received data"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=13371)
from flask import Flask, request, jsonify
import mysql.connector as mysql
from mysql.connector import Error, OperationalError

app = Flask(__name__)

class DatabaseConnection:
    def __init__(self):
        self.db = None
        self.mycursor = None
        self.connect()

    def connect(self):
        try:
            self.db = mysql.connect(
                host="79.171.148.163",
                user="user",
                passwd="MaaGodt*7913!",
                database="LogunitDB",
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

db_connection = DatabaseConnection()

data_handler = DataHandler()
@app.route('/', methods=['POST'])
def handle():
    data = request.json

    print(data)

if __name__ == "__main__":
    app.run(debug=True, port=13371)
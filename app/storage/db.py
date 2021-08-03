from pathlib import Path
import os
import sqlite3

class Database(object):
    def __init__(self, **kw):
        super().__init__(**kw)
        home = str(Path.home())
        self.datapath = os.path.join(home, 'Documents','.kivylive')

        if not os.path.exists(self.datapath):
            try:
                os.mkdir(self.datapath)
            except:
                print('failed to init directory structure')

            conn = sqlite3.connect(os.path.join(self.datapath, 'db.sqlite'))

            sql = 'CREATE TABLE kvdata (id integer primary key, path text not null)'

            cur = conn.cursor()
            result = cur.execute(sql)
            
            if result:
                print("Successfully initialized the db")
            else:
                print("Failed to Initialize the db")
            conn.commit()
        else:
            print('Skipping as directory exists')

    def db_connect(self):
        """Connect to the database and return the connection

        Returns
        -------
        sqlite3.connection
            The database connection

        """
        conn = sqlite3.connect(os.path.join(self.datapath, 'db.sqlite'))

        return conn

    def add_kv(self, path: str):
        """Add a path to a created kv file

        Parameters
        ----------
        path : str
            The file location of the .kv file.

        Returns
        -------
        bool
            Return True if added successfully otherwise False

        """
        conn = self.db_connect()
        cur = conn.cursor()
        # print(f'type is {type(path)} and {path}')
        sql = 'INSERT INTO kvdata(path) VALUES(?)'

        try:
            cur.execute(sql, [path])
            conn.commit()

            return True
        except Exception as e:
            print(e)
            return False

    def get_kvs(self):
        conn = self.db_connect()
        cur = conn.cursor()
        sql = 'SELECT path FROM kvdata'

        try:
            cur.execute(sql)
            conn.commit()

            dat = cur.fetchall()

            return dat
        except Exception as e:
            print(e)
            return []

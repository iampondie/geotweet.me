import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from geotweet_me import app

if __name__ == "__main__":
    app.run(host=app.config['HOST'], port=app.config['PORT'])
    

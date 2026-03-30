from flask import Flask
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.secret_key = 'test'
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id='test-client-id',
    client_secret='test-client-secret',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    authorize_params={'prompt': 'select_account'},
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@app.route("/")
def test():
    # Calling authorize_redirect directly
    return google.authorize_redirect('http://localhost/callback')

if __name__ == "__main__":
    with app.test_request_context('/'):
        resp = test()
        print("GENERATED AUTH URL:")
        print(resp.headers.get('Location'))

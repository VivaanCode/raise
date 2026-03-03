from flask import Flask, render_template
import api

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/donate/<id>")
def donate(id):
    org_name = api.get_organization_name(id)
    return render_template("donate.html", organization=org_name)

if __name__ == "__main__":
    app.run(debug=True)
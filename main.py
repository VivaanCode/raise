from flask import Flask, redirect, render_template, request
import api

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/donate/<id>")
def donate(id):
    outcome, org_name = api.get_organization_name(id)
    if not outcome:
        return "Organization not found", 404
    
    referrer = request.args.get("referrer")
    donation_id = api.assign_donation_id(id)

    if not referrer:
        return redirect("https://hcb.hackclub.com/donations/start/" + id)
    
    return render_template("donate.html", organization=org_name, referrer=referrer, id=donation_id)

if __name__ == "__main__":
    app.run(debug=True)
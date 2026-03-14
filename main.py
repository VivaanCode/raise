from flask import Flask, redirect, render_template, request
import api

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/org/<id>")
def org(id):
    outcome, org_name = api.get_organization_name(id)
    if not outcome:
        return "Organization not found", 404
    
    referrer = request.args.get("referrer")
    if not referrer:
        return redirect("https://hcb.hackclub.com/donations/start/" + id)
    
    return render_template("org.html", organization=org_name, referrer=referrer, org_id=id)

@app.route("/org/<id>/donate", methods=["GET", "POST"])
def org_donate(id):
    outcome, org_name = api.get_organization_name(id)
    if not outcome:
        return redirect("/org/" + id)

    referrer = request.args.get("referrer")
    amount = request.args.get("amount")
    name = request.args.get("name")
    email = request.args.get("email")

    if not referrer or not amount or not name or not email:
        return redirect("/org/" + id)
    
    try:
        success, donation_id = api.add_donation(id, name, email, referrer)
        amount = int(amount)
    except:
        return redirect("/org/" + id)
    if amount <=0:
        return redirect("/org/" + id)
    
    amount_cents = amount * 100
    
    return render_template("donate.html", 
                           organization=org_name, 
                           referrer=referrer, 
                           id=donation_id, 
                           org_id=id, 
                           name=name, 
                           email=email, 
                           amount_cents=amount_cents, 
                           amount=amount)

@app.route("/donate/<id>/success")
def donate_success(id):
    outcome, donation_info = api.get_donation_info(id)
    if not outcome:
        return "Donation not found", 404
    
    return render_template("success.html", 
                           organization=donation_info["organization_name"], 
                           referrer=donation_info["referrer"], 
                           name=donation_info["name"], 
                           email=donation_info["email"], 
                           amount=donation_info["amount"])

@app.route("/api/create_fundraiser", methods=["POST"])
def create_fundraiser():
    try:
        success, fundraiser_id = api.create_fundraiser(request.form["org_id"], request.form["fundraiser_name"], request.form["end_time"], int(request.form["goal_cents"]), request.form["password"])
        if success:
            return "Fundraiser created successfully", 201
    except Exception as e:
        return f"Error creating fundraiser: {str(e)}", 400
    return "Error creating fundraiser", 400

@app.route("/api/fundraiser/<id>/add_donation", methods=["POST"])
def add_donation(id):
    try:
        success, donation_id = api.add_donation(id, request.form["name"], request.form["email"], request.form["referrer"])
        if success:
            return donation_id, 200
    except Exception as e:
        return str(e), 400
    return "Error", 400 

@app.route("/create_fundraiser")
def create_fundraiser_page():
    if request.args.org:
        return render_template("create_fundraiser.html", org_id=request.args.org)
    return render_template("create_fundraiser.html")

if __name__ == "__main__":
    app.run(debug=True)
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

@app.route("/org/<id>/donate")
def org_donate(id):
    outcome, org_name = api.get_organization_name(id)
    if not outcome:
        return redirect("/org/" + id)

    referrer = request.args.get("referrer")
    amount = request.args.get("amount")
    name = request.args.get("name")
    email = request.args.get("email")
    donation_id = api.assign_donation_id(id)

    if not referrer or not amount or not name or not email:
        return redirect("/org/" + id)
    
    try:
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

if __name__ == "__main__":
    app.run(debug=True)
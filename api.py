import requests, random

def assign_donation_id(org):
    id = ""
    for x in range(6):
        id += str(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
    res = requests.get(f"https://hcb.hackclub.com/api/v3/organizations/{org}/")
    donations = res.json()
    for d in donations:
        donor = d["donor"]["name"]
        if id in donor:
            return assign_donation_id(org)
    return id

def check_donation(org, id):
    res = requests.get(f"https://hcb.hackclub.com/api/v3/organizations/{org}/donations")
    donations = res.json()
    for d in donations:
        donor = d["donor"]["name"]
        amount = int(d["amount_cents"])
        if str(id).lower() in donor.lower():
            return True, amount
    return False, 0


def get_organization_name(org):
    res = requests.get(f"https://hcb.hackclub.com/api/v3/organizations/{org}")
    if res.status_code != 200:
        return False, None
    info = res.json()
    name = info["name"]
    # https://hcb.hackclub.com/docs/api/v3/operations/get-a-single-organization
    # for some reason, name is an optional field, so i have to
    # check if it exists before returning it
    if name:
        return True, name
    else:
        return True, org
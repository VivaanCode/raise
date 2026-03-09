import os
import psycopg2
import bcrypt
import requests, random
from datetime import timezone

DATABASE_URL = os.getenv("DATABASE_URL")
conn = None

def dbInit():
    global conn
    conn = psycopg2.connect(DATABASE_URL, options="-c timezone=UTC")

    with conn.cursor() as c:
        c.execute("SET TIME ZONE 'UTC'")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS fundraisers (
                id text PRIMARY KEY,
                org text NOT NULL,
                fundraiser_name text NOT NULL,
                end_time timestamptz NOT NULL,
                goal_cents integer NOT NULL,
                password_hash text NOT NULL)
            """
        )
    conn.commit()

def assign_fundraiser_id(org):
    id = ""
    for x in range(10):
        id += str(random.choice("1234567890"))
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id FROM fundraisers WHERE id = %s
                """,
                (id,)
            )
            result = c.fetchone()
            if result:
                return assign_fundraiser_id(org)
    except psycopg2.InterfaceError as e:
        dbInit()
        return assign_fundraiser_id(org)
    return id

def assign_donation_id(org):
    id = ""
    for x in range(6):
        id += str(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"))
    res = requests.get(f"https://hcb.hackclub.com/api/v3/organizations/{org}/donations")
    donations = res.json()
    for d in donations:
        donor = d["donor"]["name"]
        if id.lower() in donor.lower():
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

def create_fundraiser(org, fundraiser_name, fundraiser_description, goal_cents, length_days, fundraiser_password):
    password_hash = bcrypt.hashpw(fundraiser_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    orgNameSuccess, orgName = get_organization_name(org)
    if not orgNameSuccess:
        return False, "Organization not found"
    
    if length_days <= 0:
        return False, False
    if length_days > 60:
        return False, False
    try:
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO fundraisers (id, org, fundraiser_name, end_time, goal_cents, password_hash)
                VALUES (%s, %s, %s, NOW() + INTERVAL '%s days', %s, %s)
                """,
                (fundraiser_name, org, fundraiser_name, length_days, goal_cents, password_hash)
            )
        conn.commit()
        return True, assign_fundraiser_id(org)
    except psycopg2.InterfaceError as e:
        #print(e)
        dbInit()
        return create_fundraiser(org, fundraiser_name, fundraiser_description, goal_cents, length_days, fundraiser_password)
    
def check_fundraiser_password(org, password, fundraiser_name):
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT password_hash FROM fundraisers WHERE org = %s AND fundraiser_name = %s
                """,
                (org, fundraiser_name)
            )
            result = c.fetchone()
            if result:
                return bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8'))
            else:
                return False
    except psycopg2.InterfaceError as e:
        #print(e)
        dbInit()
        return check_fundraiser_password(org, password, fundraiser_name)
    
def get_fundraiser(id):
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT fundraiser_name, end_time, goal_cents FROM fundraisers WHERE id = %s
                """,
                (id,)
            )
            result = c.fetchone()
            if result:
                end_time_utc = result[1].astimezone(timezone.utc)
                return True, {"fundraiser_name": result[0], "end_time": end_time_utc, "goal_cents": result[2]}
            else:
                return False, None
    except psycopg2.InterfaceError as e:
        #print(e)
        dbInit()
        return get_fundraiser(id)
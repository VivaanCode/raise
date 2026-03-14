import os
import psycopg2
import bcrypt
import requests, random
from datetime import timezone, datetime
import dotenv

if not os.getenv("DATABASE_URL"):
    dotenv.load_dotenv()
    if not os.getenv("DATABASE_URL"):
        raise Exception("Assign the DATABASE_URL enviormment variable.")

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
                password_hash text NOT NULL,
                users jsonb NOT NULL DEFAULT '[]'::jsonb,
                donations jsonb NOT NULL DEFAULT '[]'::jsonb)
            """
        )
    conn.commit()

def add_donation(fundraiser_id, name, email, referrer):
    success, fundraiser_info = get_fundraiser_info(fundraiser_id)
    donation_id = assign_donation_id(fundraiser_info["org"])
    if not success:
        return False, "Fundraiser not found"
    try:
        with conn.cursor() as c:
            c.execute(
                """
                UPDATE fundraisers
                SET donations = array_append(donations, %s)
                WHERE id = %s
                """,
                ({"id": donation_id, "name": name, "email": email, "referrer": referrer, "fulfilled": False, "amount_cents": 0, "time_created": datetime.now(timezone.utc)}, fundraiser_id)
            )
        conn.commit()
    except psycopg2.InterfaceError as e:
        dbInit()
        add_donation(fundraiser_id, name, email, referrer)
    return True, donation_id

def mark_donation_fulfilled(fundraiser_id, donation_id, amount_cents):
    success, fundraiser_info = get_fundraiser_info(fundraiser_id)
    if not success:
        return False
    donations = fundraiser_info["donations"]
    for d in donations:
        if d["id"] == donation_id:
            d["fulfilled"] = True
            d["amount_cents"] = amount_cents
    try:
        with conn.cursor() as c:
            c.execute(
                """
                UPDATE fundraisers
                SET donations = %s
                WHERE id = %s
                """,
                (donations, fundraiser_id)
            )
        conn.commit()
    except psycopg2.InterfaceError as e:
        dbInit()
        mark_donation_fulfilled(fundraiser_id, donation_id, amount_cents)
    return True

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
    fundraiser_id = assign_fundraiser_id(org)

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
                (fundraiser_id, org, fundraiser_name, length_days, goal_cents, password_hash)
            )
        conn.commit()
        return True, fundraiser_id
    except psycopg2.InterfaceError as e:
        #print(e)
        dbInit()
        return create_fundraiser(org, fundraiser_name, fundraiser_description, goal_cents, length_days, fundraiser_password)
    
def check_fundraiser_password(password, fundraiser_id):
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT password_hash FROM fundraisers WHERE id = %s
                """,
                (fundraiser_id,)
            )
            result = c.fetchone()
            if result:
                return bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8'))
            else:
                return False
    except psycopg2.InterfaceError as e:
        #print(e)
        dbInit()
        return check_fundraiser_password(password, fundraiser_id)
    
def get_fundraiser_info(id):
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
        return get_fundraiser_info(id)

def get_fundraiser_cents(id):
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT donations FROM fundraisers WHERE id = %s
                """,
                (id,)
            )
            result = c.fetchone()
            if result:
                donations = result[0]
                total_cents = 0
                for d in donations:
                    if d["fulfilled"]:
                        total_cents += d["amount_cents"]
                return True, total_cents
            else:
                return False, None
    except psycopg2.InterfaceError as e:
        dbInit()
        return get_fundraiser_cents(id)
    

def get_fundraiser_donations(id):
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT donations FROM fundraisers WHERE id = %s
                """,
                (id,)
            )
            result = c.fetchone()
            if result:
                return True, result[0]
            else:
                return False, None
    except psycopg2.InterfaceError as e:
        dbInit()
        return get_fundraiser_donations(id)
import firebase_admin
from firebase_admin import credentials, firestore
from . import safe_get_env_var
import json
from mockfirestore import MockFirestore

cert_env = json.loads(safe_get_env_var("FIREBASE_CERT_CONFIG"))
cred = credentials.Certificate(cert_env)
firebase_admin.initialize_app(credential=cred)

mockfirestore = MockFirestore() #Only used when testing 

# add logger
import logging
logger = logging.getLogger(__name__)
# set log level
logger.setLevel(logging.INFO)


def get_db():
    if safe_get_env_var("ENVIRONMENT") == "test":
        return mockfirestore
    
    return firestore.client()

def get_team_by_name(team_name):
    db = get_db()  # this connects to our Firestore database
    docs = db.collection('teams').where("name", "==", team_name).stream()

    for doc in docs:
        adict = doc.to_dict()
        return adict["slack_channel"]


def get_users_in_team_by_name(team_name):
    db = get_db()  # this connects to our Firestore database
    docs = db.collection('teams').where("name", "==", team_name).stream()

    user_list = []
    for doc in docs:
        adict = doc.to_dict()
        for user in adict["users"]:
            auser = user.get().to_dict()
            user_list.append(auser)
    return user_list

def get_user_by_id(id):
    db = get_db()  # this connects to our Firestore database
    doc = db.collection('users').document(id).get()
    adict = doc.to_dict()
    adict["id"] = doc.id
    return adict

def get_user_by_email(email_address):
    db = get_db()  # this connects to our Firestore database
    docs = db.collection('users').where("email_address", "==", email_address).stream()

    for doc in docs:
        adict = doc.to_dict()
        adict["id"] = doc.id
        return adict


def create_user(name, email_address, slack_id):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Creating user {name} {email_address}")

    user = get_user_by_email(email_address)
    if user:
        logger.info("user already exists")
        return user
    else:
        logger.info("user does not exist")
        user = {
            "name": name,
            "email_address": email_address,
            "profile_image": "https://i.imgur.com/mJSr58l.png",
            "user_id": slack_id
        }
        logger.info(f"Adding user {user}")
        db.collection("users").add(user)
        return user

def add_user_to_team(userid, teamid):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding user {userid} to team {teamid}")

    # Get team
    team = db.collection("teams").document(teamid).get()

    if not team.exists:
        logger.error(f"**ERROR Team {teamid} does not exist")
        raise Exception(f"Team {teamid} does not exist")

    # Get user
    user = db.collection("users").document(userid).get()

    if not user.exists:
        logger.error(f"**ERROR User {userid} does not exist")
        raise Exception(f"User {userid} does not exist")

    # Check if user is already in team
    team_users = team.to_dict()["users"]
    
    # Add user to team
    team_users = team.to_dict()["users"]
    if user.reference in team_users:
        logger.info(f"User {userid} is already in team {teamid}, not adding again")        
    else:
        team_users.append(user.reference)
        db.collection("teams").document(teamid).set({"users": team_users}, merge=True)

    # Add team to user    
    user_teams = user.to_dict()
    if "teams" not in team_users:
        user_teams = []        
    if team.reference in user_teams:
        logger.info(f"Team {teamid} is already in user {userid}, not adding again")
    else:
        user_teams.append(team.reference)
        db.collection("users").document(userid).set({"teams": user_teams}, merge=True)

def remove_user_from_team(userid, teamid):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Removing user {userid} from team {teamid}")

    # Get team
    team = db.collection("teams").document(teamid).get()

    if not team.exists:
        logger.error(f"**ERROR Team {teamid} does not exist")
        raise Exception(f"Team {teamid} does not exist")

    # Get user
    user = db.collection("users").document(userid).get()

    if not user.exists:
        logger.error(f"**ERROR User {userid} does not exist")
        raise Exception(f"User {userid} does not exist")

    # Remove user from team
    if "users" not in team.to_dict():
        logger.warning(f"Team {teamid} has no users, not removing")
    else:    
        team_users = team.to_dict()["users"]
        if user.reference in team_users:
            team_users.remove(user.reference)
            db.collection("teams").document(teamid).set({"users": team_users}, merge=True)
        else:
            logger.info(f"User {userid} is not in team {teamid}, not removing")

    # Remove team from user
    if "teams" not in user.to_dict():
        logger.warning(f"User {userid} has no teams, not removing")
    else:
        user_teams = user.to_dict()["teams"]
        if team.reference in user_teams:
            user_teams.remove(team.reference)
            db.collection("users").document(userid).set({"teams": user_teams}, merge=True)
        else:
            logger.info(f"Team {teamid} is not in user {userid}, not removing")

def delete_user_by_id(userid):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Deleting user {userid}")

    # Get user
    user = db.collection("users").document(userid).get()

    if not user.exists:
        logger.error(f"**ERROR User {userid} does not exist")
        raise Exception(f"User {userid} does not exist")

    # Delete user from all teams
    if "teams" in user.to_dict():
        user_teams = user.to_dict()["teams"]
        for team in user_teams:
            team_users = team.get().to_dict()["users"]
            team_users.remove(user.reference)
            db.collection("teams").document(team.id).set({"users": team_users}, merge=True)

    # Delete user
    db.collection("users").document(userid).delete()

def add_user_by_email_to_team(email_address, team_name):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding user {email_address} to team {team_name}")

    # Get team
    team = db.collection("teams").where("name", "==", team_name).get()

    if not team:
        logger.error(f"**ERROR Team {team_name} does not exist")
        raise Exception(f"Team {team_name} does not exist")

    # Get user
    user = db.collection("users").where("email_address", "==", email_address).get()

    if not user:
        logger.error(f"**ERROR User {email_address} does not exist")
        raise Exception(f"User {email_address} does not exist")

    # Check if user is already in team
    team_users = team.to_dict()["users"]
    
    # Add user to team
    team_users = team.to_dict()["users"]
    if user.reference in team_users:
        logger.info(f"User {email_address} is already in team {team_name}, not adding again")        
    else:
        team_users.append(user.reference)
        db.collection("teams").document(team.id).set({"users": team_users}, merge=True)

    # Add team to user    
    user_teams = user.to_dict()
    if "teams" not in team_users:
        user_teams = []        
    if team.reference in user_teams:
        logger.info(f"Team {team_name} is already in user {email_address}, not adding again")
    else:
        user_teams.append(team.reference)
        db.collection("users").document(user.id).set({"teams": user_teams}, merge=True)

def add_user_by_slack_id_to_team(user_id, team_name):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding user {user_id} to team {team_name}")

    # If user_id doesn't have oauth2|slack|T1Q7936BH- prefix, add it
    if not user_id.startswith("oauth2|slack|T1Q7936BH-"):
        user_id = "oauth2|slack|T1Q7936BH-" + user_id


    # Get team
    team = db.collection("teams").where("name", "==", team_name).get()

    if not team:
        logger.error(f"**ERROR Team {team_name} does not exist")
        raise Exception(f"Team {team_name} does not exist")

    # Get user
    user = db.collection("users").where("user_id", "==", user_id).get()

    if not user:
        logger.error(f"**ERROR User {user_id} does not exist")
        raise Exception(f"User {user_id} does not exist")

    # Check if user is already in team
    team_users = team.to_dict()["users"]
    if user.reference in team_users:
        logger.info(f"User {user_id} is already in team {team_name}, not adding again")        
    else:
        team_users.append(user.reference)
        db.collection("teams").document(team.id).set({"users": team_users}, merge=True)

    # Add team to user    
    user_teams = user.to_dict()
    if "teams" not in team_users:
        user_teams = []        
    if team.reference in user_teams:
        logger.info(f"Team {team_name} is already in user {user_id}, not adding again")
    else:
        user_teams.append(team.reference)
        db.collection("users").document(user.id).set({"teams": user_teams}, merge=True)

def add_team_to_hackathon(team_id, hackathon_id):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding team {team_id} to hackathon {hackathon_id}")

    # Get hackathon
    hackathon = db.collection("hackathons").document(hackathon_id).get()

    if not hackathon.exists:
        logger.error(f"**ERROR Hackathon {hackathon_id} does not exist")
        raise Exception(f"Hackathon {hackathon_id} does not exist")

    # Get team
    team = db.collection("teams").document(team_id).get()

    if not team.exists:
        logger.error(f"**ERROR Team {team_id} does not exist")
        raise Exception(f"Team {team_id} does not exist")

    # Check if team is already in hackathon
    hackathon_teams = hackathon.to_dict()["teams"]
    if team.reference in hackathon_teams:
        logger.info(f"Team {team_id} is already in hackathon {hackathon_id}, not adding again")
    else:
        hackathon_teams.append(team.reference)
        db.collection("hackathons").document(hackathon_id).set({"teams": hackathon_teams}, merge=True)

    

def add_problem_statement_to_team(problem_statement_id, team_id):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding problem statement {problem_statement_id} to team {team_id}")

    # Get team
    team = db.collection("teams").document(team_id).get()

    if not team.exists:
        logger.error(f"**ERROR Team {team_id} does not exist")
        raise Exception(f"Team {team_id} does not exist")

    # Get problem statement
    problem_statement = db.collection("problem_statements").document(problem_statement_id).get()

    if not problem_statement.exists:
        logger.error(f"**ERROR Problem statement {problem_statement_id} does not exist")
        raise Exception(f"Problem statement {problem_statement_id} does not exist")

    # Add problem statement to team
    problem_statements = team.to_dict()["problem_statements"]
    if problem_statement.reference in problem_statements:
        logger.info(f"Problem statement {problem_statement_id} is already in team {team_id}, not adding again")        
    else:
        problem_statements.append(problem_statement.reference)
        db.collection("teams").document(team_id).set({"problem_statements": problem_statements}, merge=True)

    

def create_team(name):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Creating team {name}")

    team = get_team_by_name(name)
    if team:
        logger.info("team already exists")
        return team
    else:
        logger.info("team does not exist")
        team = {
            "name": name,
            "active": True,
            "slack_channel": "",
            "team_number": -1,
            "problem_statements": [],
            "users": []
        }
        logger.info(f"Adding team {team}")
        db.collection("teams").add(team)
        return team

def get_nonprofit_by_name(name):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Getting nonprofit {name}")

    nonprofit = db.collection("nonprofits").where("name", "==", name).get()
    if nonprofit:
        logger.info("nonprofit exists")
        # convert DocumentSnapshot to DocumentReference
        result = []
        for thing in nonprofit:
            result.append(thing.reference)

        return result
    else:
        logger.info("nonprofit does not exist")
        return None

def create_new_hackathon(title, type, links, teams, donation_current, donation_goals, location, nonprofits, start_date, end_date):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Creating hackathon {title}")

    # check if hackathon already exists by start_date or end_date
    hackathon = db.collection("hackathons").where("start_date", "==", start_date).get()
    if hackathon:
        logger.info(f"hackathon already exists with start_date {start_date}")
        return hackathon
    else:
        logger.info("hackathon does not exist")
    
    hackathon = db.collection("hackathons").where("end_date", "==", end_date).get()
    if hackathon:
        logger.info(f"hackathon already exists with end_date {end_date}")
        return hackathon
    else:
        logger.info("hackathon does not exist")
    
    hackathon = db.collection("hackathons").where("title", "==", title).get()
    if hackathon:
        logger.info(f"hackathon already exists with title {title}")
        return hackathon
    else:
        logger.info("hackathon does not exist")
    


    hackathon = {
        "title": title,
        "type": type,
        "links": links,
        "teams": teams,
        "donation_current": donation_current,
        "donation_goals": donation_goals,
        "location": location,
        "nonprofits": nonprofits,
        "start_date": start_date,
        "end_date": end_date,
        "image_url": ""
    }
    logger.info(f"Adding hackathon {hackathon}")
    db.collection("hackathons").add(hackathon)
    return hackathon


def get_team_by_name(name):
    db = get_db()  # this connects to our Firestore database
    docs = db.collection('teams').where("name", "==", name).stream()

    for doc in docs:
        adict = doc.to_dict()
        adict["id"] = doc.id
        return adict

def add_hackathon_to_user_and_teams(hackathon_id):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding hackathon {hackathon_id} to user and teams")

    # Get hackathon
    hackathon = db.collection("hackathons").document(hackathon_id).get()

    if not hackathon.exists:
        logger.error(f"**ERROR Hackathon {hackathon_id} does not exist")
        raise Exception(f"Hackathon {hackathon_id} does not exist")

    
    # Get teams from hackathon   
    hackathon_teams = hackathon.to_dict()["teams"]

    # For each team, add hackathon to user
    for team in hackathon_teams:
        team_users = team.get().to_dict()["users"]
        for user in team_users:
            user_hackathons = user.get().to_dict()["hackathons"]
            if hackathon.reference in user_hackathons:
                logger.info(f"Hackathon {hackathon_id} is already in user {user.id}, not adding again")
            else:
                user_hackathons.append(hackathon.reference)
                db.collection("users").document(user.id).set({"hackathons": user_hackathons}, merge=True)


def add_reference_link_to_problem_statement(problem_statement_id, name, link):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding reference link {link} to problem statement {problem_statement_id}")

    # Get problem statement
    problem_statement = db.collection("problem_statements").document(problem_statement_id).get()

    if not problem_statement.exists:
        logger.error(f"**ERROR Problem statement {problem_statement_id} does not exist")
        raise Exception(f"Problem statement {problem_statement_id} does not exist")

    # Add reference link
    reference_links = problem_statement.to_dict()["references"]
    reference_links.append({"name": name, "link": link})
    db.collection("problem_statements").document(problem_statement_id).set(
        {"references": reference_links}, merge=True)
    


def get_user_by_user_id(user_id):
    SLACK_PREFIX = "oauth2|slack|T1Q7936BH-"
    slack_user_id = f"{SLACK_PREFIX}{user_id}"
    # log slack_user_id
    logger.info(f"Looking up user {slack_user_id}")
    
    db = get_db()  # this connects to our Firestore database
    docs = db.collection('users').where("user_id", "==", slack_user_id).stream()

    for doc in docs:
        adict = doc.to_dict()
        adict["id"] = doc.id
        return adict


def add_certificate(user_id, certificate):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding certificate {certificate} to user {user_id}")

    # Get history from user    
    user = db.collection("users").document(user_id).get()

    if not user.exists:
        logger.error(f"**ERROR User {user_id} does not exist")
        raise Exception(f"User {user_id} does not exist")

    # Set this as empty if it doesn't exist   
    user_history = {}    

    if "history" in user.to_dict():
        user_history = user.to_dict()["history"]
    
    # handle when certificate does not exist
    if "certificates" not in user_history:
        user_history["certificates"] = []

    user_history["certificates"].append(certificate)

    # Update user
    db.collection("users").document(user_id).set({"history": user_history}, merge=True)    
   

def add_hearts_for_user(user_id, hearts, reason):
    db = get_db()  # this connects to our Firestore database
    logger.info(f"Adding {hearts} hearts to user {user_id} for reason {reason}")

    # Get history from user    
    user = db.collection("users").document(user_id).get()

    if not user.exists:
        logger.error(f"**ERROR User {user_id} does not exist")
        raise Exception(f"User {user_id} does not exist")
    
    user_history = user.to_dict()["history"]
    
    # 4 things in "how"
    if "how" not in user_history:
        user_history["how"] = {}
    if "code_reliability" not in user_history["how"]:
        user_history["how"]["code_reliability"] = 0
    if "customer_driven_innovation_and_design_thinking" not in user_history["how"]:
        user_history["how"]["customer_driven_innovation_and_design_thinking"] = 0
    if "iterations_of_code_pushed_to_production" not in user_history["how"]:
        user_history["how"]["iterations_of_code_pushed_to_production"] = 0
    if "standups_completed" not in user_history["how"]:
        user_history["how"]["standups_completed"] = 0    
    # 8 things in "what"
    if "what" not in user_history:
        user_history["what"] = {}                                
    if "code_quality" not in user_history["what"]:
        user_history["what"]["code_quality"] = 0
    if "design_architecture" not in user_history["what"]:
        user_history["what"]["design_architecture"] = 0
    if "documentation" not in user_history["what"]:
        user_history["what"]["documentation"] = 0
    if "observability" not in user_history["what"]:
        user_history["what"]["observability"] = 0
    if "productionalized_projects" not in user_history["what"]:
        user_history["what"]["productionalized_projects"] = 0
    if "requirements_gathering" not in user_history["what"]:
        user_history["what"]["requirements_gathering"] = 0
    if "unit_test_coverage" not in user_history["what"]:
        user_history["what"]["unit_test_coverage"] = 0
    if "unit_test_writing" not in user_history["what"]:
        user_history["what"]["unit_test_writing"] = 0
        
        

    # TODO: We should be using enums instead of static strings
    #  Enums allow us to centralize our strings and make it easier to refactor
    
    # 4 things in "how"
    if reason == "code_reliability":
        user_history["how"]["code_reliability"] += hearts
    elif reason == "customer_driven_innovation_and_design_thinking":
        user_history["how"]["customer_driven_innovation_and_design_thinking"] += hearts
    elif reason == "iterations_of_code_pushed_to_production":
        user_history["how"]["iterations_of_code_pushed_to_production"] += hearts
    elif reason == "standups_completed":
        user_history["how"]["standups_completed"] += hearts
    # 8 things in "what"
    elif reason == "code_quality":
        user_history["what"]["code_quality"] += hearts
    elif reason == "design_architecture":
        user_history["what"]["design_architecture"] += hearts
    elif reason == "documentation":
        user_history["what"]["documentation"] += hearts
    elif reason == "observability":
        user_history["what"]["observability"] += hearts
    elif reason == "productionalized_projects":
        user_history["what"]["productionalized_projects"] += hearts
    elif reason == "requirements_gathering":
        user_history["what"]["requirements_gathering"] += hearts
    elif reason == "unit_test_coverage":
        user_history["what"]["unit_test_coverage"] += hearts
    elif reason == "unit_test_writing":
        user_history["what"]["unit_test_writing"] += hearts
    else:
        raise Exception(f"Invalid reason: {reason}")                

    # Update user history
    db.collection("users").document(user_id).set({"history": user_history}, merge=True)
    
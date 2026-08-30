"""A complete comsocwebapp application in a single file.

A faculty hiring committee shortlists candidates by approval voting.

Run it::

    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5010/ and log in as admin@example.com / admin.

Settings come from two places.  What is not secret -- the port, the database
path, the folders -- is the CONFIG dict below, and is committed.  What is
secret -- the session key, any OAuth client secrets, a database password --
goes in a .env file next to this one, which .gitignore keeps out of the
repository; copy example.env to .env to fill it in.
"""

import os
from comsocwebapp import adapters, auth, create_app, db, dummy, oauth, rules, poll


# --------------------------------------------------------------------------
# 1. Configuration -- how this application is set up
# --------------------------------------------------------------------------

# Load examples/.env (next to this file) into the environment, if it exists.
# The .env file holds the session key, the API keys and the database password
# -- things that should not be on GitHub.  Copy example.env to .env to add
# yours (see README, "Runnable examples").
import dotenv; dotenv.load_dotenv() 

HERE = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "PORT": 5010,  # Port for the development server.
    "LANGUAGE": "en", # The GUI language: one of comsocwebapp.i18n.available_languages().

    "DATABASE_ENGINE": "mariadb",  # or postgresql / sqlite / mysql

    # SQLite wants only a path, kept next to the code:
    # "DATABASE_FILE": os.path.join(HERE, "instance", "faculty_hiring.sqlite"),

    # For a server engine, replace the DATABASE_FILE line above with these four:
       "DATABASE_HOST": "localhost",
       "DATABASE_PORT": 3306,   # 5432 for postgresql, 3306 for mysql/mariadb
       "DATABASE_NAME": "faculty_hiring",
       "DATABASE_USER": "hiring_app",
    # and add DATABASE_PASSWORD in .env.

    "TEMPLATE_FOLDER": os.path.join(HERE, "templates"),
    # Whatever we do not provide falls back to the ones inside comsocwebapp.  
    # Set to None to use the package's templates only.
    
    "STATIC_FOLDER": os.path.join(HERE, "static"),
    # Our own CSS and images, served at /static.  
    # Set to None to use the package's.
}


# --------------------------------------------------------------------------
# 3. Committee voting rules
# --------------------------------------------------------------------------

# --- Register some rules from the abcvoting library ------------------------------------------
# To use these rules, install the library first:
#
#     pip install "comsocwebapp[voting] @ git+https://github.com/ariel-research/comsocwebapp"
#
# Without abcvoting installed these calls register nothing, so the dropdown
# never offers a rule this installation cannot run.

adapters.register_abcvoting_rule("pav")           # Proportional Approval Voting
adapters.register_abcvoting_rule("seqphragmen")   # sequential Phragmén
adapters.register_abcvoting_rule("cc")            # Chamberlin-Courant
adapters.register_abcvoting_rule("monroe")


# --- Register a custom rule ------------------------------------------

@rules.register_rule("shortlist_by_approval", formats=("approval",), poll_types=("committee",))
def shortlist_by_approval(poll_id, scope=adapters.SCOPE_ALL,
                          committee_size=None, **_):
    """Shortlist the most-approved candidates.

    A rule is any function returning a RuleResult.  Its ``log_lines`` are what
    the committee -- and every candidate -- can read afterwards, which is the
    whole point of running the process in the open.

    How many to shortlist comes from two places, and never from a constant in
    this file:

    * the **run**, when the admin types a size on the run form -- comsocwebapp
      passes it in, exactly as it does to the built-in rules.  Accept it, or
      the number the admin chose is silently ignored;
    * otherwise the **poll**, whose ``budget_limit`` is the committee size
      declared when it was created (that is what the column counts in a
      ``committee`` poll).

    So the rule keeps working after the size is edited in the GUI, and on any
    other committee poll -- exactly as the budgeting example reads its
    budget from the poll rather than from a module constant.
    """
    size = rules.committee_size_for(poll_id, committee_size)    
    names = {o["id"]: o["name"] for o in adapters.fetch_options(poll_id)}
    approvals = {oid: 0 for oid in names}
    for approved in adapters.approval_sets(poll_id, scope).values():
        for oid in approved:
            approvals[oid] += 1

    ranked = sorted(approvals.items(), key=lambda pair: (-pair[1], names[pair[0]]))
    shortlist = [oid for oid, _ in ranked[:size]]

    log = [f"Shortlisting the top {size} candidates by approvals.",
           "Approvals received:"]
    log += [f"  {names[oid]}: {count}" for oid, count in ranked]
    log.append("Shortlisted: " + ", ".join(names[oid] for oid in shortlist))
    return rules.RuleResult(outcome=shortlist, log_lines=log)




# --------------------------------------------------------------------------
# 4. Seeding -- runs once, on the first start
# --------------------------------------------------------------------------

def seed(app):
    """Create the database only if it does not exist yet.

    Restarting the app must never throw away ballots that were already cast.
    To start over, delete the file at CONFIG["DATABASE_FILE"] and run again.
    """
    with app.app_context():
        if not db.ensure_db():
            name = app.config.get("DATABASE_NAME") or app.config.get("DATABASE_FILE")
            print(f"Using the existing database at {name}.")
            return

        COMMITTEE_SIZE = 3
        CANDIDATES = [
            ("Dr. Adeyemi", "Algorithmic game theory; 12 papers, 3 in top venues", 0),
            ("Dr. Bianchi", "Machine learning for healthcare; strong teaching record", 0),
            ("Dr. Chen", "Distributed systems; brings an industry collaboration", 0),
            ("Dr. Duarte", "Formal verification; two funded grants", 0),
            ("Dr. Eriksen", "Human-computer interaction; runs a large lab", 0),
            ("Dr. Farouk", "Cryptography; best-paper award last year", 0),
        ]

        auth.create_user("admin@example.com", "admin", is_admin=True)
        poll_id = poll.create_poll(
            "Faculty hiring 2026",
            poll_type="committee",
            pref_format="approval",
            budget_limit=COMMITTEE_SIZE,
            status="open",
            options=CANDIDATES,
        )
        # A few simulated committee members, so there is something to look at.
        dummy.generate_dummy_users(poll_id, 7, approval_rate=0.45, seed=11)
        token = auth.create_invitation(poll_id, is_generic=True)

        print("Admin login: admin@example.com / admin")
        print(f"Committee invitation:"
              f" http://127.0.0.1:{app.config['PORT']}/auth/invite/{token}")


def build_app():
    """Application factory -- also usable as `flask --app app:build_app run`."""
    # return create_app(CONFIG, instance_path=os.path.dirname(CONFIG["DATABASE_FILE"]))
    return create_app(CONFIG)


app = build_app()
seed(app)

if __name__ == "__main__":
    port = app.config["PORT"]
    for label, uri in oauth.redirect_uris(f"http://127.0.0.1:{port}", app):
        print(f"Register this redirect URI in the {label} console: {uri}")
    app.run(port=port, debug=True)

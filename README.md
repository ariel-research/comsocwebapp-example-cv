# comsocwebapp-example-cv - Faculty hiring — a standalone `comsocwebapp` application

A hiring committee shortlists candidates by approval voting. Every committee
member approves the candidates they consider hirable; the three most-approved
are shortlisted, and everyone can read exactly how that was computed.

This folder is self-contained. Copy it into a repository of your own, rename
things, and it keeps working — it depends only on `comsocwebapp` and on nothing
else in this repository.

## Install and run

Requires **Python 3.10+**.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip           # avoid "project name unknown" with older pip

# comsocwebapp is not on PyPI yet, so install it straight from GitHub:
pip install --upgrade "comsocwebapp @ git+https://github.com/ariel-research/comsocwebapp"


python app.py
```

Open <http://127.0.0.1:5010/>, and log in as `admin@example.com` / `admin`.
The console also prints an invitation link — open it in a private window to see
what a voter sees.

That is the whole installation. There is no database server to set up: the app
creates an SQLite file under `instance/` on first run.

## Secrets: the `.env` file

Settings come from two places, and the split matters once this folder is on
GitHub:

* **Not secret** — the port, the database path, the template and static folders
  — is the `CONFIG` dict in `app.py`, and is committed.
* **Secret** — the session key, any OAuth client secrets, a database password —
  is a `.env` file next to `app.py`, which `.gitignore` keeps out of the
  repository. `app.py` reads it with `load_dotenv()` on start-up.

`example.env` is the committed template, with every line commented out. Copy it
and fill in what you need:

```bash
cp example.env .env          # Windows: copy example.env .env
```

Nothing in it is required to run locally: a missing `.env`, or a line left
commented, simply changes nothing. The one line to set before this is reachable
from anywhere but your own machine is the session key:

```dotenv
COMSOCWEBAPP_SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
```

Without it the app falls back to the development key `"dev"`, and anyone who
knows that — it is in the package source — can forge a session cookie,
including an administrator's.

## What is in here

```
app.py               the entire application: config, candidates, rule, seeding
example.env          template for .env -- committed, every line commented out
.env                 your secrets; git-ignored, created by you (see below)
.gitignore           keeps .env and the database out of version control
templates/
└── participant/
    └── index.html   one page replaced; every other page comes from the package
static/
└── style.css        this application's own styling
instance/            created on first run; holds the SQLite database
```

`app.py` is organised in the four steps you will edit:

1. **Configuration** — `PORT`, the database path, and the template/static
   folders. Not the secrets: those live in `.env`.
2. **The problem** — the list of candidates. Swap in projects with costs for
   participatory budgeting, or items for a fair division.
3. **A rule of our own** — `@rules.register_rule` makes it appear in the
   admin's dropdown. Delete it and use the built-in rules if you prefer. The
   same step also shows how to expose extra rules from `abcvoting` without
   touching the package.
4. **Seeding** — `db.ensure_db()` creates the schema only when it is missing,
   so restarting never destroys collected ballots.

## Making it yours

* **Different problem?** Change `pref_format` in the `create_poll(...)` call
  to `ranking`, `points` or `budget`, and give the options a `cost` if they
  have one.
* **Different look?** Every template in `comsocwebapp/templates/` can be
  overridden by putting a file with the same path under `templates/` here.
  This app overrides `participant/index.html`; everything else falls back to
  the package.
* **Real solver libraries?**
  `pip install "comsocwebapp[all] @ git+https://github.com/ariel-research/comsocwebapp"`
  installs `fairpyx`, `abcvoting` and `pabutools`. Installing them adds no
  rules by itself: the package registers none, and this app asks for the four
  it wants at the end of step 3 — PAV, seq-Phragmén, Chamberlin–Courant and
  Monroe.
* **More rules than that?** One line each.
  `adapters.register_abcvoting_rule` takes any id from
  `abcvoting.abcrules.MAIN_RULE_IDS`:

  ```python
  adapters.register_abcvoting_rule("equal-shares")
  ```

  The committee size is not part of the registration: the admin picks it on
  the run form each time, so one line covers every size.
  `register_pabutools_rule` and `register_fairpyx_rule` are the equivalents for
  budgeting and allocation.
* **Sign-in with Google / GitHub / ORCID?**
  `pip install "comsocwebapp[oauth] @ git+https://github.com/ariel-research/comsocwebapp"`,
  then uncomment that provider's two lines in `.env` — for example
  `OAUTH_GITHUB_CLIENT_ID` and `OAUTH_GITHUB_CLIENT_SECRET`. The buttons appear
  by themselves, and `app.py` prints the redirect URI to register in the
  provider's console. Client secrets belong in `.env`, never in `app.py`.

## Starting over

Delete the database and re-run:

```bash
rm -rf instance/            # Windows: rmdir /s /q instance
python app.py
```

## Deploying

Put a real session key in `.env` (see [Secrets](#secrets-the-env-file)), then
run behind a WSGI server:

```bash
pip install gunicorn
gunicorn "app:build_app()" --bind 0.0.0.0:8000 --workers 4
```

`app.py` loads `.env` by absolute path, so this works from any directory. If
your platform injects configuration as real environment variables instead —
most PaaS do — set `COMSOCWEBAPP_SECRET_KEY` there and skip the file; the app
reads the same variable either way.

Serve it over HTTPS: invitation tokens and session cookies travel in the
request.

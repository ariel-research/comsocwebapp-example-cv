#!/usr/bin/env bash
# Installation script for comsocwebapp.
#
# Generated on 2026-09-01 by comsocwebapp from this application's
# own configuration:
#
#     engine     mysql
#     location   mysql://hiring_app@localhost:3306/faculty_hiring
#     packages   comsocwebapp[mysql,voting]
#
# The configuration was read, not connected to, so this file is accurate only
# for the configuration above. Regenerate it whenever that changes:
#
#     flask install-script
#
# No password appears anywhere in this file. Steps that need one read
# $DATABASE_PASSWORD from the environment when they run.

# Stop at the first failure; an unset variable is a failure too.
set -euo pipefail

# ------------------------------------------------------------------------
# Step 1/5: Python packages
# Run this inside the virtual environment the application will use.
#   [mysql] PyMySQL, the MySQL/MariaDB driver
#   [voting] abcvoting, for the committee rules this app registers
# ------------------------------------------------------------------------
echo "==> Step 1/5: Python packages"
pip install "comsocwebapp[mysql,voting]"

# ------------------------------------------------------------------------
# Step 2/5: Database and user (needs the MySQL root account)
# The application's own account cannot create itself, so this step runs
# as root. If that is not you, this is the part to send to whoever
# administers the server.
#
# Reaching root differs by platform:
#   macOS/Homebrew:  mysql -u root
#   Windows:         mysql -u root -p
#
# utf8mb4 is set at CREATE DATABASE time because tables inherit the
# database's charset; the older utf8 cannot hold every character an
# option name may contain.
# ------------------------------------------------------------------------
echo "==> Step 2/5: Database and user (needs the MySQL root account)"
: "${DATABASE_PASSWORD:?set it, or source your .env, before running}"
# Escape the password for a MySQL string literal: backslash first,
# then the quote, so the doubling is not itself doubled.
pw=${DATABASE_PASSWORD//\\/\\\\}
pw=${pw//\'/\'\'}
sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS faculty_hiring
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'hiring_app'@'localhost' IDENTIFIED BY '${pw}';
GRANT ALL PRIVILEGES ON faculty_hiring.* TO 'hiring_app'@'localhost';
SQL

# ------------------------------------------------------------------------
# Step 3/5: Tables
# --if-missing keeps an existing event's data. Drop the flag to
# rebuild the six tables from scratch, erasing every ballot.
# ------------------------------------------------------------------------
echo "==> Step 3/5: Tables"
flask init-db --if-missing

# ------------------------------------------------------------------------
# Step 4/5: First administrator
# Prompts for an email address and a password. Everyone else can
# be invited from the dashboard afterwards.
# ------------------------------------------------------------------------
echo "==> Step 4/5: First administrator"
flask create-admin

# ------------------------------------------------------------------------
# Step 5/5: Check
# Prints the engine, the driver and the location -- never the
# password -- so the output is safe to paste into a bug report.
# ------------------------------------------------------------------------
echo "==> Step 5/5: Check"
flask db-info

echo "comsocwebapp is installed."

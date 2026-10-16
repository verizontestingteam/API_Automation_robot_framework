*** Settings ***

# Credentials come from .env (or real environment variables)
Variables    credentials.py


*** Variables ***

# IAM Configuration
${IAM_BASE_URL}        https://ttvz-sb-iam.tecnotree.com
${TOKEN_ENDPOINT}      /oauth2/token

# OAuth Configuration
${GRANT_TYPE}          password
${SCOPE}               openid

# Fetch a new token once the cached one is older than this (tokens usually last 1 hour)
${TOKEN_MAX_AGE_SECONDS}    3000

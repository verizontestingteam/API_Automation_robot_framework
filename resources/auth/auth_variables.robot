*** Variables ***

# IAM Configuration
${IAM_BASE_URL}        https://ttvz-sb-iam.tecnotree.com
${TOKEN_ENDPOINT}      /oauth2/token

# OAuth Credentials
# Values come from environment variables, loaded from the local .env file by the runner scripts.
${CLIENT_ID}           %{CLIENT_ID=}
${CLIENT_SECRET}       %{CLIENT_SECRET=}

# User Credentials
${USERNAME}            %{API_USERNAME=}
${PASSWORD}            %{API_PASSWORD=}

# OAuth Configuration
${GRANT_TYPE}          password
${SCOPE}               openid
*** Variables ***

# IAM Configuration
${IAM_BASE_URL}        https://ttvz-sb-iam.tecnotree.com
${TOKEN_ENDPOINT}      /oauth2/token

# OAuth Credentials
${CLIENT_ID}           %{CLIENT_ID}
${CLIENT_SECRET}       %{CLIENT_SECRET}

# User Credentials
${USERNAME}            %{API_USERNAME}
${PASSWORD}            %{API_PASSWORD}

# OAuth Configuration
${GRANT_TYPE}          password
${SCOPE}               openid

# Cookie
${IAM_COOKIE}          YOUR_COOKIE_VALUE
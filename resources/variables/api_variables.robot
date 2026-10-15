*** Variables ***

# Token API
${IAM_BASE_URL}          https://ttvz-sb-iam.tecnotree.com
${TOKEN_ENDPOINT}        /oauth2/token

# Product Offering API
${BASE_URL}              https://ttvz-sb-app.tecnotree.com
${PRODUCT_ENDPOINT}      /dcm/product-catalogue/v1/product-offering
${TODO_ENDPOINT}         /todos/1
${CSV_FILE}              ${CURDIR}/../../testdata/api/product_offering.csv
${AUTH_TOKEN}            sample_access_token

# Compatibility Check API
${COMPATIBILITY_ENDPOINT}    /ve-api/api/3PP/v1/compatibility-check
${COMPATIBILITY_CSV_FILE}    ${CURDIR}/../../testdata/api/compatibility_check.csv
${JSON_CONTENT_TYPE}         application/json

# ============================================================
# Authentication
# ============================================================

# OAuth access token is obtained dynamically by Get Access Token.
# Do NOT put the bearer token here.

${AUTH_TOKEN}                sample_access_token

# Valid SSO cookie required by Compatibility API.
# Replace this with a valid value from a working request.
${COMPATIBILITY_COOKIE}      YOUR_VALID_SSO_COOKIE

*** Variables ***

# Product Offering API
${BASE_URL}                  https://ttvz-sb-app.tecnotree.com
${PRODUCT_ENDPOINT}          /dcm/product-catalogue/v1/product-offering

# Compatibility Check API
${COMPATIBILITY_ENDPOINT}    /ve-api/api/3PP/v1/compatibility-check
${JSON_CONTENT_TYPE}         application/json

# IAM URL and credentials live in resources/auth/auth_variables.robot.
# The Compatibility Check SSO cookie is read from the COMPATIBILITY_COOKIE environment variable (.env).

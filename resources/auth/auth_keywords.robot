*** Settings ***

Library    RequestsLibrary
Library    Collections
Library    OperatingSystem

Resource    auth_variables.robot


*** Keywords ***

Disable Proxy For API Requests
    Remove Environment Variable    HTTP_PROXY
    Remove Environment Variable    HTTPS_PROXY
    Remove Environment Variable    ALL_PROXY

Get Access Token
    Should Not Be Empty    ${CLIENT_ID}        CLIENT_ID environment variable is not set. Add it to .env.
    Should Not Be Empty    ${CLIENT_SECRET}    CLIENT_SECRET environment variable is not set. Add it to .env.
    Should Not Be Empty    ${USERNAME}         API_USERNAME environment variable is not set. Add it to .env.
    Should Not Be Empty    ${PASSWORD}         API_PASSWORD environment variable is not set. Add it to .env.

    Disable Proxy For API Requests

    &{headers}=    Create Dictionary
    ...    Content-Type=application/x-www-form-urlencoded

    &{form_data}=    Create Dictionary
    ...    client_id=${CLIENT_ID}
    ...    client_secret=${CLIENT_SECRET}
    ...    grant_type=${GRANT_TYPE}
    ...    username=${USERNAME}
    ...    password=${PASSWORD}
    ...    scope=${SCOPE}

    Create Session
    ...    iam
    ...    ${IAM_BASE_URL}
    ...    headers=${headers}
    ...    verify=True

    ${response}=    POST On Session
    ...    iam
    ...    ${TOKEN_ENDPOINT}
    ...    data=${form_data}
    ...    expected_status=200

    ${body}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${body}    access_token

    ${token}=    Set Variable    ${body}[access_token]
    Should Not Be Empty    ${token}
    RETURN    ${token}

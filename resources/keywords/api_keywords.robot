*** Settings ***

Library    RequestsLibrary
Library    Collections
Library    OperatingSystem

Resource    ../variables/api_variables.robot
Resource    ../auth/auth_keywords.robot


*** Keywords ***

Create API Session
    Disable Proxy For API Requests

    Create Session
    ...    api
    ...    ${BASE_URL}
    ...    verify=True

Get Product Offering

    [Arguments]    ${related_party}    ${depth}    ${code}    ${category_name}=${EMPTY}    ${request_fields}=${EMPTY}    ${channel_name}=${EMPTY}

    Disable Proxy For API Requests

    ${token}=    Get Access Token
    ${authorization}=    Set Variable    Bearer ${token}

    &{headers}=    Create Dictionary
    ...    Cache-Control=no-store
    ...    Authorization=Bearer ${token}


    &{params}=    Create Dictionary
    ...    relatedParty.name=${related_party}
    ...    depth=${depth}
    ...    code=${code}

    Run Keyword If    '${category_name}' != ''
    ...    Set To Dictionary
    ...    ${params}
    ...    category.name=${category_name}

    Run Keyword If    '${request_fields}' != ''
    ...    Set To Dictionary
    ...    ${params}
    ...    fields=${request_fields}

    Run Keyword If    '${channel_name}' != ''
    ...    Set To Dictionary
    ...    ${params}
    ...    channel.name=${channel_name}

    Create Session
    ...    api
    ...    ${BASE_URL}
    ...    headers=${headers}
    ...    verify=True

    ${response}=    GET On Session
    ...    api
    ...    ${PRODUCT_ENDPOINT}
    ...    params=${params}
    ...    expected_status=any

    RETURN    ${response}

Get Todo
    Create API Session

    ${response}=    GET On Session
    ...    api
    ...    ${TODO_ENDPOINT}
    ...    expected_status=200

    RETURN    ${response}

Compatibility Check
    [Arguments]    ${correlation_group}    ${skus}    ${channel_name}    ${brand}

    Disable Proxy For API Requests

    ${token}=    Get Access Token
    ${authorization}=    Set Variable    Bearer ${token}

    &{headers}=    Create Dictionary
    ...    Content-Type=${JSON_CONTENT_TYPE}
    ...    Authorization=Bearer ${token}


    ${cookie}=    Get Environment Variable    COMPATIBILITY_COOKIE    ${EMPTY}
    Run Keyword If    '${cookie}' != ''    Set To Dictionary    ${headers}    Cookie=${cookie}

    &{channel}=    Create Dictionary    name=${channel_name}
    &{cart_item}=    Create Dictionary
    ...    correlationGroup=${correlation_group}
    ...    skus=${skus}
    @{cart_items}=    Create List    ${cart_item}

    &{payload}=    Create Dictionary
    ...    cartItem=${cart_items}
    ...    channel=${channel}
    ...    brand=${brand}

    Create Session
    ...    compatibility_api
    ...    ${BASE_URL}
    ...    headers=${headers}
    ...    verify=True

    ${response}=    POST On Session
    ...    compatibility_api
    ...    ${COMPATIBILITY_ENDPOINT}
    ...    json=${payload}
    ...    expected_status=any

    RETURN    ${response}

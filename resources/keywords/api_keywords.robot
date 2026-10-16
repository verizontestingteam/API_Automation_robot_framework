*** Settings ***

Library    RequestsLibrary
Library    Collections
Library    OperatingSystem

Resource    ../variables/api_variables.robot
Resource    ../auth/auth_keywords.robot


*** Keywords ***

Get Product Offering

    [Arguments]    ${related_party}    ${depth}    ${code}    ${category_name}=${EMPTY}    ${request_fields}=${EMPTY}    ${channel_name}=${EMPTY}    ${extra_params}=${None}

    Disable Proxy For API Requests

    ${token}=    Get Cached Access Token

    &{headers}=    Create Dictionary
    ...    Cache-Control=no-store
    ...    Authorization=Bearer ${token}


    &{params}=    Create Dictionary
    ...    relatedParty.name=${related_party}
    ...    depth=${depth}
    ...    code=${code}

    IF    '${category_name}' != ''
        Set To Dictionary    ${params}    category.name=${category_name}
    END

    IF    '${request_fields}' != ''
        Set To Dictionary    ${params}    fields=${request_fields}
    END

    IF    '${channel_name}' != ''
        Set To Dictionary    ${params}    channel.name=${channel_name}
    END

    IF    $extra_params
        ${clashes}=    Evaluate    sorted(set($params) & set($extra_params))
        Should Be Empty    ${clashes}    CSV columns ${clashes} clash with built-in query parameters.
        Set To Dictionary    ${params}    &{extra_params}
    END

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

Compatibility Check
    [Arguments]    ${correlation_group}    ${skus}    ${channel_name}    ${brand}

    Disable Proxy For API Requests

    ${token}=    Get Cached Access Token

    &{headers}=    Create Dictionary
    ...    Content-Type=${JSON_CONTENT_TYPE}
    ...    Authorization=Bearer ${token}


    ${cookie}=    Get Environment Variable    COMPATIBILITY_COOKIE    ${EMPTY}
    IF    '${cookie}' != ''
        Set To Dictionary    ${headers}    Cookie=${cookie}
    END

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

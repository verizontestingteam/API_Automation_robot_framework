*** Settings ***

Library    DataDriver    file=${CURDIR}/../../testdata/api/product_offering.csv    dialect=excel    encoding=utf_8_sig
Library    ../../python/api_custom_validations.py

Resource    ../../resources/keywords/api_keywords.robot
Resource    ../../resources/variables/api_variables.robot

Test Template    Validate Channel Based Product Offering


*** Test Cases ***

Product Offering ${code} ${channel_name}    Default    Default    Default    Default    Default


*** Keywords ***

Validate Channel Based Product Offering
    [Arguments]    ${related_party}    ${depth}    ${code}    ${category_name}    ${channel_name}

    Log    Testing code=${code}, relatedParty=${related_party}, depth=${depth}, category=${category_name}, channel=${channel_name}

    ${response}=    api_keywords.Get Product Offering
    ...    ${related_party}
    ...    ${depth}
    ...    ${code}
    ...    ${category_name}
    ...    ${EMPTY}
    ...    ${channel_name}

    ${body_text}=    Set Variable    ${response.text}
    ${body_length}=    Get Length    ${body_text}

    Log    Request Summary: code=${code}, relatedParty=${related_party}, depth=${depth}, category=${category_name}, status=${response.status_code}, bodyLength=${body_length}
    Log    Status Code: ${response.status_code}
    Log    Response Body: ${body_text}

    # Gate: stop here if the response is not usable
    Validate Response Status    ${response}    200
    Validate Response Not Empty    ${response}
    Validate Response Headers    ${response}    Content-Type    application/json

    Validate Product Offering Content    ${response}    ${related_party}    ${code}    ${category_name}    ${channel_name}

Validate Product Offering Content
    [Arguments]    ${response}    ${related_party}    ${code}    ${category_name}    ${channel_name}
    [Tags]    robot:continue-on-failure
    Validate Response Time    ${response}    5000
    ${channel_summary}=    Validate Requested Product Offering Channels    ${response}    ${channel_name}
    Log    ${channel_summary}
    Validate Product Offering Schema    ${response}
    Validate Product Offering Prices    ${response}    expected_channel=${channel_name}
    Validate Product Offering Validity    ${response}
    Validate Product Offering Response
    ...    ${response}
    ...    related_party=${related_party}
    ...    code=${code}
    ...    category_name=${category_name}

*** Settings ***

Library    Collections
Library    ../../python/csv_reader.py
Library    ../../python/api_custom_validations.py

Resource    ../../resources/keywords/api_keywords.robot
Resource    ../../resources/variables/api_variables.robot


*** Test Cases ***

Get Product Offering From CSV

    ${rows}=    Read Csv    ${CSV_FILE}
    ${failures}=    Create List

    FOR    ${row}    IN    @{rows}

        ${related_party}=    Get From Dictionary    ${row}    relatedParty
        ${depth}=    Get From Dictionary    ${row}    depth
        ${code}=    Get From Dictionary    ${row}    code
        ${category_name}=    Get From Dictionary    ${row}    category.name
        ${channel_name}=    Get From Dictionary    ${row}    channel.name

        Log    Testing Code: ${code}
        Log    Related Party: ${related_party}
        Log    Depth: ${depth}
        Log    Category Name: ${category_name}
        Log    Channel Name: ${channel_name}

        TRY
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

            Validate Response Status    ${response}    200
            Validate Response Not Empty    ${response}
            Validate Response Time    ${response}    5000
            Validate Response Headers    ${response}    Content-Type    application/json
            Validate Requested Product Offering Channels    ${response}    ${channel_name}
            Validate Root Offering Channels    ${response}    ${channel_name}
            Validate Product Offering Schema    ${response}
            Validate Product Offering Prices    ${response}    expected_channel=${channel_name}
            Validate Product Offering Validity    ${response}
            Validate Product Offering Response
            ...    ${response}
            ...    related_party=${related_party}
            ...    code=${code}
            ...    category_name=${category_name}
            ...    channel_name=${channel_name}
            ${bundle_channel_result}=    Validate Bundled Product Offering Channels
            ...    ${response}
            ...    ${channel_name}
            Log    ${bundle_channel_result}[message]
        EXCEPT    AS    ${error}
            Log    Product offering test failed for code=${code}, relatedParty=${related_party}, category=${category_name}. Error: ${error}    ERROR
            Append To List
            ...    ${failures}
            ...    code=${code}, channel=${channel_name}: ${error}
        END

    END

    ${failure_count}=    Get Length    ${failures}
    IF    ${failure_count} > 0
        ${failure_details}=    Catenate    SEPARATOR=\n    @{failures}
        Fail    ${failure_count} product offering row(s) failed:\n${failure_details}
    END

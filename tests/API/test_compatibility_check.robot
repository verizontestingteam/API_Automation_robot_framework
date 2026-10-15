*** Settings ***

Library    DataDriver    file=${CURDIR}/../../testdata/api/compatibility_check.csv    dialect=excel    encoding=utf_8_sig
Library    ../../python/api_custom_validations.py

Resource    ../../resources/keywords/api_keywords.robot
Resource    ../../resources/variables/api_variables.robot

Test Template    Verify Compatibility Check


*** Test Cases ***

Compatibility Check ${correlation_group}    Default    Default    Default    Default


*** Keywords ***

Verify Compatibility Check
    [Arguments]    ${correlation_group}    ${skus}    ${channel_name}    ${brand}

    @{sku_list}=    Evaluate    [item.strip() for item in '${skus}'.split(',')]

    ${compatibility}=    Set Variable    ${False}

    FOR    ${attempt}    IN RANGE    3

        ${response}=    Compatibility Check
        ...    ${correlation_group}
        ...    ${sku_list}
        ...    ${channel_name}
        ...    ${brand}

        Log    Compatibility attempt ${attempt + 1} status: ${response.status_code}
        Log    Compatibility attempt ${attempt + 1} body: ${response.text}

        Validate Response Status    ${response}    200
        Validate Response Not Empty    ${response}
        Validate Compatibility Check Response
        ...    ${response}
        ...    correlation_group=${correlation_group}
        ...    skus=${sku_list}

        ${compatibility}=    Get Compatibility Result    ${response}
        IF    ${compatibility}
            BREAK
        END

        Log    Compatibility returned false on attempt ${attempt + 1}; retrying.    WARN

    END

    IF    not ${compatibility}
        Log    Compatibility remained false after 3 attempts. Final response: ${response.text}    ERROR
        Fail    Compatibility check failed after 2 retries for ${correlation_group}.
    END

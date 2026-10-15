*** Settings ***

Library    Collections
Library    ../../python/csv_reader.py
Library    ../../python/api_custom_validations.py

Resource    ../../resources/keywords/api_keywords.robot
Resource    ../../resources/variables/api_variables.robot


*** Test Cases ***

Compatibility Check From CSV

    ${rows}=    Read Csv    ${COMPATIBILITY_CSV_FILE}
    ${failures}=    Create List

    FOR    ${row}    IN    @{rows}

        ${correlation_group}=    Get From Dictionary    ${row}    correlationGroup
        ${skus_value}=    Get From Dictionary    ${row}    skus
        ${channel_name}=    Get From Dictionary    ${row}    channel.name
        ${brand}=    Get From Dictionary    ${row}    brand

        @{skus}=    Evaluate    [item.strip() for item in '${skus_value}'.split(',')]

        TRY
            ${compatibility}=    Set Variable    ${False}

            FOR    ${attempt}    IN RANGE    3

                ${response}=    Compatibility Check
                ...    ${correlation_group}
                ...    ${skus}
                ...    ${channel_name}
                ...    ${brand}

                Log    Compatibility attempt ${attempt + 1} status: ${response.status_code}
                Log    Compatibility attempt ${attempt + 1} body: ${response.text}

                Validate Response Status    ${response}    200
                Validate Response Not Empty    ${response}
                Validate Compatibility Check Response
                ...    ${response}
                ...    correlation_group=${correlation_group}
                ...    skus=${skus}

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
        EXCEPT    AS    ${error}
            Log    Compatibility check failed for correlationGroup=${correlation_group}, skus=${skus_value}, channel=${channel_name}. Error: ${error}    ERROR
            Append To List
            ...    ${failures}
            ...    correlationGroup=${correlation_group}, skus=${skus_value}, channel=${channel_name}: ${error}
        END

    END

    ${failure_count}=    Get Length    ${failures}
    IF    ${failure_count} > 0
        ${failure_details}=    Catenate    SEPARATOR=\n    @{failures}
        Fail    ${failure_count} compatibility row(s) failed:\n${failure_details}
    END

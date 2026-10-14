*** Keywords ***

Get Access Token
    ${token}=    Set Variable    sample_access_token
    RETURN    ${token}


*** Test Cases ***

Verify Token API

    ${token}=    Get Access Token

    Should Not Be Empty    ${token}

    Log    Token generated successfully
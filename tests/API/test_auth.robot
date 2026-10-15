*** Settings ***

Resource    ../../resources/auth/auth_keywords.robot


*** Test Cases ***

Verify Token API

    ${token}=    Get Access Token

    Should Not Be Empty    ${token}

    Log    Token generated successfully

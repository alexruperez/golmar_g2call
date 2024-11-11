# Golmar G2Call+ Home Assistant Integration

**This project is currently non-functional. Help is needed to resolve integration issues.**

## Issue Description
This integration was designed to control a Golmar G2Call+ intercom in Home Assistant, enabling features like door control and automatic session management. However, it is currently non-functional due to an authentication problem with the server.

### Detailed Authentication Issue
The integration uses a two-step authentication flow:
1. **First Request (`auth/user;jus_duplex=down`)**: Sends an initial request to obtain a `jsessionid`.
2. **Second Request (`auth/user;jus_duplex=up`)**: Uses the `jsessionid` and sends an XML-formatted login request.

**Primary Error**:
- In the second request, the server inconsistently responds with an empty `application/octet-stream` response.
- This results in a retry loop that eventually leads to a `TimeoutError`, preventing successful authentication and access to the device’s features.

**Technical Details of the Error**:
- **Error Messages**:
  - "Retrying login due to empty binary response."
  - "Error in async_login: asyncio.exceptions.CancelledError"
  - "TimeoutError: Login failed after max retries due to empty binary response."
  
It’s suspected that the server may require specific parameters, headers, or timing adjustments that have not yet been identified.

## Assistance Needed
If you have experience with IoT device integrations, REST/XML server authentication, or specific knowledge of Golmar devices, any help in resolving this issue would be greatly appreciated. Suggestions or contributions to adjust this integration and solve the authentication issues are welcome.

## Installation
This integration is currently non-functional. For those interested in exploring and contributing to development:

1. Clone this repository into the `custom_components` folder in your Home Assistant setup.
2. Restart Home Assistant.
3. Add the `Golmar G2Call+` integration from the Integrations section.

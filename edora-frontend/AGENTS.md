# Developer Agent Instructions

## Architecture & API Flow
- **Strict API Routing:** The frontend must **always** call the internal API first.
- **Internal Proxy Pattern:** The internal API must handle forwarding requests to the backend API.
- **No Direct Backend Calls:** Never call the backend API directly from the frontend under any circumstances.
- **Frontend Alignment:** Ensure all frontend logic, state management, and integration patterns remain strictly aligned with the internal API flow.

## Code Quality & Standards
- Always follow established coding best practices, including clean architecture, proper error handling, type safety, and modular design.

## Response Formatting Rules
- **Backend Changes Last:** Always place any backend-related changes or instructions at the very end of your response. This includes:
  - API endpoint or contract changes
  - New database table generation
  - Table schema or structure modifications
  - Any other backend-related implementation updates

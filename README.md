# Speech Improvement Backend

This project is the backend for a Speech Improvement application, designed to help users enhance their public speaking and pronunciation skills. It provides a RESTful API to handle user authentication, audio recording submissions, speech-to-text transcription, and in-depth analysis of spoken content.

## Features

- **User Authentication:** Secure user management via Supabase, with JWT-based authentication for protected endpoints.
- **Full User Account Management:** Allows users to retrieve their profile, update their details, and delete their account.
- **Audio Submission:** Users can upload audio files (e.g., MP3, WAV, M4A) for analysis.
- **Speech-to-Text:** Integrates with AssemblyAI to provide fast and accurate transcriptions of user audio.
- **Comprehensive Speech Analysis:**
    - **Fluency:** Measures Words Per Minute (WPM) and detects significant pauses.
    - **Pronunciation:** Calculates Word Error Rate (WER) against a given prompt to score accuracy.
    - **Filler Words:** Identifies and quantifies the usage of common filler words (e.g., "um", "like", "you know").
    - **Pacing:** Analyzes the consistency of the user's speaking rate over time.
- **Database Integration:** Stores user data, prompts, recordings, and analysis results in a PostgreSQL database.
- **Database Migrations:** Uses Alembic to manage database schema changes.
- **Cloud Storage:** Securely stores audio recordings using Supabase Storage.

## API Endpoints

Here are the primary endpoints available:

| Method  | Endpoint                         | Description                                                                                                                                |
| :------ | :------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`   | `/`                              | Root endpoint with a welcome message.                                                                                                      |
| `GET`   | `/health-check`                  | Checks the API and database connection status.                                                                                             |
| `GET`   | `/users/me`                      | Retrieves the profile of the currently authenticated user. (Protected)                                                                     |
| `PATCH` | `/users/me`                      | Updates the details of the currently authenticated user. (Protected)                                                                       |
| `DELETE`| `/users/me`                      | Deletes the account of the currently authenticated user and all associated data. (Protected)                                               |
| `POST`  | `/recordings/submit-and-analyze` | Submits an audio file and a text prompt for transcription and full analysis. Returns the complete analysis. (Protected)                      |

## Authentication Flow

This backend uses a token-based authentication system powered by Supabase. The frontend client is responsible for the initial steps of user sign-up and sign-in.

### 1. Frontend: Acquiring Tokens

To authenticate, the frontend application must handle user registration and login directly with Supabase using a client-side library (e.g., `supabase-js`).

-   **Sign-Up/Sign-In:** The user provides their email and password.
-   **Receive Tokens:** Upon successful authentication, Supabase returns a session object containing two key items:
    -   `access_token`: A short-lived JSON Web Token (JWT).
    -   `refresh_token`: A long-lived token used to get a new `access_token`.

### 2. Frontend: Making Authenticated Requests

To access protected endpoints on this backend, the frontend must include the `access_token` in the `Authorization` header of each request, using the **Bearer** scheme.

**Example:**
```
Authorization: Bearer <your_supabase_access_token>
```

### 3. Backend: Validating Users

When a request with an `Authorization` header is received, the backend:
1.  Extracts the JWT (`access_token`).
2.  Verifies the token's validity with Supabase.
3.  If the token is valid, it retrieves the associated user's profile.
4.  **First-Time Login:** If the user exists in Supabase but not in the application's database, a new user profile is automatically created.

### 4. Security and User Experience: Managing Tokens

For a seamless and secure user experience, the frontend should implement the following token management strategy:

-   **Access Token (`access_token`)**:
    -   **Purpose:** Grants access to protected API resources.
    -   **Security:** It is short-lived (e.g., 1 hour) to minimize the risk of stolen tokens. Because it expires quickly, it should be stored in a location accessible to your frontend code, such as in-memory or browser local storage.
-   **Refresh Token (`refresh_token`)**:
    -   **Purpose:** Silently obtains a new `access_token` when the current one expires, without requiring the user to log in again.
    -   **Security:** It is long-lived and more sensitive. It should be stored securely, ideally in an **HttpOnly cookie** to prevent access from client-side scripts and mitigate XSS attacks.

#### Recommended Flow:

1.  **Login:** User signs in. The frontend stores the `access_token` in memory and the `refresh_token` in a secure HttpOnly cookie.
2.  **API Calls:** The frontend attaches the `access_token` to all API requests.
3.  **Token Expiration:** When an API call fails with a `401 Unauthorized` error, it signals that the `access_token` has likely expired.
4.  **Silent Refresh:** The frontend makes a request to the Supabase `/token` endpoint (using the `refresh_token`) to get a new `access_token`.
5.  **Retry Request:** Once the new token is received, the frontend automatically retries the original API request that failed.
6.  **Logout:** If the refresh token is also invalid or has expired, the user is logged out and must sign in again.

This approach ensures that the user stays logged in for an extended period while maintaining a high level of security.

## Technologies Used

- **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** [PostgreSQL](https://www.postgresql.org/)
- **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
- **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Authentication:** [Supabase](https://supabase.io/)
- **Speech-to-Text:** [AssemblyAI](https://www.assemblyai.com/)
- **Data Validation:** [Pydantic](https://pydantic-docs.helpmanual.io/)
- **Asynchronous Server:** [Uvicorn](https://www.uvicorn.org/)

## Project Structure

The project follows a standard FastAPI application structure:

```
.
├── alembic/              # Alembic migration scripts
├── .env                  # Environment variables (not committed)
├── alembic.ini           # Alembic configuration
├── main.py               # FastAPI app definition and main routes
├── requirements.txt      # Python dependencies
├── auth.py               # Authentication logic (Supabase JWT)
├── crud.py               # Database Create, Read, Update, Delete operations
├── database.py           # Database session and engine setup
├── models.py             # SQLAlchemy database models
├── schemas.py            # Pydantic data validation schemas
├── analysis_service.py   # Core logic for speech analysis
└── transcription_service.py # Service for interacting with AssemblyAI
```

## Setup and Installation

### 1. Prerequisites

- Python 3.12+
- A running PostgreSQL database instance.

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd team_epsilon_backend
```

### 3. Set up a Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies.

```bash
# For Unix/macOS
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Environment Variables

Create a `.env` file in the root of the project directory and add the following environment variables. These are essential for the application to connect to the required services.

```env
# Supabase Credentials
SUPABASE_PROJECT_URL="your_supabase_project_url"
SUPABASE_KEY="your_supabase_anon_key"
SUPABASE_SERVICE_ROLE_KEY="your_supabase_service_role_key" # Required for user deletion

# AssemblyAI API Key
ASSEMBLYAI_API_KEY="your_assemblyai_api_key"

# PostgreSQL Database Connection URL
# Format: postgresql://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL="your_database_connection_string"

# CORS Allowed Origins (comma-separated)
# Example: "http://localhost:3000,https://your-frontend-domain.com"
# For development, you can use "*" to allow all origins.
ALLOWED_ORIGINS="*"
```

### 6. Database Migrations

This project uses Alembic to handle database migrations.

- To generate a new migration script after changing the SQLAlchemy models in `models.py`:

```bash
alembic revision --autogenerate -m "A descriptive message for your migration"
```

- To apply the migrations to the database:

```bash
alembic upgrade head
```

## Running the Application

Once the setup is complete, you can run the development server using Uvicorn.

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, and you can access the interactive API documentation (Swagger UI) at `http://12.0.0.1:8000/docs`.

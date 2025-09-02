# Speech Improvement Backend

This project is the backend for a Speech Improvement application, designed to help users enhance their public speaking and pronunciation skills. It provides a RESTful API to handle user authentication, audio recording submissions, speech-to-text transcription, and in-depth analysis of spoken content.

## Features

- **User Authentication:** Secure user management using Supabase for authentication.
- **Audio Submission:** Users can upload audio files (e.g., MP3, WAV, M4A) for analysis.
- **Speech-to-Text:** Integrates with AssemblyAI to provide fast and accurate transcriptions of user audio.
- **Comprehensive Speech Analysis:**
    - **Fluency:** Measures Words Per Minute (WPM) and detects significant pauses.
    - **Pronunciation:** Calculates Word Error Rate (WER) against a given prompt to score accuracy.
    - **Filler Words:** Identifies and quantifies the usage of common filler words (e.g., "um", "like", "you know").
    - **Pacing:** Analyzes the consistency of the user's speaking rate over time.
- **Database Integration:** Stores user data, prompts, recordings, and analysis results in a PostgreSQL database.
- **Cloud Storage:** Securely stores audio recordings using Supabase Storage.

## API Endpoints

Here are the primary endpoints available:

| Method | Endpoint                             | Description                                                                                                 |
| :----- | :----------------------------------- | :---------------------------------------------------------------------------------------------------------- |
| `GET`  | `/health-check`                      | Checks the API and database connection status.                                                              |
| `GET`  | `/users/me`                          | Retrieves the profile of the currently authenticated user. Creates a new profile in the DB if it is not already there(Protected)                                      |
| `POST` | `/recordings/submit-and-analyze`     | Submits an audio file and a text prompt for transcription and full analysis. Returns the complete analysis. (Protected) |

## Technologies Used

- **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** [PostgreSQL](https://www.postgresql.org/)
- **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
- **Authentication:** [Supabase](https://supabase.io/)
- **Speech-to-Text:** [AssemblyAI](https://www.assemblyai.com/)
- **Data Validation:** [Pydantic](https://pydantic-docs.helpmanual.io/)
- **Asynchronous Server:** [Uvicorn](https://www.uvicorn.org/)

## Project Structure

The project follows a standard FastAPI application structure:

```
.
├── .env                # Environment variables (not committed)
├── main.py             # FastAPI app definition and main routes
├── requirements.txt    # Python dependencies
├── auth.py             # Authentication logic (Supabase JWT)
├── crud.py             # Database Create, Read, Update, Delete operations
├── database.py         # Database session and engine setup
├── models.py           # SQLAlchemy database models
├── schemas.py          # Pydantic data validation schemas
├── analysis_service.py # Core logic for speech analysis
└── transcription_service.py # Service for interacting with AssemblyAI
```

## Setup and Installation

### 1. Prerequisites

- Python 3.9+
- A running PostgreSQL database instance.

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd Team-Epsilon-Enforcers-Backend
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

# AssemblyAI API Key
ASSEMBLYAI_API_KEY="your_assemblyai_api_key"

# PostgreSQL Database Connection URL
# Format: postgresql://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL="your_database_connection_string"

# CORS Allowed Origins (comma-separated)
# Example: "http://localhost:3000,https://your-frontend-domain.com"
ALLOWED_ORIGINS="http://localhost:3000"
```

## Running the Application

Once the setup is complete, you can run the development server using Uvicorn.

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, and you can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

Here's the updated `README.md` in English, including instructions on setting up a virtual environment and testing the API with `pytest`:

---

# IoT Backend API

A FastAPI application for managing IoT devices, sensor data, and user authentication.

## Features

- User authentication with JWT
- IoT server management
- Collecting sensor data (temperature, humidity, voltage, current)
- Data aggregation and filtering
- Server status monitoring

## Configuration

### Environment Variables

- `DATABASE_URL`: URL for PostgreSQL database connection
- `SECRET_KEY`: Secret key for generating JWT tokens
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration time in minutes

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd iot-backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS
source venv/bin/activate
# On Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

## Testing the API

### Testing the API with Pytest

To test the API, you can use `pytest`, a popular testing tool for Python. Follow the instructions below to set up the testing environment and run tests automatically.

### Create and Activate a Virtual Environment

If you haven't done so already, create a virtual environment to isolate development dependencies:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS
source venv/bin/activate
# On Windows
venv\Scripts\activate
```

### Install Test Dependencies

With the virtual environment activated, install the necessary dependencies to run the tests, which are listed in the `requirements.txt`. Alternatively, you can manually install `pytest` for testing:

```bash
pip install -r requirements.txt
```

### Running the Tests

You can run the tests by executing the `pytest` command directly. Here's how to run the API tests:

```bash
# Run the tests
python -m pytest
```

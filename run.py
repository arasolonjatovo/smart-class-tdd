from src.api.app import create_app
import os

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_ENV", "development") == "development"

    print(f"Starting ML Service on port {port}")
    print(f"Debug mode: {debug}")
    print(
        f"Database URL: {os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/smartclass')}"
    )

    app.run(host="0.0.0.0", port=port, debug=debug)
